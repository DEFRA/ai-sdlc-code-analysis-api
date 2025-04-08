import logging
from typing import Any, Optional


class BaseLanguageParser:
    """Base class for language-specific parsers"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the language parser

        Args:
            logger: Logger instance to use for logging
        """
        self.logger = logger or logging.getLogger(__name__)

    def extract_elements(self, content: str, parser) -> dict[str, Any]:
        """Extract code elements using tree-sitter parsing

        Args:
            content: Source code content to parse
            parser: Tree-sitter parser instance

        Returns:
            Dictionary of code elements (functions, classes, imports, comments)
        """
        error_msg = "Subclasses must implement extract_elements"
        raise NotImplementedError(error_msg)

    def filter_comments(self, elements: dict[str, Any]) -> dict[str, Any]:
        """Filter out comments from code elements.

        Args:
            elements: Dictionary of code elements

        Returns:
            Dictionary of code elements with comments removed
        """
        filtered = elements.copy()
        filtered["comments"] = []  # Remove all comments
        return filtered

    def _query_nodes(self, node, type_name: str) -> list:
        """Find all nodes of a specific type in the syntax tree

        Args:
            node: Root node to search from
            type_name: Type of node to search for

        Returns:
            List of matching nodes
        """
        nodes = []

        def visit(node):
            if node.type == type_name and not node.has_error:
                nodes.append(node)
            for child in node.children:
                visit(child)

        visit(node)
        return nodes

    def _find_child(self, node, type_name: str):
        """Find the first child node of a specific type

        Args:
            node: Parent node
            type_name: Type of child node to find

        Returns:
            Child node if found, None otherwise
        """
        for child in node.children:
            if child.type == type_name and not child.has_error:
                return child
        return None
