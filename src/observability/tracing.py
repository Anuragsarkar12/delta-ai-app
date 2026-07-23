import logging
import phoenix as px
from openinference.instrumentation.litellm import LiteLLMInstrumentor

logger = logging.getLogger(__name__)

def setup_tracing():
    """
    Initializes Arize Phoenix for local observability and traces all LiteLLM calls.
    Launch the Phoenix UI in your browser to view traces and metrics.
    """
    logger.info("Initializing Arize Phoenix for observability...")
    try:
        # Starts a local Phoenix server if not already running
        session = px.launch_app()
        logger.info(f"Phoenix UI is running at {session.url}")
        
        # Instrument LiteLLM to automatically capture all LLM calls, tokens, and costs
        LiteLLMInstrumentor().instrument()
        logger.info("LiteLLM tracing enabled.")
        
    except Exception as e:
        logger.error(f"Failed to initialize Phoenix tracing: {e}")
