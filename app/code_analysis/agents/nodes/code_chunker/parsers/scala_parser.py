"""Scala parser module with support for functional patterns."""

import re
from typing import Any, Optional

from .base_parser import BaseParser


class ScalaParser(BaseParser):
    """Parser for Scala programming language with support for functional patterns."""

    def __init__(self) -> None:
        """Initialize the Scala parser with functional programming patterns."""
        super().__init__()
        self.language = "scala"
        self.file_extensions = [".scala"]

        # Scala-specific patterns
        self.class_pattern = r"(?:case\s+)?class\s+(\w+)(?:\[.*?\])?\s*(?:extends|\(|{|$)"
        self.object_pattern = r"object\s+(\w+)(?:\s+extends\s+\w+)?\s*\{"
        self.trait_pattern = r"trait\s+(\w+)(?:\[.*?\])?(?:\s+extends\s+\w+)?\s*\{"

        # Enhanced patterns for Cats Effect
        self.effect_type_pattern = (
            r"(?:"
            r"IO\[.*?\]"  # IO type
            r"|F\[.*?\]"  # Generic effect type (common in tagless final)
            r"|Resource\[.*?\]"  # Resource type
            r"|Stream\[.*?\]"  # fs2.Stream
            r"|(?:Async|Sync|Concurrent)\[.*?\]"  # Common type classes
            r")"
        )

        # Update method pattern to better handle effect types
        self.method_pattern = (
            r"(?:"
            r"def\s+(\w+)(?:\[.*?\])?\s*"  # Method name and type params
            r"(?:\(.*?\))?"  # Parameters
            r"(?:\s*:\s*"  # Return type start
            + self.effect_type_pattern  # Effect return type
            + r")??\s*=?"
            r"|val\s+(\w+)(?:\s*:\s*"
            + self.effect_type_pattern
            + r")??\s*=?"  # Val definitions
            r"|var\s+(\w+)(?:\s*:\s*"
            + self.effect_type_pattern
            + r")??\s*=?"  # Var definitions
            r"|for\s*\{([^}]*)\}\s*yield\s*\{"  # For comprehensions
            r"|(?:map|flatMap|filter|fold|reduce|evalMap|parTraverse|parSequence)\s*\{"
            r")"
        )

        # Additional patterns for functional constructs
        self.for_comp_pattern = r"for\s*\{([^}]*)\}\s*yield\s*\{([^}]*)\}"
        self.type_class_pattern = (
            r"implicit\s+(?:class|object)\s+(\w+)(?:\[.*?\])?\s*(?:extends|\(|{|$)"
        )
        self.implicit_pattern = (
            r"implicit\s+(?:val|def)\s+(\w+)(?:\[.*?\])?\s*"
            r"(?:\(.*?\))?(?:\s*:\s*\w+(?:\[.*?\])?)??\s*=?"
        )

        # Pattern for Cats Effect specific constructs
        self.effect_construct_pattern = (
            r"(?:"
            r"IO\.(?:pure|delay|async|defer|race|both|uncancelable)"  # IO constructors
            r"|Resource\.(?:make|eval|pure)"  # Resource constructors
            r"|Stream\.(?:eval|emit|chunk)"  # Stream constructors
            r")\s*\("
        )

        # Pattern for error handling
        self.error_handling_pattern = (
            r"(?:"
            r"\.(?:handleError|handleErrorWith|attempt|recover|recoverWith)"  # Error handlers
            r"|(?:try|catch|finally)\s*\{"  # Try blocks
            r")"
        )

    def extract_imports(self, content: str) -> list[str]:
        """Extract import statements from Scala code, including Cats imports.

        Args:
            content: The source code content to parse.

        Returns:
            List of import statements.
        """
        import_pattern = r"import\s+([^\n;]+)"
        imports = re.finditer(import_pattern, content)
        return [match.group(1).strip() for match in imports]

    def extract_classes(self, content: str) -> list[dict[str, Any]]:
        """Extract class definitions with enhanced Cats Effect support.

        Args:
            content: The source code content to parse.

        Returns:
            List of dictionaries containing class information.
        """
        classes = []

        # Find all class, object, trait, and type class definitions
        for pattern, kind in [
            (self.class_pattern, "class"),
            (self.object_pattern, "object"),
            (self.trait_pattern, "trait"),
            (self.type_class_pattern, "type_class"),
        ]:
            for match in re.finditer(pattern, content, re.MULTILINE):
                class_name = match.group(1)
                start_pos = match.start()

                class_info = self._extract_block_info(content, start_pos)
                if class_info:
                    class_data = {
                        "name": class_name,
                        "type": kind,
                        "start_line": self._get_line_number(content, start_pos),
                        "end_line": self._get_line_number(content, class_info["end_pos"]),
                        "methods": self._extract_methods(class_info["body"]),
                        "content": class_info["body"],
                        "for_comprehensions": self._extract_for_comprehensions(
                            class_info["body"]
                        ),
                        "implicits": self._extract_implicits(class_info["body"]),
                        "effect_patterns": self._extract_effect_patterns(class_info["body"]),
                        "error_handling": self._extract_error_handling(class_info["body"]),
                    }

                    # Extract type parameters and type class constraints
                    type_info = self._extract_type_info(
                        content[start_pos : class_info["end_pos"]]
                    )
                    class_data.update(type_info)

                    classes.append(class_data)

        return classes

    def _extract_methods(self, class_content: str) -> list[dict[str, Any]]:
        """Extract method definitions including functional patterns.

        Args:
            class_content: The class content to parse.

        Returns:
            List of dictionaries containing method information.
        """
        methods = []

        for match in re.finditer(self.method_pattern, class_content, re.MULTILINE):
            method_name = next(name for name in match.groups() if name is not None)
            start_pos = match.start()

            method_info = self._extract_block_info(class_content, start_pos)
            if method_info:
                method_data = {
                    "name": method_name,
                    "start_line": self._get_line_number(class_content, start_pos),
                    "end_line": self._get_line_number(class_content, method_info["end_pos"]),
                    "content": method_info["body"],
                    "is_for_comprehension": bool(
                        re.match(self.for_comp_pattern, class_content[start_pos:])
                    ),
                }

                type_sig = self._extract_type_signature(
                    class_content[start_pos : method_info["end_pos"]]
                )
                if type_sig:
                    method_data["type_signature"] = type_sig

                methods.append(method_data)

        return methods

    def _extract_for_comprehensions(self, content: str) -> list[dict[str, Any]]:
        """Extract for comprehensions from the code.

        Args:
            content: The content to parse.

        Returns:
            List of dictionaries containing for comprehension information.
        """
        comprehensions = []
        for match in re.finditer(self.for_comp_pattern, content, re.MULTILINE):
            start_pos = match.start()
            comprehensions.append(
                {
                    "generators": match.group(1).strip(),
                    "yield": match.group(2).strip(),
                    "start_line": self._get_line_number(content, start_pos),
                    "end_line": self._get_line_number(content, match.end()),
                }
            )
        return comprehensions

    def _extract_implicits(self, content: str) -> list[dict[str, Any]]:
        """Extract implicit definitions.

        Args:
            content: The content to parse.

        Returns:
            List of dictionaries containing implicit information.
        """
        implicits = []
        for match in re.finditer(self.implicit_pattern, content, re.MULTILINE):
            start_pos = match.start()
            implicit_info = self._extract_block_info(content, start_pos)
            if implicit_info:
                implicits.append(
                    {
                        "name": match.group(1),
                        "start_line": self._get_line_number(content, start_pos),
                        "end_line": self._get_line_number(
                            content, implicit_info["end_pos"]
                        ),
                        "content": implicit_info["body"],
                    }
                )
        return implicits

    def _extract_type_parameters(self, content: str) -> Optional[list[str]]:
        """Extract type parameters from class/trait/method definitions.

        Args:
            content: The content to parse.

        Returns:
            List of type parameters if found, None otherwise.
        """
        type_param_pattern = r"\[([\w\s,]+)\]"
        match = re.search(type_param_pattern, content)
        if match:
            return [param.strip() for param in match.group(1).split(",")]
        return None

    def _extract_type_signature(self, content: str) -> Optional[str]:
        """Extract type signature from method definitions.

        Args:
            content: The content to parse.

        Returns:
            Type signature if found, None otherwise.
        """
        type_sig_pattern = (
            r":\s*((?:\w+(?:\[.*?\])?(?:\s*=>\s*\w+(?:\[.*?\])?)*))(?:\s*=|$)"
        )
        match = re.search(type_sig_pattern, content)
        if match:
            return match.group(1).strip()
        return None

    def _extract_block_info(self, content: str, start_pos: int) -> Optional[dict[str, Any]]:
        """Extract a code block starting from a given position.

        Args:
            content: The content to parse.
            start_pos: Starting position in the content.

        Returns:
            Dictionary containing block information if found, None otherwise.
        """
        pos = start_pos
        while pos < len(content) and content[pos] != "{":
            pos += 1

        if pos >= len(content):
            return None

        brace_count = 1
        pos += 1
        start_body = pos

        while pos < len(content) and brace_count > 0:
            if content[pos] == "{":
                brace_count += 1
            elif content[pos] == "}":
                brace_count -= 1
            pos += 1

        if brace_count == 0:
            return {"body": content[start_body : pos - 1].strip(), "end_pos": pos}

        return None

    def _extract_effect_patterns(self, content: str) -> list[dict[str, Any]]:
        """Extract Cats Effect specific patterns and constructs.

        Args:
            content: The content to parse.

        Returns:
            List of dictionaries containing effect pattern information.
        """
        patterns = []
        for match in re.finditer(self.effect_construct_pattern, content, re.MULTILINE):
            start_pos = match.start()
            construct_info = self._extract_block_info(content, start_pos)
            if construct_info:
                patterns.append(
                    {
                        "construct": match.group(0).strip("("),
                        "start_line": self._get_line_number(content, start_pos),
                        "end_line": self._get_line_number(
                            content, construct_info["end_pos"]
                        ),
                        "content": construct_info["body"],
                    }
                )
        return patterns

    def _extract_error_handling(self, content: str) -> list[dict[str, Any]]:
        """Extract error handling patterns.

        Args:
            content: The content to parse.

        Returns:
            List of dictionaries containing error handling information.
        """
        handlers = []
        for match in re.finditer(self.error_handling_pattern, content, re.MULTILINE):
            start_pos = match.start()
            handler_info = self._extract_block_info(content, start_pos)
            if handler_info:
                handlers.append(
                    {
                        "type": match.group(0).strip(".{"),
                        "start_line": self._get_line_number(content, start_pos),
                        "end_line": self._get_line_number(
                            content, handler_info["end_pos"]
                        ),
                        "content": handler_info["body"],
                    }
                )
        return handlers

    def _extract_type_info(self, content: str) -> dict[str, Any]:
        """Extract type parameters and type class constraints.

        Args:
            content: The content to parse.

        Returns:
            Dictionary containing type information.
        """
        type_info = {}

        type_params = self._extract_type_parameters(content)
        if type_params:
            type_info["type_parameters"] = type_params

        constraints_pattern = r"(?:requires|with)\s+((?:\w+(?:\[.*?\])?(?:\s*,\s*\w+(?:\[.*?\])?)*))(?:\s*{|$)"
        match = re.search(constraints_pattern, content)
        if match:
            type_info["type_class_constraints"] = [
                constraint.strip() for constraint in match.group(1).split(",")
            ]

        return type_info
    