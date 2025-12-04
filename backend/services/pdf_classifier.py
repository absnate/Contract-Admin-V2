from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
import os
import tempfile
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class PDFClassifier:
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        if not self.api_key:
            logger.warning("EMERGENT_LLM_KEY not found in environment")
    
    async def classify_pdf(self, filename: str, url: str, content_sample: bytes, manufacturer: str, product_lines: list) -> dict:
        """
        Classify if a PDF is technical documentation using Gemini AI
        
        Returns:
            dict with keys: is_technical (bool), reason (str), document_type (str or None)
        """
        try:
            # Basic filename-based classification first
            filename_lower = filename.lower()
            url_lower = url.lower()
            
            technical_keywords = [
                'datasheet', 'data sheet', 'spec sheet', 'specification',
                'technical data', 'tds', 'pds', 'product data',
                'installation', 'manual', 'operation', 'maintenance',
                'submittal', 'cut sheet', 'engineering'
            ]
            
            marketing_keywords = [
                'brochure', 'catalog', 'flyer', 'marketing',
                'press release', 'news', 'warranty', 'msds', 'sds'
            ]
            
            # Check for obvious technical documents
            has_technical = any(kw in filename_lower or kw in url_lower for kw in technical_keywords)
            has_marketing = any(kw in filename_lower or kw in url_lower for kw in marketing_keywords)
            
            if has_marketing and not has_technical:
                return {
                    "is_technical": False,
                    "reason": "Filename/URL indicates marketing material",
                    "document_type": None
                }
            
            if has_technical:
                doc_type = self._determine_document_type(filename_lower, url_lower)
                return {
                    "is_technical": True,
                    "reason": "Filename/URL indicates technical documentation",
                    "document_type": doc_type
                }
            
            # Use AI for uncertain cases
            if self.api_key:
                return await self._classify_with_ai(filename, url, content_sample, manufacturer, product_lines)
            else:
                # Default to conservative classification
                return {
                    "is_technical": True,
                    "reason": "Unable to definitively classify - conservatively marked as technical",
                    "document_type": "Unknown"
                }
        
        except Exception as e:
            logger.error(f"Error classifying PDF {filename}: {str(e)}")
            return {
                "is_technical": False,
                "reason": f"Classification error: {str(e)}",
                "document_type": None
            }
    
    async def _classify_with_ai(self, filename: str, url: str, content_sample: bytes, manufacturer: str, product_lines: list) -> dict:
        """Use Gemini AI to classify the PDF"""
        try:
            # Save content sample to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(content_sample)
                tmp_path = tmp_file.name
            
            # Initialize Gemini chat
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"pdf_classify_{filename}",
                system_message="""You are an expert at classifying PDF documents for construction and manufacturing.
                
Your task is to determine if a PDF is TECHNICAL PRODUCT DOCUMENTATION or MARKETING MATERIAL.
                
TECHNICAL DOCUMENTATION includes:
                - Technical data sheets (TDS)
                - Product data sheets (PDS)
                - Specification sheets
                - Cut sheets
                - Installation manuals
                - Operation & maintenance manuals
                - Submittal sheets
                - Engineering diagrams
                
MARKETING MATERIALS include:
                - Sales brochures
                - Marketing flyers
                - Press releases
                - Warranty documents
                - General catalogs
                
Respond with a JSON object containing:
                - is_technical: boolean
                - reason: brief explanation
                - document_type: string (one of: "Technical Data Sheet", "Product Data Sheet", "Specification Sheet", "Installation Manual", "Operation Manual", "Submittal Sheet", "Engineering Diagram", "Marketing", "Other")
                """
            ).with_model("gemini", "gemini-2.0-flash")
            
            # Create file attachment
            file_content = FileContentWithMimeType(
                file_path=tmp_path,
                mime_type="application/pdf"
            )
            
            product_lines_str = ", ".join(product_lines) if product_lines else "Not specified"
            
            # Send classification request
            user_message = UserMessage(
                text=f"""Analyze this PDF and determine if it is technical product documentation.
                
Manufacturer: {manufacturer}
Product Lines: {product_lines_str}
Filename: {filename}
URL: {url}
                
Provide classification in JSON format.""",
                file_contents=[file_content]
            )
            
            response = await chat.send_message(user_message)
            
            # Clean up temp file
            os.unlink(tmp_path)
            
            # Parse response
            import json
            # Extract JSON from response
            response_text = response.strip()
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            result = json.loads(response_text.strip())
            
            return {
                "is_technical": result.get("is_technical", False),
                "reason": result.get("reason", "AI classification"),
                "document_type": result.get("document_type")
            }
        
        except Exception as e:
            logger.error(f"AI classification failed for {filename}: {str(e)}")
            # Fallback to filename-based classification
            doc_type = self._determine_document_type(filename.lower(), url.lower())
            return {
                "is_technical": doc_type is not None,
                "reason": f"AI failed, used filename analysis: {str(e)}",
                "document_type": doc_type
            }
    
    def _determine_document_type(self, filename_lower: str, url_lower: str) -> str:
        """Determine document type from filename and URL"""
        combined = f"{filename_lower} {url_lower}"
        
        if any(kw in combined for kw in ['datasheet', 'data sheet', 'tds']):
            return "Technical Data Sheet"
        elif any(kw in combined for kw in ['product data', 'pds']):
            return "Product Data Sheet"
        elif any(kw in combined for kw in ['spec', 'specification']):
            return "Specification Sheet"
        elif 'installation' in combined:
            return "Installation Manual"
        elif any(kw in combined for kw in ['operation', 'maintenance', 'o&m', 'om']):
            return "Operation Manual"
        elif 'submittal' in combined:
            return "Submittal Sheet"
        elif 'cut sheet' in combined:
            return "Cut Sheet"
        elif any(kw in combined for kw in ['diagram', 'drawing', 'cad']):
            return "Engineering Diagram"
        else:
            return "Technical Document"