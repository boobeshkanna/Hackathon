"""
Logging configuration for Lambda functions
"""
import logging
import json
import sys
from typing import Any, Dict
from .config import config


def setup_logger(name: str) -> logging.Logger:
    """
    Set up structured logger for Lambda functions
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # JSON formatter for CloudWatch Logs Insights
    formatter = JsonFormatter()
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.propagate = False
    
    return logger


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data: Dict[str, Any] = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'catalog_id'):
            log_data['catalog_id'] = record.catalog_id
        if hasattr(record, 'tenant_id'):
            log_data['tenant_id'] = record.tenant_id
        
        return json.dumps(log_data)
