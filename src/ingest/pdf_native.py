import logging
import uuid
import pdfplumber
from typing import Optional
from src.ingest.base import BaseParser
from src.canonical.model import CanonicalDocument, CanonicalPage, DocumentElement, BoundingBox

logger = logging.getLogger(__name__)

class NativePDFParser(BaseParser):
    """
    Parses native (born-digital) PDFs using pdfplumber.
    Extracts text and its precise bounding boxes.
    """
    
    def parse(self, filepath: str, pid: Optional[str] = None) -> CanonicalDocument:
        final_pid = pid or self._generate_pid(filepath)
        logger.info(f"Parsing Native PDF: {filepath}", extra={"pid": final_pid})
        
        doc = CanonicalDocument(
            pid=final_pid,
            source_format="native_pdf",
            metadata={"source_filepath": filepath}
        )
        
        try:
            with pdfplumber.open(filepath) as pdf:
                for i, page in enumerate(pdf.pages):
                    canon_page = CanonicalPage(
                        page_number=i + 1,
                        width=float(page.width),
                        height=float(page.height)
                    )
                    
                    # Extract words with their bounding boxes
                    words = page.extract_words()
                    for word_obj in words:
                        text = word_obj.get("text", "")
                        if not text.strip():
                            continue
                            
                        # pdfplumber bbox is (x0, top, x1, bottom)
                        bbox = BoundingBox(
                            x0=float(word_obj["x0"]),
                            y0=float(word_obj["top"]),
                            x1=float(word_obj["x1"]),
                            y1=float(word_obj["bottom"])
                        )
                        
                        elem = DocumentElement(
                            id=str(uuid.uuid4()),
                            type="text",
                            content=text,
                            bbox=bbox,
                            metadata={"font_size": word_obj.get("size")} # Approximate if extracted at word level
                        )
                        canon_page.elements.append(elem)
                    
                    doc.pages.append(canon_page)
                    logger.debug(f"Parsed page {i+1} with {len(canon_page.elements)} elements.")
                    
        except Exception as e:
            logger.error(f"Failed to parse Native PDF {filepath}: {str(e)}")
            raise
            
        logger.info(f"Successfully parsed Native PDF into canonical format with {len(doc.pages)} pages.")
        return doc
