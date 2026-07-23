from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    """
    Represents a bounding box (x0, y0, x1, y1) in points.
    x0, y0 is top-left, x1, y1 is bottom-right.
    """
    x0: float
    y0: float
    x1: float
    y1: float

class DocumentElement(BaseModel):
    """
    A unified element parsed from any source format.
    """
    id: str = Field(description="A unique identifier for the element within the document")
    type: str = Field(description="The type of element (e.g., text, line, path, image, dimension)")
    content: Optional[str] = Field(default=None, description="The text content if applicable")
    bbox: Optional[BoundingBox] = Field(default=None, description="The spatial location of the element")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional format-specific metadata (e.g. layer, font size)")

class CanonicalPage(BaseModel):
    """
    Represents a single page or sheet in the document.
    """
    page_number: int
    width: float
    height: float
    elements: List[DocumentElement] = Field(default_factory=list)

class CanonicalDocument(BaseModel):
    """
    The format-agnostic canonical representation of a document revision (PID).
    """
    pid: str
    source_format: str = Field(description="e.g. native_pdf, scanned_pdf, dwg")
    pages: List[CanonicalPage] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
