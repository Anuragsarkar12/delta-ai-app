import logging
import uuid
import numpy as np
import pdfplumber
import easyocr
from typing import Optional
from src.ingest.base import BaseParser
from src.canonical.model import CanonicalDocument, CanonicalPage, DocumentElement, BoundingBox

logger = logging.getLogger(__name__)

# Initialize the EasyOCR reader (loads models into memory on first use)
# Using English only for this assignment to keep it fast
reader = easyocr.Reader(['en'], gpu=False) # Switch gpu=True if running on a CUDA machine

class ScannedPDFParser(BaseParser):
    """
    Parses scanned (raster) PDFs using pdfplumber to extract images and EasyOCR to extract text.
    """
    
    def parse(self, filepath: str, pid: Optional[str] = None) -> CanonicalDocument:
        final_pid = pid or self._generate_pid(filepath)
        logger.info(f"Parsing Scanned PDF with OCR: {filepath}", extra={"pid": final_pid})
        
        doc = CanonicalDocument(
            pid=final_pid,
            source_format="scanned_pdf",
            metadata={"source_filepath": filepath, "ocr_engine": "easyocr"}
        )
        
        try:
            with pdfplumber.open(filepath) as pdf:
                for i, page in enumerate(pdf.pages):
                    canon_page = CanonicalPage(
                        page_number=i + 1,
                        width=float(page.width),
                        height=float(page.height)
                    )
                    
                    # Convert page to a PIL Image at a reasonable resolution for OCR
                    page_image = page.to_image(resolution=300).original
                    # Convert PIL Image to numpy array (RGB) for EasyOCR
                    img_array = np.array(page_image)
                    
                    logger.debug(f"Running EasyOCR on page {i+1}...")
                    # result is a list of tuples: (bbox, text, confidence)
                    # bbox is a list of 4 points: [top-left, top-right, bottom-right, bottom-left]
                    results = reader.readtext(img_array)
                    
                    for (bbox, text, confidence) in results:
                        if not text.strip():
                            continue
                            
                        # EasyOCR bbox format: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
                        # Note: coordinates are based on the 300 DPI image, we should map them back
                        # to the PDF's point-based coordinate system if we want them to align with native PDFs.
                        # Scale factor = PDF dimension / Image dimension
                        scale_x = float(page.width) / img_array.shape[1]
                        scale_y = float(page.height) / img_array.shape[0]
                        
                        top_left = bbox[0]
                        bottom_right = bbox[2]
                        
                        canon_bbox = BoundingBox(
                            x0=float(top_left[0]) * scale_x,
                            y0=float(top_left[1]) * scale_y,
                            x1=float(bottom_right[0]) * scale_x,
                            y1=float(bottom_right[1]) * scale_y
                        )
                        
                        elem = DocumentElement(
                            id=str(uuid.uuid4()),
                            type="text_ocr",
                            content=text,
                            bbox=canon_bbox,
                            metadata={"ocr_confidence": float(confidence)}
                        )
                        canon_page.elements.append(elem)
                    
                    doc.pages.append(canon_page)
                    logger.debug(f"Parsed page {i+1} with {len(canon_page.elements)} OCR elements.")
                    
        except Exception as e:
            logger.error(f"Failed to parse Scanned PDF {filepath}: {str(e)}")
            raise
            
        logger.info(f"Successfully OCR'd Scanned PDF into canonical format with {len(doc.pages)} pages.")
        return doc
