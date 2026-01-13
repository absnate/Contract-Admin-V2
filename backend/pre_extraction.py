"""
PRE-EXTRACTION MODULE
Global Keyword Harvest for Contract & Proposal Documents

Scans documents for high-signal lines before LLM processing.
Captures: pricing, dates, parties, payment terms, taxes, prevailing wage, 
insurance, OCIP/CCIP, addresses, deposits/retainers, escalation/tariffs, scope titles.
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

# Priority order for categories (1 = highest)
CATEGORY_PRIORITY = {
    "CONTRACT_VALUE": 1,
    "PARTIES": 2,
    "DATES": 3,
    "PAYMENT_TERMS": 4,
    "TAXES": 5,
    "INSURANCE": 6,
    "OCIP_CCIP": 7,
    "PREVAILING_WAGE": 8,
    "ADDRESS": 9,
    "DEPOSITS": 10,
    "ESCALATION": 11,
    "SCOPE_TITLES": 12,
    "PARKING": 13,
    "AUDIT": 14,
    "QAQC": 15,
    "DEFINITIONS": 0,  # HIGHEST PRIORITY - Definitions sections control role identification
}

# Keyword groups with patterns
KEYWORD_GROUPS = {
    "DEFINITIONS": [
        # Definitions sections - HIGHEST PRIORITY for role identification
        r"\bdefinitions\b", r"ARTICLE\s*\d+\s*[-–—]\s*DEFINITIONS",
        r"ARTICLE\s*1", r"ARTICLE\s*I\b",
        r"[A-Z]\.\s*Definitions", r"E\.\s*Definitions",
        r"\d+\.\s*Definitions",
        # Architect definitions (high priority)
        r"\d+\.\s*Architect\s*:", r"Architect\s*:", r"Project\s*Architect\s*:",
        r"Design\s*Architect\s*:", r"Architect\s*of\s*Record", r"\bAOR\s*:",
        r"\bDesigner\s*:",
        # Owner definitions
        r"\d+\.\s*Owner\s*:", r"Owner\s*:",
        # Contractor definitions
        r"\d+\.\s*Contractor\s*:", r"Contractor\s*:", r"General\s*Contractor\s*:",
        # Subcontractor definitions  
        r"\d+\.\s*Subcontractor\s*:", r"Subcontractor\s*:",
        # Common architecture firms (boost extraction)
        r"OZ\s*Architecture", r"Oz\s*Architecture",
        r"Architecture,?\s*Inc", r"Architects?,?\s*Inc",
        r"Architecture,?\s*LLC", r"Architects?,?\s*LLC",
    ],
    
    "CONTRACT_VALUE": [
        # Contract Price / Value / Breakdowns
        r"contract\s*price", r"contract\s*sum", r"subcontract\s*price", r"subcontract\s*sum",
        r"agreement\s*amount", r"contract\s*amount", r"total\s*contract\s*value", r"total\s*price",
        r"\btotal\b", r"\bTOTAL\s*:", r"grand\s*total", r"\bGROSS\b", r"net\s*amount",
        r"pricing\s*breakdown", r"schedule\s*of\s*values", r"\bSOV\b", r"line\s*item",
        r"cost\s*code", r"unit\s*price", r"lump\s*sum", r"base\s*bid",
        r"subtotal", r"sub-total", r"total\s*due", r"amount\s*due", r"balance\s*due",
        r"\badd\b", r"added", r"\bplus\b", r"\bfee\b", r"\bbond\b", r"bond\s*premium", r"bond\s*@",
        r"textura", r"\bPIF\b", r"builder's\s*fee", r"general\s*conditions",
        r"markup", r"OH\s*&\s*P", r"overhead", r"profit", r"retainage", r"retention",
        r"retainage\s*%", r"retention\s*%",
        r"allowances", r"contingency", r"deduct", r"deduction", r"credit",
        r"change\s*order", r"\bCO\b", r"\bPCO\b", r"extra\s*work", r"T\s*&\s*M", r"time\s*and\s*material",
        r"pay\s*app", r"pay\s*application", r"application\s*for\s*payment",
        r"AIA\s*G702", r"AIA\s*G703",
        # Currency patterns
        r"\$\s*[\d,]+\.?\d*", r"\bUSD\b", r"dollars",
    ],
    
    "PARTIES": [
        # Project / Parties / Entity Identification
        r"project\s*name", r"project\s*title", r"job\s*name", r"project\s*no", r"project\s*number",
        r"job\s*no", r"job\s*number", r"contract\s*no", r"contract\s*number", r"agreement\s*no",
        r"\bowner\b", r"property\s*owner", r"\bclient\b", r"\bcustomer\b", r"\bdeveloper\b", r"\blandlord\b",
        r"general\s*contractor", r"\bGC\b", r"\bcontractor\b", r"construction\s*manager", r"\bCM\b",
        r"CM-at-Risk", r"\bCMAR\b", r"prime\s*contractor",
        r"\barchitect\b", r"\bAIA\b", r"\bdesigner\b", r"\bengineer\b", r"\bEOR\b", r"\bconsultant\b",
        r"\bsubcontractor\b", r"\bsubcontract\b", r"trade\s*contractor", r"\bvendor\b",
        r"Milender\s*White", r"\bMW\b",
        # Signature blocks
        r"\bBy\s*:", r"\bName\s*:", r"\bTitle\s*:", r"\bCompany\s*:",
        r"authorized\s*representative", r"executed\s*by", r"IN\s*WITNESS\s*WHEREOF",
    ],
    
    "ADDRESS": [
        # Address / Location
        r"project\s*address", r"site\s*address", r"\bjobsite\b", r"\bsite\b", r"\blocation\b",
        r"\bpremises\b", r"\bproperty\b", r"\baddress\b", r"\bcity\b", r"\bstate\b",
        r"\bzip\b", r"\bZIP\b", r"\bcounty\b",
        # State abbreviations with zip patterns
        r"\b[A-Z]{2}\s+\d{5}(?:-\d{4})?\b",
    ],
    
    "DATES": [
        # Dates / Schedule / Substantial Completion
        r"start\s*date", r"commencement", r"notice\s*to\s*proceed", r"\bNTP\b",
        r"mobilization", r"mobilize",
        r"substantial\s*completion", r"final\s*completion", r"completion\s*date",
        r"contract\s*time", r"duration", r"calendar\s*days", r"working\s*days",
        r"project\s*schedule", r"\bschedule\b", r"\bmilestone\b", r"milestones",
        r"critical\s*path", r"\bCPM\b", r"baseline\s*schedule",
        # Trade activity keys for ABS
        r"final\s*paint", r"paint\s*start", r"paint\s*complete", r"\bpainting\b",
        r"\baccessories\b", r"\bmirrors\b", r"extinguishers", r"\bcabinets\b",
        r"toilet\s*accessories", r"bike\s*racks", r"ski\s*racks", r"\bcompartments\b",
        # Date patterns
        r"\d{1,2}/\d{1,2}/\d{2,4}", r"\d{4}-\d{2}-\d{2}",
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4}",
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},?\s*\d{4}",
    ],
    
    "PAYMENT_TERMS": [
        # Billing / Payment Terms / Due Dates
        r"payment\s*terms", r"terms\s*of\s*payment", r"net\s*30", r"net30", r"net\s*45", r"net45",
        r"net\s*60", r"net60", r"due\s*upon\s*receipt", r"payable\s*within", r"days\s*after",
        r"\binvoice\b", r"\binvoicing\b", r"\bbill\b", r"\bbilling\b", r"billing\s*due",
        r"due\s*date", r"\bpayable\b",
        r"pay\s*when\s*paid", r"pay-when-paid", r"pay\s*if\s*paid", r"pay-if-paid",
        r"conditional\s*payment", r"contingent\s*payment",
        r"final\s*payment", r"progress\s*payment", r"\bmonthly\b",
        # Retention / Retainage
        r"\bretention\b", r"\bretainage\b", r"retention\s*%", r"retainage\s*%",
        r"\d+\s*%\s*retention", r"\d+\s*%\s*retainage",
        r"retained", r"withheld", r"holdback", r"hold\s*back",
    ],
    
    "TAXES": [
        # Taxes / Tax Rate / Tax Status
        r"\btax\b", r"\btaxes\b", r"sales\s*tax", r"use\s*tax", r"gross\s*receipts\s*tax", r"excise\s*tax",
        r"tax\s*exempt", r"\bexempt\b", r"exemption", r"tax\s*exemption",
        r"\bcertificate\b", r"resale\s*certificate",
        r"tax\s*rate", r"\d+\.?\d*\s*%", r"\bpercent\b", r"percentage", r"rate\s*of",
        r"inclusive\s*of\s*tax", r"exclusive\s*of\s*tax", r"tax\s*included", r"plus\s*applicable\s*tax",
    ],
    
    "INSURANCE": [
        # Insurance (All Policies + Limits + Endorsements)
        r"\binsurance\b", r"certificate\s*of\s*insurance", r"\bCOI\b", r"\blimits\b",
        r"\bcoverage\b", r"\bpolicy\b", r"\boccurrence\b", r"claims-made", r"claims\s*made",
        r"commercial\s*general\s*liability", r"\bCGL\b", r"general\s*liability", r"\bGL\b",
        r"automobile\s*liability", r"auto\s*liability", r"business\s*auto", r"\bBAP\b",
        r"any\s*auto", r"\bhired\b", r"non-owned", r"\bowned\b",
        r"\bumbrella\b", r"\bexcess\b", r"umbrella/excess", r"excess\s*liability",
        r"excess\s*umbrella", r"\baggregate\b", r"each\s*occurrence",
        r"workers'\s*compensation", r"workers\s*comp", r"\bWC\b",
        r"employers\s*liability", r"employer's\s*liability", r"\bEL\b",
        r"professional\s*liability", r"errors\s*and\s*omissions", r"E\s*&\s*O", r"professional\s*errors",
        # Endorsements
        r"additional\s*insured", r"\bAI\b",
        r"primary\s*and\s*noncontributory", r"primary/non-contributory", r"\bPNC\b",
        r"waiver\s*of\s*subrogation", r"\bWOS\b",
        r"notice\s*of\s*cancellation", r"30\s*days", r"10\s*days",
        r"completed\s*operations", r"products-completed\s*operations",
        r"per\s*occurrence", r"each\s*occurrence", r"per\s*accident", r"each\s*accident",
        # Exhibits
        r"insurance\s*requirements", r"exhibit\s*D", r"exhibit\s*E",
        # Limit patterns
        r"\$\s*[\d,]+\.?\d*\s*/\s*\$\s*[\d,]+\.?\d*",  # $X/$Y format
        r"\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:each|per|aggregate|occurrence)",
    ],
    
    "OCIP_CCIP": [
        # OCIP / CCIP
        r"\bOCIP\b", r"owner\s*controlled\s*insurance\s*program", r"owner-controlled\s*insurance\s*program",
        r"\bCCIP\b", r"contractor\s*controlled\s*insurance\s*program", r"contractor-controlled\s*insurance\s*program",
        r"wrap-up", r"wrap\s*up", r"wrapup",
        r"enrollment", r"\bdeductible\b", r"\bSIR\b", r"site\s*safety",
        r"excluded\s*parties", r"excluded\s*work",
    ],
    
    "PREVAILING_WAGE": [
        # Prevailing Wage / Davis-Bacon
        r"prevailing\s*wage", r"davis-bacon", r"davis\s*bacon", r"\bDBRA\b",
        r"wage\s*determination", r"\bWD\b", r"certified\s*payroll",
        r"LCPtracker", r"LCP\s*Tracker", r"federal\s*wage", r"state\s*wage",
    ],
    
    "DEPOSITS": [
        # Deposits / Retainers / Upfront Payments
        r"\bdeposit\b", r"material\s*deposit", r"\bupfront\b", r"\badvance\b",
        r"\bprepayment\b", r"down\s*payment",
        r"\bretainer\b", r"new\s*client\s*retainer",
        r"purchase\s*order\s*release", r"PO\s*release", r"lead\s*time", r"long\s*lead",
    ],
    
    "ESCALATION": [
        # Escalation / Tariffs / Price Changes
        r"\bescalation\b", r"price\s*escalation", r"material\s*escalation",
        r"\bincrease\b", r"price\s*increase", r"price\s*change", r"price\s*increases",
        r"\btariff\b", r"\btariffs\b", r"\bsurcharge\b", r"market\s*volatility",
        r"\binflation\b", r"\bindex\b", r"price\s*adjustment",
        r"no\s*escalation", r"fixed\s*price", r"assume\s*risk", r"risk\s*assumption",
        r"subcontractor\s*responsible\s*for\s*increases",
    ],
    
    "SCOPE_TITLES": [
        # Scope titles for cross-reference
        r"scope\s*of\s*work", r"\bSOW\b", r"work\s*scope", r"scope\s*description",
        r"division\s*\d+", r"section\s*\d+",
        # Common ABS scopes
        r"toilet\s*partitions", r"bath\s*accessories", r"\bFRP\b",
        r"\blockers\b", r"visual\s*display", r"\bspecialties\b",
        r"fire\s*extinguishers", r"corner\s*guards", r"wall\s*protection",
    ],
    
    "PARKING": [
        # Parking - affects cost, logistics, access
        r"\bparking\b", r"onsite\s*parking", r"on-site\s*parking",
        r"off-site\s*parking", r"offsite\s*parking",
        r"street\s*parking", r"garage\s*parking", r"parking\s*garage",
        r"parking\s*deck", r"parking\s*structure",
        r"parking\s*fee", r"parking\s*fees", r"paid\s*parking", r"fee-based\s*parking",
        r"parking\s*pass", r"parking\s*passes", r"parking\s*permit", r"parking\s*permits",
        r"parking\s*badge", r"parking\s*badges",
        r"\bvalidation\b", r"validated\s*parking",
        r"daily\s*parking", r"monthly\s*parking",
        r"subcontractor\s*responsible\s*for\s*parking",
        r"no\s*parking\s*provided", r"parking\s*by\s*others",
        r"loading\s*zone", r"loading\s*dock",
        r"staging\s*area",
    ],
    
    "AUDIT": [
        # Audit rights and provisions - critical for Terms review
        r"\baudit\b", r"\baudits\b", r"\baudited\b", r"\bauditing\b",
        r"audit\s*rights", r"audit\s*right", r"right\s*to\s*audit",
        r"audit\s*provision", r"audit\s*provisions", r"audit\s*clause",
        r"books\s*and\s*records", r"financial\s*records", r"accounting\s*records",
        r"access\s*to\s*records", r"inspection\s*of\s*records",
        r"cost\s*records", r"cost\s*audit", r"cost\s*audits",
        r"lump\s*sum\s*audit", r"open\s*book", r"open-book",
        r"audit\s*period", r"audit\s*duration", r"years?\s*after\s*completion",
        r"certified\s*public\s*accountant", r"\bCPA\b",
        r"examination\s*of\s*records", r"review\s*of\s*records",
    ],
    
    "QAQC": [
        # QA/QC programs and fees - critical for Terms review
        r"\bQA/QC\b", r"\bQAQC\b", r"\bQA\s*/\s*QC\b",
        r"quality\s*assurance", r"quality\s*control",
        r"quality\s*assurance\s*program", r"quality\s*control\s*program",
        r"QA\s*program", r"QC\s*program", r"QA/QC\s*program",
        r"quality\s*program", r"quality\s*management",
        r"third\s*party\s*inspection", r"third-party\s*inspection",
        r"inspection\s*fee", r"inspection\s*fees",
        r"testing\s*fee", r"testing\s*fees",
        r"quality\s*fee", r"quality\s*fees",
        r"QA\s*fee", r"QC\s*fee", r"QA/QC\s*fee",
        r"fee\s*based\s*program", r"fee-based\s*program",
        r"program\s*fee", r"program\s*fees",
        r"inspection\s*program", r"testing\s*program",
        r"third\s*party\s*testing", r"third-party\s*testing",
        r"independent\s*testing", r"independent\s*inspection",
        r"material\s*testing", r"special\s*inspection",
        r"special\s*inspections", r"deputy\s*inspection",
    ],
}

@dataclass
class ExtractedMatch:
    """Represents a single extracted keyword match with context."""
    category: str
    line_number: int
    exact_line: str
    context: List[str]  # ±2 lines
    matched_keyword: str
    
    def __hash__(self):
        return hash((self.category, self.line_number, self.exact_line[:50]))
    
    def __eq__(self, other):
        if not isinstance(other, ExtractedMatch):
            return False
        # Consider matches equal if same category and similar text (deduplication)
        return (self.category == other.category and 
                self._normalize(self.exact_line) == self._normalize(other.exact_line))
    
    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        return re.sub(r'\s+', ' ', text.lower().strip())[:100]


def compile_patterns() -> Dict[str, List[re.Pattern]]:
    """Compile all keyword patterns for efficiency."""
    compiled = {}
    for category, patterns in KEYWORD_GROUPS.items():
        compiled[category] = [
            re.compile(pattern, re.IGNORECASE) for pattern in patterns
        ]
    return compiled

# Pre-compile patterns
COMPILED_PATTERNS = compile_patterns()


def get_context_lines(lines: List[str], line_idx: int, context_range: int = 2) -> List[str]:
    """Get ±context_range lines around the matched line."""
    start = max(0, line_idx - context_range)
    end = min(len(lines), line_idx + context_range + 1)
    return lines[start:end]


def is_table_row(line: str) -> bool:
    """Detect if line is part of a table (has multiple columns/tabs)."""
    # Check for tab separators or multiple consecutive spaces
    return '\t' in line or '  |  ' in line or line.count('   ') >= 2


def extract_keywords_from_text(text: str, document_type: str = "contract") -> List[ExtractedMatch]:
    """
    Scan document text for high-signal keywords.
    
    Args:
        text: Full document text
        document_type: "contract" or "proposal"
        
    Returns:
        List of ExtractedMatch objects sorted by priority
    """
    lines = text.split('\n')
    matches = []
    seen_matches = set()  # For deduplication
    
    for category, patterns in COMPILED_PATTERNS.items():
        for line_idx, line in enumerate(lines):
            for pattern in patterns:
                if pattern.search(line):
                    # Get context
                    context = get_context_lines(lines, line_idx)
                    
                    # If table row, get the full row
                    if is_table_row(line):
                        # Extend context to capture full table section
                        extended_start = max(0, line_idx - 5)
                        extended_end = min(len(lines), line_idx + 5)
                        context = lines[extended_start:extended_end]
                    
                    match = ExtractedMatch(
                        category=category,
                        line_number=line_idx + 1,  # 1-indexed
                        exact_line=line.strip(),
                        context=context,
                        matched_keyword=pattern.pattern[:50]
                    )
                    
                    # Deduplicate near-identical matches
                    match_key = (category, match._normalize(line))
                    if match_key not in seen_matches:
                        seen_matches.add(match_key)
                        matches.append(match)
                    
                    break  # Only match one pattern per line per category
    
    # Sort by priority
    matches.sort(key=lambda m: (CATEGORY_PRIORITY.get(m.category, 99), m.line_number))
    
    return matches


def format_pre_extraction_output(matches: List[ExtractedMatch], document_type: str) -> str:
    """
    Format extracted matches for LLM consumption.
    
    Args:
        matches: List of ExtractedMatch objects
        document_type: "contract" or "proposal"
        
    Returns:
        Formatted string for LLM prompt
    """
    if not matches:
        return f"Pre-Extraction: {document_type.title()}\nNo high-signal keywords found.\n"
    
    output_lines = [f"═══ PRE-EXTRACTION: {document_type.upper()} ═══\n"]
    
    # Group by category
    by_category = defaultdict(list)
    for match in matches:
        by_category[match.category].append(match)
    
    # Output in priority order
    for category in sorted(by_category.keys(), key=lambda c: CATEGORY_PRIORITY.get(c, 99)):
        category_matches = by_category[category]
        output_lines.append(f"\n[{category.replace('_', ' ')}]")
        
        for match in category_matches[:10]:  # Limit to 10 per category
            output_lines.append(f"  Line {match.line_number}: {match.exact_line[:200]}")
            
            # Add context (collapsed format)
            context_str = " | ".join([l.strip()[:80] for l in match.context if l.strip()])
            if context_str and context_str != match.exact_line.strip()[:80]:
                output_lines.append(f"    Context: {context_str[:300]}")
    
    output_lines.append("\n" + "═" * 50 + "\n")
    
    return "\n".join(output_lines)


def run_pre_extraction(
    contract_text: Optional[str] = None,
    proposal_text: Optional[str] = None
) -> str:
    """
    Main entry point: Run pre-extraction on contract and/or proposal.
    
    Args:
        contract_text: Full text of contract document (if uploaded)
        proposal_text: Full text of proposal document (if uploaded)
        
    Returns:
        Formatted pre-extraction output to prepend to LLM prompt
    """
    output_parts = []
    
    # Extract from contract
    if contract_text and contract_text.strip():
        contract_matches = extract_keywords_from_text(contract_text, "contract")
        output_parts.append(format_pre_extraction_output(contract_matches, "Contract"))
    
    # Extract from proposal
    if proposal_text and proposal_text.strip():
        proposal_matches = extract_keywords_from_text(proposal_text, "proposal")
        output_parts.append(format_pre_extraction_output(proposal_matches, "Proposal"))
    
    if not output_parts:
        return ""
    
    header = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PRE-EXTRACTION: KEYWORD HARVEST                           ║
║  High-signal lines extracted BEFORE full document analysis                   ║
║  Categories: Value, Parties, Dates, Payment, Taxes, Insurance, etc.          ║
╚══════════════════════════════════════════════════════════════════════════════╝

"""
    
    return header + "\n".join(output_parts)


