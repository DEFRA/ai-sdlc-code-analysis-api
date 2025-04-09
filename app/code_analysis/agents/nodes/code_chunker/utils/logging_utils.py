"""Logging utilities for the code analyzer.

This module contains functions for consistent logging across the code analyzer components.
"""

import json
import logging
import time
from typing import Any


def setup_logger(name: str, log_level: int = logging.INFO) -> logging.Logger:
    """Set up and configure a logger.

    Args:
        name: Name of the logger
        log_level: The logging level to use

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # If the root logger has handlers, it means that logging is already configured
    # from the application's logging configuration system
    if logging.getLogger().handlers:
        # Just set the level and return the logger
        logger.setLevel(log_level)
        return logger

    # Don't add handlers if they're already configured from the parent logger
    if not logger.handlers:
        # Create file handler
        file_handler = logging.FileHandler(f"{name}.log")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter("%(levelname)s - %(message)s")
        console_handler.setFormatter(console_formatter)

        # Add both handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.DEBUG)  # Always log debug to file

    return logger


def log_message(
    logger: logging.Logger, level: int, message: str, include_traceback: bool = False
) -> None:
    """Standardized logging method to ensure consistent log formatting.

    Args:
        logger: Logger instance to use
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        message: Message to log
        include_traceback: Whether to include traceback (only for ERROR)
    """
    if level == logging.DEBUG:
        logger.debug(message)
    elif level == logging.INFO:
        logger.info(message)
    elif level == logging.WARNING:
        logger.warning(message)
    elif level == logging.ERROR:
        if include_traceback:
            logger.error(message, exc_info=True)
        else:
            logger.error(message)
    else:
        # Default to info for unknown levels
        logger.info(message)


class PromptLogger:
    """Logger for prompts and responses to API services."""

    def __init__(
        self, log_file_path: str, log_prompts: bool = False, log_responses: bool = False
    ):
        """Initialize the prompt logger.

        Args:
            log_file_path: Path to the log file
            log_prompts: Whether to log prompts
            log_responses: Whether to log responses
        """
        self.log_file_path = log_file_path
        self.log_prompts = log_prompts
        self.log_responses = log_responses

    def log_prompt(self, prompt: str):
        """Log a prompt to the log file.

        Args:
            prompt: The prompt to log
        """
        if not self.log_prompts:
            return

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"=== PROMPT: {timestamp} ===\n")
            log_file.write(prompt)
            log_file.write("\n\n")

    def log_response(self, response: Any):
        """Log a response to the log file.

        Args:
            response: The response to log
        """
        if not self.log_responses:
            return

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file_path, "a", encoding="utf-8") as log_file:
            log_file.write(f"=== RESPONSE: {timestamp} ===\n")
            # Ensure we're writing a string to the file
            if hasattr(response, "content") and hasattr(response.content, "text"):
                log_file.write(response.content.text)
            elif hasattr(response, "content"):
                if isinstance(response.content, str):
                    log_file.write(response.content)
                else:
                    log_file.write(json.dumps(response.content, indent=2, default=str))
            elif not isinstance(response, str):
                log_file.write(json.dumps(response, indent=2, default=str))
            else:
                log_file.write(response)
            log_file.write("\n\n")
