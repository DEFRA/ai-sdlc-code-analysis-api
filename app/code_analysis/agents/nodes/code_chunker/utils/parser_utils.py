"""Parser utilities for the code analyzer.

This module contains functions for initializing and managing code parsers.
"""

import logging
from typing import Any, Optional

from ..parsers.factory import get_language_parser


class ParserManager:
    """Manages the initialization and use of code parsers."""

    SUPPORTED_LANGUAGES = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".cs": "csharp",
        ".java": "java",
    }

    def __init__(self, logger: logging.Logger):
        """Initialize the parser manager.

        Args:
            logger: Logger instance to use for logging
        """
        self.logger = logger
        self.parsers = {}
        self.using_tree_sitter = False
        self._init_parsers()

    def _init_parsers(self):
        """Initialize tree-sitter parsers for supported languages."""
        self.parsers = {}
        self.using_tree_sitter = False

        try:
            import tree_sitter
            import tree_sitter_language_pack

            # Log the tree-sitter version if available
            version = getattr(tree_sitter, "__version__", "Unknown")
            self.logger.info("Tree-sitter version: %s", version)
            
            # Remove references to non-existent attributes
            # self.logger.info(
            #     "Language version required: %s", tree_sitter.LANGUAGE_VERSION
            # )
            # self.logger.info(
            #     "Min compatible language version: %s",
            #     tree_sitter.MIN_COMPATIBLE_LANGUAGE_VERSION,
            # )

            # Check if the language pack has the get_language function
            if hasattr(tree_sitter_language_pack, "get_language"):
                self.logger.info(
                    "Using tree-sitter-language-pack for parser initialization"
                )

                languages_to_try = {
                    "python": "Python",
                    "javascript": "JavaScript",
                    "typescript": "TypeScript",
                    "csharp": "C#",
                    "java": "Java",
                }

                initialized_count = 0
                for lang_id, lang_name in languages_to_try.items():
                    try:
                        language = tree_sitter_language_pack.get_language(lang_id)
                        parser = tree_sitter.Parser()
                        parser.language = language
                        self.parsers[lang_name] = parser
                        self.logger.info(
                            "✅ Successfully initialized parser for %s", lang_name
                        )
                        initialized_count += 1
                    except Exception as e:
                        self.logger.warning(
                            "Failed to initialize parser for %s: %s", lang_name, e
                        )

                if initialized_count > 0:
                    self.using_tree_sitter = True
                    self.logger.info(
                        "Successfully initialized %s parsers using tree-sitter-language-pack",
                        initialized_count,
                    )
                else:
                    self.logger.warning(
                        "Failed to initialize any parsers with tree-sitter-language-pack"
                    )
            else:
                self.logger.warning(
                    "tree-sitter-language-pack doesn't have get_language function"
                )

        except ImportError as e:
            self.logger.warning(
                "Failed to import tree-sitter or tree-sitter-language-pack: %s", e
            )
            self.logger.warning(
                "Will use simple parsing instead of tree-sitter for code structure extraction"
            )
        except Exception as e:
            self.logger.warning("Error initializing parsers: %s", e)
            self.logger.warning(
                "Will use simple parsing instead of tree-sitter for code structure extraction"
            )

        if not self.using_tree_sitter:
            self.logger.warning(
                "Tree-sitter not available or initialization failed. Using simple parsing instead."
            )

    def parse_file(self, file_path: str, extension: str) -> dict[str, Any]:
        """Parse a single file and extract its code structure.

        Args:
            file_path: Path to the file
            extension: File extension

        Returns:
            Dictionary containing the code structure
        """
        from ..parsers.simple_parser import extract_code_elements_simple

        self.logger.debug("Processing file: %s", file_path)

        # Return empty structure when tree-sitter is disabled
        if not self.using_tree_sitter:
            return {
                "functions": [],
                "classes": [],
                "imports": [],
                "comments": [],
            }

        # Read file content
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Identify language
        lang_id = self.SUPPORTED_LANGUAGES[extension]
        # Convert language ID to the format used in the parsers dictionary
        lang_name = {
            "python": "Python",
            "javascript": "JavaScript",
            "typescript": "TypeScript",
            "csharp": "C#",
            "java": "Java",
        }.get(lang_id)

        self.logger.debug("File language: %s -> %s", lang_id, lang_name)

        # Try tree-sitter parsing first if available
        if self.using_tree_sitter and lang_name in self.parsers:
            try:
                result = self._parse_with_tree_sitter(file_path, content, lang_name)
                if result:
                    return result
            except Exception as e:
                self.logger.warning(
                    "Tree-sitter parsing failed for %s: %s", file_path, e
                )

        # Fall back to simple parsing
        self.logger.debug("Using simple parsing for %s", file_path)
        return extract_code_elements_simple(content, self.logger)

    def _parse_with_tree_sitter(
        self, file_path: str, content: str, lang_name: str
    ) -> Optional[dict[str, Any]]:
        """Parse a file using tree-sitter.

        Args:
            file_path: Path to the file
            content: Content of the file
            lang_name: Language name

        Returns:
            Dictionary containing the code structure, or None if parsing fails
        """
        self.logger.debug("Using tree-sitter to parse %s", file_path)
        language_parser = get_language_parser(lang_name.lower(), self.logger)

        if not language_parser:
            self.logger.warning("No parser available for %s", lang_name)
            return None

        result = language_parser.extract_elements(content, self.parsers[lang_name])
        self.logger.debug("Tree-sitter parsing result: %s", result)
        return result

    def filter_comments(self, elements: dict[str, Any]) -> dict[str, Any]:
        """Filter out comments from code elements.

        Args:
            elements: Dictionary of code elements

        Returns:
            Dictionary of code elements with comments removed
        """
        # Create a new language parser instance for filtering
        if elements and "comments" in elements:
            language_parser = get_language_parser(
                "python", self.logger
            )  # Default to Python parser
            if language_parser:
                return language_parser.filter_comments(elements)
        return elements
