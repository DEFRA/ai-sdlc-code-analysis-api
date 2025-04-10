import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name: str = "code_analyzer") -> logging.Logger:
    """
    Set up a logger with configuration from environment variables.

    Args:
        name: The name of the logger. Defaults to "code_analyzer".

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)

    # If the root logger has handlers, it means that logging is already configured
    # from the application's logging configuration system
    if logging.getLogger().handlers:
        # Just set the level as specified and don't add handlers
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, log_level))
        return logger

    # If we get here, no global logging config exists, so configure this logger manually

    # Get configuration from environment variables
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    enable_file_logging = os.getenv("ENABLE_FILE_LOGGING", "false").lower() == "true"

    # Use a default path relative to the repository root
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    default_log_path = os.path.join(repo_root, "logs", "code-analyzer.log")
    log_file_path = os.getenv("LOG_FILE_PATH", default_log_path)

    # Set log level
    logger.setLevel(getattr(logging, log_level))

    # Create formatters
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Always add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Add file handler if enabled
    if enable_file_logging:
        try:
            # Create log directory if it doesn't exist
            log_dir = os.path.dirname(log_file_path)
            Path(log_dir).mkdir(parents=True, exist_ok=True)

            # Set up rotating file handler (10MB max file size, keep 5 backup files)
            file_handler = RotatingFileHandler(
                log_file_path, maxBytes=10_000_000, backupCount=5
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning("Failed to set up file logging: %s", e)
            logger.warning("Continuing with console logging only")

    return logger


# Create a default logger instance
logger = setup_logger()
