from typing import Any

from .base_parser import BaseLanguageParser


class PythonParser(BaseLanguageParser):
    """Parser for Python code"""

    def extract_elements(self, content: str, parser) -> dict[str, Any]:
        """Extract code elements from Python code

        Args:
            content: Python source code
            parser: Tree-sitter parser configured for Python

        Returns:
            Dictionary of code elements
        """
        elements = {"functions": [], "classes": [], "imports": [], "comments": []}

        # Limit content size to prevent processing huge files
        if len(content) > 1_000_000:  # 1MB limit
            content = content[:1_000_000]
            self.logger.warning("File content truncated due to large size")

        # Parse the content
        tree = parser.parse(bytes(content, "utf8"))
        root_node = tree.root_node
        self.parser = parser  # Store the parser for use in other methods

        # Extract functions
        self._extract_functions(content, root_node, parser, elements)

        # Extract classes
        self._extract_classes(content, root_node, parser, elements)

        # Extract imports
        self._extract_imports(content, root_node, parser, elements)

        # Extract comments
        self._extract_comments(content, root_node, parser, elements)

        return elements

    def _extract_functions(self, content: str, root_node, _, elements: dict[str, Any]):
        """Extract Python functions using tree-sitter queries"""
        try:
            function_captures, method_captures = self._get_function_method_captures(
                root_node
            )

            # Process captured data
            function_names, method_names, class_method_map = (
                self._process_function_captures(
                    content, function_captures, method_captures
                )
            )

            # Combine functions and methods
            elements["functions"] = list(function_names.values()) + list(
                method_names.values()
            )

            # Fall back to direct node traversal if class query didn't work well
            if not method_names:
                self._extract_methods_fallback(content, root_node, elements)

        except Exception as e:
            self.logger.error("Error creating function/method query: %s", e)
            # Fall back to simple parsing for functions and methods
            self.logger.debug("Falling back to simple parsing for functions/methods")
            self._extract_methods_fallback(content, root_node, elements)

    def _get_function_method_captures(self, root_node):
        """Get captures for functions and methods"""
        function_query_string = """
        (function_definition
            name: (identifier) @function.name)
        """

        method_query_string = """
        (class_definition
            name: (identifier) @class.name
            body: (block
                (function_definition
                    name: (identifier) @method.name)))
        """

        # Process standalone functions
        function_query = self.parser.language.query(function_query_string)
        function_captures = function_query.captures(root_node)
        self.logger.debug("Function captures: %s", function_captures)

        # Process class methods
        method_query = self.parser.language.query(method_query_string)
        method_captures = method_query.captures(root_node)
        self.logger.debug("Method captures: %s", method_captures)

        return function_captures, method_captures

    def _process_function_captures(self, content, function_captures, method_captures):
        """Process function and method captures to extract function info"""
        function_names = {}  # Use a dict to deduplicate functions
        method_names = {}  # Use a dict to deduplicate methods
        class_method_map = {}  # Map to associate methods with their parent classes
        current_class = None

        # First, process standalone functions
        for capture in function_captures:
            function_info = self._process_function_capture(content, capture)
            if function_info:
                name = function_info["name"]
                function_names[name] = function_info

        # Then, process methods and organize by class
        for capture in method_captures:
            self._process_method_capture(
                content, capture, method_names, class_method_map, current_class
            )

        return function_names, method_names, class_method_map

    def _process_function_capture(self, content, capture):
        """Process a single function capture"""
        node, capture_name = capture

        if capture_name == "function.name":
            # Check if this function is not inside a class definition
            parent = node.parent
            is_method = False
            while parent:
                if parent.type == "class_definition":
                    is_method = True
                    break
                parent = parent.parent

            # Only add standalone functions, not methods
            if not is_method:
                name = content[node.start_byte : node.end_byte]
                self.logger.debug("Found function: %s", name)
                return {
                    "name": name,
                    "type": "function",
                }

        return None

    def _process_method_capture(
        self, content, capture, method_names, class_method_map, current_class
    ):
        """Process a single method capture"""
        node, capture_name = capture

        if capture_name == "class.name":
            name = content[node.start_byte : node.end_byte]
            current_class = name
            class_method_map[current_class] = []

        elif capture_name == "method.name" and current_class:
            name = content[node.start_byte : node.end_byte]
            self.logger.debug("Found method: %s in class: %s", name, current_class)

            method_info = {
                "name": name,
                "type": "method",
                "class": current_class,
            }

            # Add to both collections
            method_names[f"{current_class}.{name}"] = method_info
            if current_class in class_method_map:
                class_method_map[current_class].append(method_info)

    def _extract_methods_fallback(
        self, content: str, root_node, elements: dict[str, Any]
    ):
        """Fallback method to extract Python functions and methods using direct tree traversal"""
        # Process all function definitions
        function_nodes = self._query_nodes(root_node, "function_definition")

        # First identify all classes
        class_nodes = self._query_nodes(root_node, "class_definition")
        class_ranges = {}

        for node in class_nodes:
            name_node = self._find_child(node, "identifier")
            if name_node:
                class_name = content[name_node.start_byte : name_node.end_byte]
                class_ranges[class_name] = (node.start_byte, node.end_byte)

        # Then process functions, checking if they're within class ranges
        for node in function_nodes:
            name_node = self._find_child(node, "identifier")
            if name_node:
                name = content[name_node.start_byte : name_node.end_byte]
                start_pos = node.start_byte

                # Check if this function is inside a class
                is_method = False
                parent_class = None

                for class_name, (class_start, class_end) in class_ranges.items():
                    if start_pos > class_start and start_pos < class_end:
                        is_method = True
                        parent_class = class_name
                        break

                if is_method and parent_class:
                    self.logger.debug(
                        "Found method (fallback): %s in class %s", name, parent_class
                    )
                    elements["functions"].append(
                        {
                            "name": name,
                            "type": "method",
                            "class": parent_class,
                        }
                    )
                else:
                    self.logger.debug("Found function (fallback): %s", name)
                    elements["functions"].append(
                        {
                            "name": name,
                            "type": "function",
                        }
                    )

    def _extract_classes(self, content: str, root_node, _, elements: dict[str, Any]):
        """Extract Python classes using tree-sitter queries"""
        try:
            # Extract class information
            processed_classes = self._extract_top_level_classes(
                content, root_node, elements
            )

            # Extract nested classes
            self._extract_nested_classes(
                content, root_node, elements, processed_classes
            )

        except Exception as e:
            self.logger.error("Error creating class query: %s", e)
            # Fall back to simple parsing for classes
            self.logger.debug("Falling back to simple parsing for classes")
            self._extract_classes_fallback(content, root_node, elements)

    def _extract_top_level_classes(self, content, root_node, elements):
        """Extract top-level classes from the AST"""
        class_nodes = self._query_nodes(root_node, "class_definition")
        processed_classes = set()

        for node in class_nodes:
            name_node = self._find_child(node, "identifier")
            if name_node:
                name = content[name_node.start_byte : name_node.end_byte]
                self.logger.debug("Found class: %s", name)

                if name not in processed_classes:
                    elements["classes"].append(
                        {
                            "name": name,
                            "type": "class",
                        }
                    )
                    processed_classes.add(name)

        return processed_classes

    def _extract_nested_classes(self, content, root_node, elements, processed_classes):
        """Extract nested classes from within other classes"""
        class_nodes = self._query_nodes(root_node, "class_definition")

        for class_node in class_nodes:
            body_node = self._find_child(class_node, "block")
            if body_node:
                # Look for class definitions within this block
                nested_class_nodes = self._query_nodes(body_node, "class_definition")

                for nested_node in nested_class_nodes:
                    self._process_nested_class_node(
                        content, nested_node, class_node, elements, processed_classes
                    )

    def _process_nested_class_node(
        self, content, nested_node, parent_class_node, elements, processed_classes
    ):
        """Process a single nested class node"""
        name_node = self._find_child(nested_node, "identifier")
        if name_node:
            name = content[name_node.start_byte : name_node.end_byte]
            self.logger.debug("Found nested class: %s", name)

            if name not in processed_classes:
                # Get parent class name
                parent_class_name = content[
                    self._find_child(
                        parent_class_node, "identifier"
                    ).start_byte : self._find_child(
                        parent_class_node, "identifier"
                    ).end_byte
                ]

                elements["classes"].append(
                    {
                        "name": name,
                        "type": "class",
                        "parent_class": parent_class_name,
                    }
                )
                processed_classes.add(name)

    def _extract_classes_fallback(self, content, root_node, elements):
        """Fallback method to extract classes using simple parsing"""
        class_nodes = self._query_nodes(root_node, "class_definition")
        for node in class_nodes:
            name_node = self._find_child(node, "identifier")
            if name_node:
                name = content[name_node.start_byte : name_node.end_byte]
                self.logger.debug("Found class (fallback): %s", name)
                elements["classes"].append(
                    {
                        "name": name,
                        "type": "class",
                    }
                )

    def _extract_imports(self, content: str, root_node, _, elements: dict[str, Any]):
        """Extract Python imports using tree-sitter queries"""
        query_string = """
        (import_statement
            name: (dotted_name) @import.name)
        (import_from_statement
            module_name: (dotted_name)? @from.module
            name: (dotted_name) @import.name)
        """
        try:
            query = self.parser.language.query(query_string)
            captures = query.captures(root_node)
            self.logger.debug("Import captures: %s", captures)

            # Process import captures
            for capture in captures:
                node = capture[0]
                elements["imports"].append(
                    {
                        "text": content[node.start_byte : node.end_byte],
                        "type": "import",
                    }
                )
        except Exception as e:
            self.logger.error("Error creating import query: %s", e)

    def _extract_comments(self, content: str, root_node, _, elements: dict[str, Any]):
        """Extract Python comments and docstrings using tree-sitter queries"""
        # Query for basic comments - simplify to avoid errors
        try:
            # First extract regular comments
            for node in self._query_nodes(root_node, "comment"):
                try:
                    text = content[node.start_byte : node.end_byte]
                    elements["comments"].append(
                        {
                            "text": text,
                            "type": "comment",
                        }
                    )
                except Exception as e:
                    self.logger.debug("Error processing comment node: %s", e)

            # Then extract docstrings separately
            self._extract_docstrings(content, root_node, elements)

        except Exception as e:
            self.logger.error("Error extracting comments: %s", e)

    def _extract_docstrings(self, content: str, root_node, elements: dict[str, Any]):
        """Extract docstrings from Python code"""
        try:
            # Find all string nodes that could be docstrings
            string_nodes = self._query_nodes(root_node, "string")

            for node in string_nodes:
                try:
                    self._process_potential_docstring(content, node, elements)
                except Exception as e:
                    self.logger.debug("Error processing possible docstring node: %s", e)
        except Exception as e:
            self.logger.error("Error extracting docstrings: %s", e)

    def _process_potential_docstring(self, content, node, elements):
        """Process a node that could potentially be a docstring"""
        # Check if parent is expression_statement
        parent = node.parent
        if parent and parent.type == "expression_statement":
            # Check if this is the first statement in a block/module
            grandparent = parent.parent
            if (
                grandparent
                and grandparent.type in ("block", "module")
                and self._is_docstring(parent, grandparent)
            ):
                text = content[node.start_byte : node.end_byte]
                elements["comments"].append(
                    {
                        "text": text,
                        "type": "docstring",
                    }
                )

    def _is_docstring(self, parent_node, grandparent_node):
        """Determine if a string is actually a docstring based on its position"""
        # If it's the first statement in a module, it's a module docstring
        if (
            grandparent_node.type == "module"
            and parent_node == grandparent_node.children[0]
        ):
            return True

        # If it's in a block, check if it's the first statement
        if grandparent_node.type == "block":
            # Get index of the expression statement
            for i, child in enumerate(grandparent_node.children):
                if child == parent_node and i == 0:
                    # It's the first statement in the block
                    return True

        return False
