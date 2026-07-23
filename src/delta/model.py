from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from src.canonical.model import BoundingBox

class ChangeType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"

class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class DeltaItem(BaseModel):
    id: str = Field(description="Unique ID for the delta item")
    change_type: ChangeType
    element_type: str = Field(description="Type of the element that changed (e.g., text, dimension)")
    page_number: int = Field(description="The page/sheet where the change occurred")
    bbox: Optional[BoundingBox] = Field(default=None, description="Bounding box of the changed region")
    description: str = Field(description="Human-readable description of what changed")
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.HIGH)
    
    # Raw context for the RAG chat
    base_content: Optional[str] = None
    revised_content: Optional[str] = None

class DeltaReport(BaseModel):
    base_pid: str
    revised_pid: str
    changes: List[DeltaItem] = Field(default_factory=list)
    
    @property
    def summary_counts(self) -> dict:
        counts = {"added": 0, "removed": 0, "modified": 0}
        for change in self.changes:
            counts[change.change_type.value] += 1
        return counts
