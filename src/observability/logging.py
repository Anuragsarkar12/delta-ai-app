import logging
import sys
import uuid
from pythonjsonlogger import jsonlogger
from contextvars import ContextVar

# A context variable to hold the trace ID for the current request/flow
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        
        # Inject the trace_id if it exists in the current context
        trace_id = trace_id_var.get()
        if trace_id:
            log_record['trace_id'] = trace_id
            
def setup_logging(level=logging.INFO):
    """
    Configure the root logger to output structured JSON logs.
    """
    logger = logging.getLogger()
    
    # Avoid adding multiple handlers if setup_logging is called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(level)
    
    logHandler = logging.StreamHandler(sys.stdout)
    # Define the format for the JSON logs
    formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(logger)s %(message)s')
    logHandler.setFormatter(formatter)
    
    logger.addHandler(logHandler)
    return logger

def set_trace_id(new_trace_id: str = None) -> str:
    """
    Set a new trace ID for the current context. Generates a UUID if none provided.
    """
    if not new_trace_id:
        new_trace_id = str(uuid.uuid4())
    trace_id_var.set(new_trace_id)
    return new_trace_id
