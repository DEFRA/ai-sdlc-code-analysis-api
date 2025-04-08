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

            # Now process each class, checking for nesting
            for node in class_nodes:
                self._process_class_node(node, content, elements)

        except Exception as e:
            self.logger.error("Error extracting Java classes: %s", e)

    def _process_class_node(self, node, content, elements):
        """Process a single Java class node."""
        name_node = self._find_child(node, "identifier")
        if not name_node:
            return

        name = content[name_node.start_byte : name_node.end_byte]
        class_info = {
            "name": name,
        }

        # Check if this is a nested class
        parent_class_info = self._find_parent_class_info(node, content)
        if parent_class_info:
            class_info.update(parent_class_info)
        else:
            # If no parent was found, it's a top-level class
            class_info["type"] = "class"

        elements["classes"].append(class_info)

    def _find_parent_class_info(self, node, content):
        """Find parent class information for a potentially nested class."""
        parent = node.parent
        while parent:
            if parent.type == "class_body":
                # This class might be nested inside another class
                parent_class = parent.parent
                if parent_class and parent_class.type == "class_declaration":
                    parent_name_node = self._find_child(parent_class, "identifier")
                    if parent_name_node:
                        parent_name = content[
                            parent_name_node.start_byte : parent_name_node.end_byte
                        ]
                        result = {"parent_class": parent_name}

                        # Check if it's a static nested class
                        result["type"] = self._determine_class_type(node, content)
                        return result
                break
            parent = parent.parent
        return None

    def _determine_class_type(self, node, content):
        """Determine the type of a nested class (static or inner)."""
        modifiers = self._query_nodes(node, "modifiers")
        for mod in modifiers:
            if "static" in content[mod.start_byte : mod.end_byte]:
                return "static_nested_class"
        return "inner_class"

    def _extract_methods(self, content: str, root_node, elements: dict[str, Any]):
        """Extract Java methods and constructors with type information"""
        try:
            # Process both regular methods and constructors
            method_nodes = self._query_nodes(root_node, "method_declaration")
            constructor_nodes = self._query_nodes(root_node, "constructor_declaration")

            # Process method declarations
            for node in method_nodes:
                self._process_method_node(node, content, elements)

            # Process constructor declarations
            for node in constructor_nodes:
                self._process_constructor_node(node, content, elements)

        except Exception as e:
            self.logger.error("Error extracting Java methods: %s", e)

    def _process_method_node(self, node, content, elements):
        """Process a Java method node and add it to the elements dictionary."""
        name_node = self._find_child(node, "identifier")
        if not name_node:
            return

        method_name = content[name_node.start_byte : name_node.end_byte]

        method_info = {
            "name": method_name,
            "type": "method",
        }

        # Find parent class
        parent_class = self._find_parent_class(node, content)
        if parent_class:
            method_info["class"] = parent_class

        # Check for static methods
        modifier_node = self._find_child(node, "modifiers")
        if (
            modifier_node
            and "static" in content[modifier_node.start_byte : modifier_node.end_byte]
        ):
            method_info["static"] = True

        elements["functions"].append(method_info)

    def _process_constructor_node(self, node, content, elements):
        """Process a Java constructor node and add it to the elements dictionary."""
        name_node = self._find_child(node, "identifier")
        if not name_node:
            return

        constructor_name = content[name_node.start_byte : name_node.end_byte]

        constructor_info = {
            "name": constructor_name,
            "type": "constructor",
        }

        # Find parent class
        parent_class = self._find_parent_class(node, content)
        if parent_class:
            constructor_info["class"] = parent_class

        elements["functions"].append(constructor_info)

    def _find_parent_class(self, node, content):
        """Find the parent class of a method or constructor node."""
        parent = node.parent
        while parent:
            if parent.type == "class_body":
                class_parent = parent.parent
                if class_parent and class_parent.type == "class_declaration":
                    class_name_node = self._find_child(class_parent, "identifier")
                    if class_name_node:
                        return content[
                            class_name_node.start_byte : class_name_node.end_byte
                        ]
                break
            parent = parent.parent
        return None

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
            comment_nodes = self._collect_comment_nodes(root_node)

            # Process comment nodes
            for node in comment_nodes:
                self._process_comment_node(node, content, elements)

        except Exception as e:
            self.logger.error("Error extracting Java comments: %s", e)

    def _collect_comment_nodes(self, root_node):
        """Collect comment nodes from the parse tree."""
        comment_nodes = []

        # Try standard comment node
        comment_nodes.extend(self._query_nodes(root_node, "comment"))

        # Try line_comment and block_comment for Java
        comment_nodes.extend(self._query_nodes(root_node, "line_comment"))
        comment_nodes.extend(self._query_nodes(root_node, "block_comment"))

        return comment_nodes

    def _process_comment_node(self, node, content, elements):
        """Process a single comment node and add it to the elements dictionary."""
        try:
            comment_text = content[node.start_byte : node.end_byte]
            comment_info = {"text": comment_text}

            # Determine comment type
            comment_type = self._determine_comment_type(comment_text)
            if comment_type:
                comment_info["type"] = comment_type

            elements["comments"].append(comment_info)
        except Exception as e:
            self.logger.error("Error processing Java comment: %s", e)

    def _determine_comment_type(self, comment_text):
        """Determine the type of a Java comment."""
        comment_text = comment_text.strip()

        if comment_text.startswith("/**"):
            return "javadoc_comment"
        if comment_text.startswith("/*"):
            return "block_comment"
        if comment_text.startswith("//"):
            return "line_comment"

        return "comment"  # Default type
