import logging
from typing import Optional

from .base_parser import BaseLanguageParser
from .csharp_parser import CSharpParser
from .java_parser import JavaParser
from .javascript_parser import JavaScriptParser
from .python_parser import PythonParser
from .scala_parser import ScalaParser


def get_language_parser(
    language: str, logger: Optional[logging.Logger] = None
) -> Optional[BaseLanguageParser]:
    """Get the appropriate parser for a language.

    Args:
        language: Programming language (e.g., 'python', 'javascript')
        logger: Logger instance to use

    Returns:
        Language-specific parser instance or None if no parser is available
    """
    # Normalize language name
    language = language.lower()
    if language == "c#":
        language = "csharp"

    parser_class = {
        "python": PythonParser,
        "javascript": JavaScriptParser,
        "typescript": JavaScriptParser,
        "java": JavaParser,
        "csharp": CSharpParser,
        "scala": ScalaParser,
    }.get(language)

    if not parser_class:
        if logger:
            logger.warning("No parser available for language: %s", language)
        return None

    return parser_class(logger)
