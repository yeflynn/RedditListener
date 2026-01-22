"""
Logging configuration for RedditListener
Creates timestamped log files with rotating file handler
"""
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

def setup_logger(name='RedditListener', log_dir='logs'):
    """
    Set up logger with timestamped file and console output
    
    Args:
        name: Logger name
        log_dir: Directory to store log files
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Generate timestamped log filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = os.path.join(log_dir, f'app_{timestamp}.log')
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # File handler with rotation (10MB per file, keep 5 files)
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Console handler (less verbose)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Log the log file location
    logger.info(f'Logging initialized. Log file: {log_filename}')
    
    return logger

def get_logger(name='RedditListener'):
    """
    Get existing logger instance
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
