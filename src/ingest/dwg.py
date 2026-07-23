import logging
from typing import Optional
from src.ingest.base import BaseParser
from src.canonical.model import CanonicalDocument

logger = logging.getLogger(__name__)

class DWGParser(BaseParser):
    """
    Stub parser for DWG format. 
    Demonstrates the seam where a third format would plug into the canonical representation pipeline.
    To be fully implemented with e.g. ezdxf later if required.
    """
    
    def parse(self, filepath: str, pid: Optional[str] = None) -> CanonicalDocument:
        final_pid = pid or self._generate_pid(filepath)
        logger.warning(f"DWGParser is currently a stub. Returning empty document for {filepath}", extra={"pid": final_pid})
        
        doc = CanonicalDocument(
            pid=final_pid,
            source_format="dwg",
            metadata={"source_filepath": filepath, "status": "stub_implementation"}
        )
        return doc
