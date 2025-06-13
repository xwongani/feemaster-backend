import logging
import sys
import json
from datetime import datetime
from pythonjsonlogger import jsonlogger
from ..config import settings

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id

def setup_logging():
    """Configure structured logging"""
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CustomJsonFormatter())
    root_logger.addHandler(console_handler)

    # File handler with JSON formatting
    file_handler = logging.FileHandler(settings.log_file)
    file_handler.setFormatter(CustomJsonFormatter())
    root_logger.addHandler(file_handler)

    # Set up specific loggers
    loggers = {
        'app': logging.INFO,
        'app.database': logging.INFO,
        'app.api': logging.INFO,
        'app.services': logging.INFO,
        'app.utils': logging.INFO
    }

    for logger_name, level in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)

    # Configure third-party loggers
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name) 