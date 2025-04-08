from typing import Any

from .base_parser import BaseLanguageParser


class JavaScriptParser(BaseLanguageParser):
    """Parser for JavaScript and TypeScript code"""

    def extract_elements(self, content: str, parser) -> dict[str, Any]:
        """Extract code elements from JavaScript or TypeScript code

        Args:
            content: Source code content
            parser: Tree-sitter parser configured for JavaScript/TypeScript

        Returns:
            Dictionary of code elements
        """
        elements = {"functions": [], "classes": [], "imports": [], "comments": []}

        # Limit content size
        if len(content) > 1_000_000:  # 1MB limit
            content = content[:1_000_000]
            self.logger.warning("File content truncated due to large size")

        try:
            # Parse the content
            tree = parser.parse(bytes(content, "utf8"))
            root_node = tree.root_node

            # Debug logging
            self.logger.debug(
                "Parsing JavaScript/TypeScript content: %s", content[:100]
            )
            self.logger.debug("Root node type: %s", root_node.type)

            # Extract functions and classes using improved methods
            self._extract_functions_and_methods(content, root_node, elements)
            self.logger.debug("After extracting functions: %s", elements["functions"])

            self._extract_classes(content, root_node, elements)
            self.logger.debug("After extracting classes: %s", elements["classes"])

            self._extract_imports(content, root_node, elements)
            self._extract_comments(content, root_node, elements)

            # Debug logging of final elements
            self.logger.debug("Final extracted elements: %s", elements)
        except Exception as e:
            self.logger.error("Error parsing JavaScript/TypeScript: %s", e)
            # Return empty elements on error
            return elements

        return elements

    def _extract_functions_and_methods(
        self, content: str, root_node, elements: dict[str, Any]
    ):
        """Extract JavaScript/TypeScript functions and methods, with type information"""
        try:
            # Find function definitions including methods, arrow functions
            function_nodes = (
                self._query_nodes(root_node, "function_declaration")
                + self._query_nodes(root_node, "method_definition")
                + self._query_nodes(root_node, "arrow_function")
            )

            # Find class declarations to map methods to their parent classes
            class_nodes = self._query_nodes(root_node, "class_declaration")
            class_ranges = {}

            for node in class_nodes:
                name_node = self._find_child(node, "identifier")
                if name_node:
                    class_name = content[name_node.start_byte : name_node.end_byte]
                    class_ranges[class_name] = (node.start_byte, node.end_byte)

            # Process all functions and methods
            functions_list = []  # Create a list to store all functions
            for node in function_nodes:
                name_node = None
                name = None
                function_type = "function"  # Default type
                parent_class = None

                # Handle different function types
                if node.type == "function_declaration":
                    name_node = self._find_child(node, "identifier")
                    if name_node:
                        name = content[name_node.start_byte : name_node.end_byte]

                elif node.type == "method_definition":
                    name_node = self._find_child(node, "property_identifier")
                    if name_node:
                        name = content[name_node.start_byte : name_node.end_byte]
                        function_type = "method"

                        # Find parent class
                        parent = node.parent
                        while parent:
                            if parent.type == "class_body":
                                class_parent = parent.parent
                                if class_parent.type == "class_declaration":
                                    class_name_node = self._find_child(
                                        class_parent, "identifier"
                                    )
                                    if class_name_node:
                                        parent_class = content[
                                            class_name_node.start_byte : class_name_node.end_byte
                                        ]
                                break
                            parent = parent.parent

                        # Check if it's a constructor method
                        if name == "constructor":
                            function_type = "constructor"

                elif node.type == "arrow_function":
                    # For arrow functions, we need to find the variable name it's assigned to
                    parent = node.parent
                    if parent and parent.type == "variable_declarator":
                        name_node = self._find_child(parent, "identifier")
                        if name_node:
                            name = content[name_node.start_byte : name_node.end_byte]
                            function_type = "arrow_function"

                # If we found a name, add the function/method to our list
                if name:
                    # For arrow functions, use the parent node's position
                    method_info = {
                        "name": name,
                        "type": "method" if function_type == "method" else "function",
                    }

                    # Add class name for methods
                    if function_type == "method":
                        method_info["class"] = parent_class

                    # Add to functions list
                    elements["functions"].append(method_info)

            # Add all functions to the elements dictionary
            self.logger.debug("Extracted functions: %s", functions_list)

        except Exception as e:
            self.logger.error("Error extracting JavaScript/TypeScript functions: %s", e)

    def _extract_classes(self, content: str, root_node, elements: dict[str, Any]):
        """Extract JavaScript/TypeScript classes"""
        try:
            # Find all class declarations and expressions
            class_nodes = self._query_nodes(root_node, "class_declaration")
            class_exp_nodes = self._query_nodes(root_node, "class_expression")

            classes_list = []

            # Process class declarations
            for node in class_nodes + class_exp_nodes:
                name_node = self._find_child(node, "identifier")
                if name_node:
                    name = content[name_node.start_byte : name_node.end_byte]
                    class_info = {
                        "name": name,
                    }
                    classes_list.append(class_info)

            # Add all classes to the elements dictionary
            elements["classes"] = classes_list
            self.logger.debug("Extracted classes: %s", classes_list)

        except Exception as e:
            self.logger.error("Error extracting JavaScript/TypeScript classes: %s", e)

    def _extract_imports(self, content: str, root_node, elements: dict[str, Any]):
        """Extract JavaScript/TypeScript import statements"""
        try:
            # Find import statements
            import_nodes = self._query_nodes(root_node, "import_statement")
            for node in import_nodes:
                elements["imports"].append(
                    {
                        "text": content[node.start_byte : node.end_byte],
                    }
                )
        except Exception as e:
            self.logger.error("Error extracting JavaScript/TypeScript imports: %s", e)

    def _extract_comments(self, content: str, root_node, elements: dict[str, Any]):
        """Extract JavaScript/TypeScript comments, differentiating between regular comments and JSDoc"""
        try:
            # Find all comments (line and block)
            comment_nodes = (
                self._query_nodes(root_node, "comment")
                + self._query_nodes(root_node, "line_comment")
                + self._query_nodes(root_node, "block_comment")
            )

            for node in comment_nodes:
                try:
                    comment_text = content[node.start_byte : node.end_byte]
                    comment_info = {
                        "text": comment_text,
                    }

                    # Identify comment type
                    if comment_text.startswith("//"):
                        comment_info["type"] = "line_comment"
                    elif comment_text.startswith("/*") and not comment_text.startswith(
                        "/**"
                    ):
                        comment_info["type"] = "block_comment"
                    elif comment_text.startswith("/**"):
                        comment_info["type"] = "jsdoc_comment"

                        # Try to associate JSDoc with the following code element
                        next_sibling = node.next_sibling
                        if next_sibling:
                            if next_sibling.type == "function_declaration":
                                name_node = self._find_child(next_sibling, "identifier")
                                if name_node:
                                    comment_info["associated_with"] = content[
                                        name_node.start_byte : name_node.end_byte
                                    ]
                                    comment_info["associated_type"] = "function"
                            elif next_sibling.type == "method_definition":
                                name_node = self._find_child(
                                    next_sibling, "property_identifier"
                                )
                                if name_node:
                                    comment_info["associated_with"] = content[
                                        name_node.start_byte : name_node.end_byte
                                    ]
                                    comment_info["associated_type"] = "method"
                            elif next_sibling.type == "class_declaration":
                                name_node = self._find_child(next_sibling, "identifier")
                                if name_node:
                                    comment_info["associated_with"] = content[
                                        name_node.start_byte : name_node.end_byte
                                    ]
                                    comment_info["associated_type"] = "class"

                    elements["comments"].append(comment_info)
                except Exception as e:
                    self.logger.error("Error processing comment: %s", e)
                    # Add a basic version of the comment if possible
                    try:
                        elements["comments"].append(
                            {
                                "text": content[node.start_byte : node.end_byte],
                            }
                        )
                    except Exception as e:
                        self.logger.debug("Error adding basic comment: %s", e)
        except Exception as e:
            self.logger.error("Error extracting JavaScript/TypeScript comments: %s", e)
