from abc import ABC, abstractmethod
from typing import Optional
import os
import uuid
from src.canonical.model import CanonicalDocument

class BaseParser(ABC):
    """
    Abstract base class for all document parsers.
    Ensures that any ingestion format outputs the standardized CanonicalDocument.
    """

    @abstractmethod
    def parse(self, filepath: str, pid: Optional[str] = None) -> CanonicalDocument:
        """
        Parse a file and return its canonical representation.
        
        Args:
            filepath: Path to the raw document file.
            pid: Persistent identifier for this revision. If None, one will be generated.
            
        Returns:
            CanonicalDocument: The normalized, format-agnostic representation.
        """
        pass
    
    def _generate_pid(self, filepath: str) -> str:
        """Helper to generate a fallback PID based on the filename or UUID."""
        filename = os.path.basename(filepath)
        return f"{filename}_{uuid.uuid4().hex[:8]}"