# Special handling for totals - find explicit numeric values
def find_explicit_totals(text: str) -> List[Dict]:
    """
    Special scan for explicit TOTAL values, even if they appear later in exhibits.
    Ignores blank fields like $__________.
    """
    totals = []
    lines = text.split('\n')
    
    # Pattern for actual dollar amounts (not blanks)
    amount_pattern = re.compile(r'\$\s*([\d,]+\.?\d*)', re.IGNORECASE)
    total_indicator = re.compile(r'\b(total|contract\s*sum|subcontract\s*price|agreement\s*amount|grand\s*total)\b', re.IGNORECASE)
    
    for line_idx, line in enumerate(lines):
        # Skip blank amount fields
        if '________' in line or '$ _' in line:
            continue
            
        if total_indicator.search(line):
            amounts = amount_pattern.findall(line)
            for amount in amounts:
                # Filter out small amounts (likely not contract totals)
                try:
                    value = float(amount.replace(',', ''))
                    if value > 1000:  # Likely a real total
                        totals.append({
                            "line_number": line_idx + 1,
                            "line_text": line.strip(),
                            "amount": f"${amount}",
                            "value": value
                        })
                except ValueError:
                    continue
    
    # Return the largest total found (likely the contract total)
    totals.sort(key=lambda t: t.get('value', 0), reverse=True)
    return totals[:5]  # Top 5 totals


if __name__ == "__main__":
    # Test with sample text
    sample_text = """
    SUBCONTRACT AGREEMENT
    Project Name: Traer Creek Mixed Use Development
    Project Address: 123 Main Street, Denver, CO 80202
    
    General Contractor: ABC Construction LLC
    Subcontractor: Associated Building Specialties
    
    Contract Sum: $____________
    
    Schedule:
    Start Date: January 15, 2025
    Substantial Completion: June 30, 2025
    
    Payment Terms: Net 30 from approved pay application
    
    Insurance Requirements:
    General Liability: $1,000,000 each occurrence / $2,000,000 aggregate
    
    EXHIBIT A - PRICING
    Division 10 - Toilet Partitions: $45,000.00
    Division 10 - Bath Accessories: $12,500.00
    Subtotal: $57,500.00
    Tax (8.31%): $4,778.25
    TOTAL CONTRACT SUM: $62,278.25
    """
    
    result = run_pre_extraction(contract_text=sample_text)
    print(result)
    
    # Test explicit totals
    totals = find_explicit_totals(sample_text)
    print("\nExplicit Totals Found:")
    for t in totals:
        print(f"  Line {t['line_number']}: {t['amount']} - {t['line_text'][:50]}")
