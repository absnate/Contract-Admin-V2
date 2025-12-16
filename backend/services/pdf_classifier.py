from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
import os
import re
import tempfile
import logging
from dotenv import load_dotenv
from typing import Dict, List, Tuple

load_dotenv()
logger = logging.getLogger(__name__)


class PDFClassifier:
    """
    Strict PDF classifier for submittal-level technical data sheets ONLY.
    
    ALLOWED: submittal data, technical data, data sheet, datasheet, submittals
    DISALLOWED: warranty, installation, maintenance, operation, spec, catalog, 
                brochure, BIM, CAD, marketing, CSI, compliance, etc.
    """
    
    # ALLOWED KEYWORDS - PDF must match at least one
    ALLOWED_KEYWORDS = [
        'submittal data',
        'submittal data sheet',
        'submittal datasheet', 
        'technical data',
        'technical data sheet',
        'technical datasheet',
        'data sheet',
        'datasheet',
        'data-sheet',
        'submittals',
        'submittal',
        'tech data',
        'tds',  # Technical Data Sheet abbreviation
        'pds',  # Product Data Sheet abbreviation
    ]
    
    # DISALLOWED KEYWORDS - PDF is rejected if ANY match
    DISALLOWED_KEYWORDS = [
        # Installation & Maintenance
        'warranty',
        'installation',
        'install',
        'maintenance',
        'maint',
        'operation',
        'o&m',
        'o & m',
        'service manual',
        'parts list',
        'spare parts',
        'user guide',
        'user manual',
        'quick start',
        
        # Specifications (not submittal data)
        '3-part spec',
        '3-part specification',
        '3 part spec',
        'three part spec',
        'master spec',
        'guide spec',
        'csi spec',
        'specification guideline',
        'spec guideline',
        
        # CAD/BIM
        'bim',
        'revit',
        'cad',
        'dwg',
        'dxf',
        'hdp',
        'autocad',
        
        # Marketing
        'catalog',
        'catalogue',
        'brochure',
        'marketing',
        'sweets',
        'flyer',
        'sell sheet',
        'sell-sheet',
        'ideabook',
        'idea book',
        'solutions guide',
        
        # Compliance/Testing
        'csi',
        'compliance',
        'certification',
        'testing report',
        'test report',
        'white paper',
        'whitepaper',
        'application guide',
        'application note',
        
        # Safety
        'msds',
        'sds',
        'safety data',
        
        # Other excluded types
        'press release',
        'news',
        'award',
        'case study',
    ]
    
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not self.api_key:
            logger.warning("EMERGENT_LLM_KEY not found in environment")
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for keyword matching"""
        # Convert to lowercase and normalize whitespace/hyphens
        text = text.lower()
        text = re.sub(r'[-_]', ' ', text)  # Replace hyphens/underscores with spaces
        text = re.sub(r'\s+', ' ', text)   # Normalize multiple spaces
        return text
    
    def _check_allowed_keywords(self, text: str) -> Tuple[bool, List[str]]:
        """Check if text contains any allowed keywords"""
        normalized = self._normalize_text(text)
        matched = []
        
        for keyword in self.ALLOWED_KEYWORDS:
            if keyword in normalized:
                matched.append(keyword)
        
        return len(matched) > 0, matched
    
    def _check_disallowed_keywords(self, text: str) -> Tuple[bool, List[str]]:
        """Check if text contains any disallowed keywords"""
        normalized = self._normalize_text(text)
        matched = []
        
        for keyword in self.DISALLOWED_KEYWORDS:
            if keyword in normalized:
                matched.append(keyword)
        
        return len(matched) > 0, matched
    
    async def classify_pdf(self, filename: str, url: str, content_sample: bytes, manufacturer: str, product_lines: list) -> dict:
        """
        Classify if a PDF qualifies as a submittal technical data sheet.
        
        Decision Logic (in order):
        1. Must match at least one ALLOWED keyword
        2. Must NOT match any DISALLOWED keyword  
        3. Combination documents are disqualified
        
        Returns:
            dict with keys: 
                - is_technical (bool): True only for submittal data sheets
                - reason (str): Explanation of decision
                - document_type (str or None): Type if allowed
                - allowed_matches (list): Matched allowed keywords
                - disallowed_matches (list): Matched disallowed keywords
        """
        try:
            combined_text = f"{filename} {url}"
            
            # Step 1: Check for allowed keywords
            has_allowed, allowed_matches = self._check_allowed_keywords(combined_text)
            
            # Step 2: Check for disallowed keywords
            has_disallowed, disallowed_matches = self._check_disallowed_keywords(combined_text)
            
            # Log the evaluation
            logger.info(f"PDF Evaluation: {filename}")
            logger.info(f"  Allowed matches: {allowed_matches}")
            logger.info(f"  Disallowed matches: {disallowed_matches}")
            
            # Decision Logic
            
            # Rule 1: Must have at least one allowed keyword
            if not has_allowed:
                reason = f"SKIPPED: No allowed keywords found. Looking for: submittal data, technical data, data sheet, etc."
                logger.info(f"  Decision: {reason}")
                return {
                    "is_technical": False,
                    "reason": reason,
                    "document_type": None,
                    "allowed_matches": [],
                    "disallowed_matches": disallowed_matches
                }
            
            # Rule 2: Must NOT have any disallowed keywords
            if has_disallowed:
                reason = f"SKIPPED: Contains disallowed content: {', '.join(disallowed_matches)}"
                logger.info(f"  Decision: {reason}")
                return {
                    "is_technical": False,
                    "reason": reason,
                    "document_type": None,
                    "allowed_matches": allowed_matches,
                    "disallowed_matches": disallowed_matches
                }
            
            # Passed all checks - this is a valid submittal technical data sheet
            doc_type = self._determine_document_type(allowed_matches)
            reason = f"APPROVED: Matched allowed keywords: {', '.join(allowed_matches)}"
            logger.info(f"  Decision: {reason}")
            
            return {
                "is_technical": True,
                "reason": reason,
                "document_type": doc_type,
                "allowed_matches": allowed_matches,
                "disallowed_matches": []
            }
        
        except Exception as e:
            logger.error(f"Error classifying PDF {filename}: {str(e)}")
            # On error, default to SKIP (precision over completeness)
            return {
                "is_technical": False,
                "reason": f"Classification error - SKIPPED: {str(e)}",
                "document_type": None,
                "allowed_matches": [],
                "disallowed_matches": []
            }
    
    def _determine_document_type(self, allowed_matches: List[str]) -> str:
        """Determine specific document type from matched keywords"""
        matches_str = ' '.join(allowed_matches)
        
        if 'submittal' in matches_str:
            return "Submittal Data Sheet"
        elif 'technical data' in matches_str or 'tech data' in matches_str or 'tds' in matches_str:
            return "Technical Data Sheet"
        elif 'pds' in matches_str:
            return "Product Data Sheet"
        elif 'data sheet' in matches_str or 'datasheet' in matches_str:
            return "Data Sheet"
        else:
            return "Submittal Technical Data"
    
    async def _classify_with_ai(self, filename: str, url: str, content_sample: bytes, manufacturer: str, product_lines: list) -> dict:
        """
        AI classification is disabled for strict mode.
        We rely solely on keyword matching for precision.
        """
        # In strict mode, we don't use AI - keyword matching provides precise filtering
        return {
            "is_technical": False,
            "reason": "AI classification disabled in strict mode - use keyword matching only",
            "document_type": None,
            "allowed_matches": [],
            "disallowed_matches": []
        }


# Utility function for reporting
def generate_classification_report(classifications: List[dict]) -> str:
    """Generate a summary report of PDF classifications"""
    report_lines = [
        "=" * 80,
        "PDF CLASSIFICATION REPORT",
        "=" * 80,
        "",
        f"Total PDFs evaluated: {len(classifications)}",
        f"Downloaded (approved): {sum(1 for c in classifications if c.get('is_technical'))}",
        f"Skipped: {sum(1 for c in classifications if not c.get('is_technical'))}",
        "",
        "-" * 80,
        "DETAILED LOG:",
        "-" * 80,
    ]
    
    for c in classifications:
        status = "✓ DOWNLOADED" if c.get('is_technical') else "✗ SKIPPED"
        report_lines.append(f"\n{status}: {c.get('filename', 'Unknown')}")
        report_lines.append(f"  URL: {c.get('url', 'Unknown')}")
        report_lines.append(f"  Allowed matches: {c.get('allowed_matches', [])}")
        report_lines.append(f"  Disallowed matches: {c.get('disallowed_matches', [])}")
        report_lines.append(f"  Reason: {c.get('reason', 'No reason')}")
    
    return "\n".join(report_lines)
