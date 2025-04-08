from typing import Any

from .base_parser import BaseLanguageParser


class JavaParser(BaseLanguageParser):
    """Parser for Java code"""

    def extract_elements(self, content: str, parser) -> dict[str, Any]:
        """Extract code elements from Java code

        Args:
            content: Source code content
            parser: Tree-sitter parser configured for Java

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

            # Extract code elements using improved methods
            self._extract_classes(content, root_node, elements)
            self._extract_methods(content, root_node, elements)
            self._extract_imports(content, root_node, elements)
            self._extract_comments(content, root_node, elements)
        except Exception as e:
            self.logger.error("Error parsing Java code: %s", e)
            # Return empty elements on error
            return elements

        return elements

    def _extract_classes(self, content: str, root_node, elements: dict[str, Any]):
        """Extract Java classes, including nested and inner classes"""
        try:
            # First find all class declarations
            class_nodes = self._query_nodes(root_node, "class_declaration")

            # Map to track parent-child relationships between classes
            class_ranges = {}  # Store byte ranges to detect nesting

            # First, collect all classes and their ranges
            for node in class_nodes:
                name_node = self._find_child(node, "identifier")
                if name_node:
                    name = content[name_node.start_byte : name_node.end_byte]
                    class_ranges[name] = (node.start_byte, node.end_byte)

            # Now process each class, checking for nesting
            for node in class_nodes:
                name_node = self._find_child(node, "identifier")
                if name_node:
                    name = content[name_node.start_byte : name_node.end_byte]
                    class_info = {
                        "name": name,
                    }

                    # Check if this is a nested class by examining its parent nodes
                    parent = node.parent
                    while parent:
                        if parent.type == "class_body":
                            # This class might be nested inside another class
                            parent_class = parent.parent
                            if (
                                parent_class
                                and parent_class.type == "class_declaration"
                            ):
                                parent_name_node = self._find_child(
                                    parent_class, "identifier"
                                )
                                if parent_name_node:
                                    parent_name = content[
                                        parent_name_node.start_byte : parent_name_node.end_byte
                                    ]
                                    class_info["parent_class"] = parent_name
                                    # Check if it's a static nested class
                                    modifiers = self._query_nodes(node, "modifiers")
                                    for mod in modifiers:
                                        if (
                                            "static"
                                            in content[mod.start_byte : mod.end_byte]
                                        ):
                                            class_info["type"] = "static_nested_class"
                                            break
                                    else:
                                        class_info["type"] = "inner_class"
                                break
                        parent = parent.parent

                    # If no parent was found, it's a top-level class
                    if "type" not in class_info:
                        class_info["type"] = "class"

                    elements["classes"].append(class_info)
        except Exception as e:
            self.logger.error("Error extracting Java classes: %s", e)

    def _extract_methods(self, content: str, root_node, elements: dict[str, Any]):
        """Extract Java methods and constructors with type information"""
        try:
            # Process both regular methods and constructors
            method_nodes = self._query_nodes(root_node, "method_declaration")
            constructor_nodes = self._query_nodes(root_node, "constructor_declaration")

            # Get class ranges to associate methods with their classes
            class_nodes = self._query_nodes(root_node, "class_declaration")
            class_ranges = {}

            for node in class_nodes:
                name_node = self._find_child(node, "identifier")
                if name_node:
                    class_name = content[name_node.start_byte : name_node.end_byte]
                    class_ranges[class_name] = (node.start_byte, node.end_byte)

            # Process method declarations
            for node in method_nodes:
                name_node = self._find_child(node, "identifier")
                if name_node:
                    method_name = content[name_node.start_byte : name_node.end_byte]

                    method_info = {
                        "name": method_name,
                        "type": "method",
                    }

                    # Find parent class
                    parent_class = None
                    parent = node.parent
                    while parent:
                        if parent.type == "class_body":
                            class_parent = parent.parent
                            if (
                                class_parent
                                and class_parent.type == "class_declaration"
                            ):
                                class_name_node = self._find_child(
                                    class_parent, "identifier"
                                )
                                if class_name_node:
                                    parent_class = content[
                                        class_name_node.start_byte : class_name_node.end_byte
                                    ]
                                    method_info["class"] = parent_class
                            break
                        parent = parent.parent

                    # Check for static methods
                    modifier_node = self._find_child(node, "modifiers")
                    if (
                        modifier_node
                        and "static"
                        in content[modifier_node.start_byte : modifier_node.end_byte]
                    ):
                        method_info["static"] = True

                    elements["functions"].append(method_info)

            # Process constructor declarations
            for node in constructor_nodes:
                name_node = self._find_child(node, "identifier")
                if name_node:
                    constructor_name = content[
                        name_node.start_byte : name_node.end_byte
                    ]

                    constructor_info = {
                        "name": constructor_name,
                        "type": "constructor",
                    }

                    # Find parent class
                    parent_class = None
                    parent = node.parent
                    while parent:
                        if parent.type == "class_body":
                            class_parent = parent.parent
                            if (
                                class_parent
                                and class_parent.type == "class_declaration"
                            ):
                                class_name_node = self._find_child(
                                    class_parent, "identifier"
                                )
                                if class_name_node:
                                    parent_class = content[
                                        class_name_node.start_byte : class_name_node.end_byte
                                    ]
                                    constructor_info["class"] = parent_class
                            break
                        parent = parent.parent

                    elements["functions"].append(constructor_info)
        except Exception as e:
            self.logger.error("Error extracting Java methods: %s", e)

    def _extract_imports(self, content: str, root_node, elements: dict[str, Any]):
        """Extract Java import declarations"""
        try:
            # Find import declarations
            import_nodes = self._query_nodes(root_node, "import_declaration")
            for node in import_nodes:
                elements["imports"].append(
                    {
                        "text": content[node.start_byte : node.end_byte],
                    }
                )
        except Exception as e:
            self.logger.error("Error extracting Java imports: %s", e)

    def _extract_comments(self, content: str, root_node, elements: dict[str, Any]):
        """Extract Java comments, differentiating between regular comments and JavaDoc"""
        try:
            # Find all comments - Java handles comments differently, try multiple approaches
            comment_nodes = []

            # Try standard comment node
            comment_nodes.extend(self._query_nodes(root_node, "comment"))

            # Try line_comment and block_comment for Java
            comment_nodes.extend(self._query_nodes(root_node, "line_comment"))
            comment_nodes.extend(self._query_nodes(root_node, "block_comment"))

            # Process comment nodes found by tree-sitter
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
                        comment_info["type"] = "javadoc_comment"

                        # Try to associate JavaDoc with the following code element
                        next_sibling = node.next_sibling
                        if next_sibling:
                            if next_sibling.type == "class_declaration":
                                name_node = self._find_child(next_sibling, "identifier")
                                if name_node:
                                    comment_info["associated_with"] = content[
                                        name_node.start_byte : name_node.end_byte
                                    ]
                                    comment_info["associated_type"] = "class"
                            elif next_sibling.type == "method_declaration":
                                name_node = self._find_child(next_sibling, "identifier")
                                if name_node:
                                    comment_info["associated_with"] = content[
                                        name_node.start_byte : name_node.end_byte
                                    ]
                                    comment_info["associated_type"] = "method"
                            elif next_sibling.type == "constructor_declaration":
                                name_node = self._find_child(next_sibling, "identifier")
                                if name_node:
                                    comment_info["associated_with"] = content[
                                        name_node.start_byte : name_node.end_byte
                                    ]
                                    comment_info["associated_type"] = "constructor"

                    elements["comments"].append(comment_info)
                except Exception as e:
                    self.logger.error("Error processing Java comment: %s", e)
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
            self.logger.error("Error extracting Java comments: %s", e)
