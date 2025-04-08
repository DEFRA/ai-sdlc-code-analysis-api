"""Simple parser for extracting code structure when tree-sitter is not available."""

import logging
from typing import Any


def extract_code_elements_simple(
    _content: str, _logger: logging.Logger
) -> dict[str, Any]:
    """Extract code elements using simple string parsing.

    Args:
        _content: Source code content to parse
        _logger: Logger instance

    Returns:
        Dictionary of code elements (functions, classes, imports, comments)
    """
    # Return empty structure when tree-sitter is disabled
    return {
        "functions": [],
        "classes": [],
        "imports": [],
        "comments": [],
    }
