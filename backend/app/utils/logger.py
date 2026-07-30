import os
import sys
import json
import logging
from datetime import datetime

# Root logger for MotherCare AI
logger = logging.getLogger("mothercare")

# Check log format from env (json or text)
LOG_FORMAT = os.getenv("LOG_FORMAT", "text").lower()
LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()

# Resolve logging level
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)

class JsonFormatter(logging.Formatter):
    """Formats log records as structured JSON strings."""
    def format(self, record):
        # Extract default attributes
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "file": f"{record.filename}:{record.lineno}",
            "func": record.funcName,
        }
        
        # Include exception traceback if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        # Parse extra custom attributes attached to standard logger call extra={}
        standard_attrs = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
            'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
            'created', 'msecs', 'relativeCreated', 'thread', 'threadName', 'processName',
            'process', 'message', 'asctime'
        }
        
        extra_attrs = {}
        for k, v in record.__dict__.items():
            if k not in standard_attrs:
                try:
                    # Test serialization of value
                    json.dumps(v)
                    extra_attrs[k] = v
                except (TypeError, OverflowError):
                    extra_attrs[k] = str(v)
                    
        if extra_attrs:
            log_data["extra"] = extra_attrs
            
        try:
            return json.dumps(log_data)
        except Exception as e:
            # Fallback for extreme cases
            return json.dumps({
                "timestamp": log_data["timestamp"],
                "logger": log_data["logger"],
                "level": log_data["level"],
                "message": f"[Serialization Fail: {e}] {log_data['message']}"
            })

# Configure appropriate formatter
handler = logging.StreamHandler(sys.stdout)
if LOG_FORMAT == "json":
    formatter = JsonFormatter()
else:
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)
    logger.setLevel(LOG_LEVEL)

# Ensure Uvicorn and FastAPI logs route through our handler or match configuration
logging.getLogger("uvicorn.access").handlers = [handler]
logging.getLogger("uvicorn.error").handlers = [handler]
