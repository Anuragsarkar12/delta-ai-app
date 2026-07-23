import logging
import litellm
import instructor
from pydantic import BaseModel
from typing import List
from src.canonical.model import CanonicalDocument
from src.delta.model import DeltaReport, DeltaItem, ConfidenceLevel
from src.delta.align import align_and_diff_pages

logger = logging.getLogger(__name__)

# Use Instructor to patch litellm for structured Pydantic outputs
client = instructor.from_litellm(litellm.completion)

class LLMRefinedDelta(BaseModel):
    human_description: str
    confidence: ConfidenceLevel

class DeltaEngine:
    def __init__(self, model_name: str = "groq/mixtral-8x7b-32768"):
        """
        Initialize the DeltaEngine. 
        Defaults to Groq's Llama 3 70B for blazing fast classification.
        """
        self.model_name = model_name
        logger.info(f"Initialized DeltaEngine with LLM backend: {self.model_name}")

    def compute_delta(self, doc_a: CanonicalDocument, doc_b: CanonicalDocument) -> DeltaReport:
        logger.info(f"Computing delta between PID {doc_a.pid} and {doc_b.pid}...")
        report = DeltaReport(base_pid=doc_a.pid, revised_pid=doc_b.pid)
        
        # Match pages by page number (assuming 1:1 mapping for simplicity)
        pages_b_dict = {p.page_number: p for p in doc_b.pages}
        
        for page_a in doc_a.pages:
            page_b = pages_b_dict.get(page_a.page_number)
            if not page_b:
                logger.warning(f"Page {page_a.page_number} found in Doc A but not Doc B. Skipping or treating as full removal.")
                continue
                
            raw_deltas = align_and_diff_pages(page_a, page_b)
            
            # Refine MODIFIED deltas with LLM
            for delta in raw_deltas:
                if delta.change_type.value == "modified":
                    self._refine_delta_with_llm(delta)
                    
            report.changes.extend(raw_deltas)
            
        logger.info(f"Delta computation complete. Found {len(report.changes)} changes.")
        return report
        
    def _refine_delta_with_llm(self, delta: DeltaItem):
        """Uses the LLM to write a concise, human-readable summary of the modification."""
        try:
            prompt = (
                "You are an engineering document AI. Analyze the difference between the base text and revised text.\n"
                f"Base text: {delta.base_content}\n"
                f"Revised text: {delta.revised_content}\n"
                "Output a concise human_description of what changed, and your confidence in this assessment."
            )
            
            # This call uses the configured litellm provider (e.g. GROQ_API_KEY environment variable)
            response = client.chat.completions.create(
                model=self.model_name,
                response_model=LLMRefinedDelta,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            
            delta.description = response.human_description
            delta.confidence = response.confidence
            
        except Exception as e:
            logger.warning(f"LLM refinement failed for delta {delta.id}. Falling back to raw description. Error: {str(e)}")
