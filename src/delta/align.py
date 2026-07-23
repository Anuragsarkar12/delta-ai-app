import uuid
from typing import List, Tuple, Dict
import logging
from src.canonical.model import CanonicalDocument, CanonicalPage, DocumentElement
from src.delta.model import ChangeType, DeltaItem, ConfidenceLevel

logger = logging.getLogger(__name__)

def _bboxes_overlap(b1, b2, tolerance=10.0) -> bool:
    """Check if two bounding boxes overlap within a spatial tolerance."""
    if not b1 or not b2:
        return False
    # Check for non-overlapping conditions
    if b1.x1 + tolerance < b2.x0 or b2.x1 + tolerance < b1.x0:
        return False
    if b1.y1 + tolerance < b2.y0 or b2.y1 + tolerance < b1.y0:
        return False
    return True

def align_and_diff_pages(page_a: CanonicalPage, page_b: CanonicalPage) -> List[DeltaItem]:
    """
    Deterministically aligns elements between two pages based on spatial overlap and text similarity.
    Classifies raw changes into Added, Removed, or Modified.
    """
    deltas = []
    
    elements_a = list(page_a.elements)
    elements_b = list(page_b.elements)
    
    matched_b_ids = set()
    
    # 1. Find Modified and Removed
    for elem_a in elements_a:
        match_found = False
        
        for elem_b in elements_b:
            if elem_b.id in matched_b_ids:
                continue
                
            # Naive spatial alignment: Do they occupy roughly the same area?
            if _bboxes_overlap(elem_a.bbox, elem_b.bbox):
                match_found = True
                matched_b_ids.add(elem_b.id)
                
                # Check for modification
                if elem_a.content != elem_b.content:
                    deltas.append(DeltaItem(
                        id=str(uuid.uuid4()),
                        change_type=ChangeType.MODIFIED,
                        element_type=elem_b.type,
                        page_number=page_b.page_number,
                        bbox=elem_b.bbox or elem_a.bbox,
                        description=f"Content changed from '{elem_a.content}' to '{elem_b.content}'",
                        base_content=elem_a.content,
                        revised_content=elem_b.content,
                        confidence=ConfidenceLevel.MEDIUM # LLM will refine this later
                    ))
                break
                
        if not match_found:
            # It was in A but not in B -> Removed
            deltas.append(DeltaItem(
                id=str(uuid.uuid4()),
                change_type=ChangeType.REMOVED,
                element_type=elem_a.type,
                page_number=page_a.page_number,
                bbox=elem_a.bbox,
                description=f"Removed content: '{elem_a.content}'",
                base_content=elem_a.content,
                confidence=ConfidenceLevel.HIGH
            ))
            
    # 2. Find Added
    for elem_b in elements_b:
        if elem_b.id not in matched_b_ids:
            # It's in B but wasn't matched to anything in A -> Added
            deltas.append(DeltaItem(
                id=str(uuid.uuid4()),
                change_type=ChangeType.ADDED,
                element_type=elem_b.type,
                page_number=page_b.page_number,
                bbox=elem_b.bbox,
                description=f"Added content: '{elem_b.content}'",
                revised_content=elem_b.content,
                confidence=ConfidenceLevel.HIGH
            ))
            
    return deltas
