import re
from typing import Any

from .base_parser import BaseLanguageParser


class CSharpParser(BaseLanguageParser):
    """Parser for C# code"""

    def extract_elements(self, content: str, parser) -> dict[str, Any]:
        """Extract code elements from C# code

        Args:
            content: Source code content
            parser: Tree-sitter parser configured for C#

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
            self._extract_methods_and_properties(content, root_node, elements)
            self._extract_imports(content, root_node, elements)
            self._extract_comments(content, root_node, elements)
        except Exception as e:
            self.logger.error("Error parsing C# code: %s", e)
            # Return empty elements on error
            return elements

        return elements

    def _extract_classes(self, content: str, root_node, elements: dict[str, Any]):
        """Extract C# classes, including nested classes"""
        try:
            # Find class declarations
            class_nodes = self._query_nodes(root_node, "class_declaration")

            # Process each class, checking for nesting
            for node in class_nodes:
                self._process_class_node(node, content, elements)

        except Exception as e:
            self.logger.error("Error extracting C# classes: %s", e)

    def _process_class_node(self, node, content, elements):
        """Process a single class node and add it to elements."""
        name_node = self._find_child(node, "identifier")
        if not name_node:
            return

        name = content[name_node.start_byte : name_node.end_byte]
        class_info = {
            "name": name,
        }

        # Check if this is a nested class
        parent_class = self._find_parent_class_name(node, content)
        if parent_class:
            class_info["parent_class"] = parent_class
            class_info["type"] = "nested_class"
        else:
            # If not a nested class, check for modifiers to identify static classes
            class_info["type"] = self._determine_class_type(node, content)

        elements["classes"].append(class_info)

    def _find_parent_class_name(self, node, content):
        """Find the parent class name for a potentially nested class."""
        parent = node.parent
        while parent:
            if parent.type == "declaration_list":
                # This might be a nested class
                parent_class = parent.parent
                if parent_class and parent_class.type == "class_declaration":
                    parent_name_node = self._find_child(parent_class, "identifier")
                    if parent_name_node:
                        return content[
                            parent_name_node.start_byte : parent_name_node.end_byte
                        ]
                    break
            parent = parent.parent
        return None

    def _determine_class_type(self, node, content):
        """Determine the type of class (static or regular) based on modifiers."""
        modifier_node = self._find_child(node, "modifier")
        if (
            modifier_node
            and "static" in content[modifier_node.start_byte : modifier_node.end_byte]
        ):
            return "static_class"
        return "class"

    def _extract_methods_and_properties(
        self, content: str, root_node, elements: dict[str, Any]
    ):
        """Extract C# methods, constructors, and properties"""
        try:
            # Extract methods
            method_nodes = self._query_nodes(root_node, "method_declaration")
            constructor_nodes = self._query_nodes(root_node, "constructor_declaration")
            property_nodes = self._query_nodes(root_node, "property_declaration")

            # Process method declarations
            for node in method_nodes:
                self._process_method_node(node, content, elements)

            # Process constructor declarations
            for node in constructor_nodes:
                self._process_constructor_node(node, content, elements)

            # Process property declarations
            for node in property_nodes:
                self._process_property_node(node, content, elements)

        except Exception as e:
            self.logger.error("Error extracting C# methods and properties: %s", e)

    def _process_method_node(self, node, content, elements):
        """Process a C# method node and add it to the elements dictionary"""
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
        modifier_node = self._find_child(node, "modifier")
        if (
            modifier_node
            and "static" in content[modifier_node.start_byte : modifier_node.end_byte]
        ):
            method_info["static"] = True

        elements["functions"].append(method_info)

    def _process_constructor_node(self, node, content, elements):
        """Process a C# constructor node and add it to the elements dictionary"""
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

    def _process_property_node(self, node, content, elements):
        """Process a C# property node and add it to the elements dictionary"""
        name_node = self._find_child(node, "identifier")
        if not name_node:
            return

        property_name = content[name_node.start_byte : name_node.end_byte]
        property_info = {
            "name": property_name,
            "type": "property",
        }

        # Find parent class
        parent_class = self._find_parent_class(node, content)
        if parent_class:
            property_info["class"] = parent_class

        # Check if property has getter and/or setter
        self._add_property_accessors(node, property_info)

        elements["functions"].append(property_info)

    def _find_parent_class(self, node, content):
        """Find the parent class of a node"""
        parent = node.parent
        while parent:
            if parent.type == "declaration_list":
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

    def _add_property_accessors(self, node, property_info):
        """Add accessor information to a property info dictionary"""
        accessors = []
        accessor_list = self._find_child(node, "accessor_list")
        if accessor_list:
            for child in accessor_list.children:
                if child.type == "accessor_declaration" and child.child_count > 0:
                    accessor_type = child.children[0]
                    if accessor_type.type == "get":
                        accessors.append("get")
                    elif accessor_type.type == "set":
                        accessors.append("set")

        if accessors:
            property_info["accessors"] = accessors

    def _extract_imports(self, content: str, root_node, elements: dict[str, Any]):
        """Extract C# using directives (imports)"""
        try:
            # Find using directives (imports)
            import_nodes = self._query_nodes(root_node, "using_directive")
            for node in import_nodes:
                elements["imports"].append(
                    {
                        "text": content[node.start_byte : node.end_byte],
                    }
                )
        except Exception as e:
            self.logger.error("Error extracting C# imports: %s", e)

    def _extract_comments(self, content: str, root_node, elements: dict[str, Any]):
        """Extract C# comments, differentiating between regular comments and XML doc comments"""
        try:
            # Track processed comment ranges to avoid duplicates
            processed_ranges = set()

            # Look for both line comments and block comments
            line_comment_nodes = self._query_nodes(root_node, "line_comment")
            block_comment_nodes = self._query_nodes(root_node, "comment")

            # Process XML doc comments - first check for triple-slash comments
            # In C#, XML doc comments start with ///
            xml_doc_pattern = r"///.*?$"
            for match in re.finditer(xml_doc_pattern, content, re.MULTILINE):
                comment_text = content[match.start() : match.end()]
                clean_text = comment_text.lstrip("/").strip()
                elements["comments"].append(
                    {"type": "xml_doc_comment", "text": clean_text}
                )
                # Mark this range as processed
                processed_ranges.add((match.start(), match.end()))

            # Process regular comments
            for node in line_comment_nodes:
                # Skip if we've already processed this range
                if (node.start_byte, node.end_byte) in processed_ranges:
                    continue

                comment_text = content[node.start_byte : node.end_byte].strip()
                # Skip XML doc comments as they were handled above
                if not comment_text.startswith("///"):
                    clean_text = comment_text.lstrip("/").strip()
                    elements["comments"].append(
                        {"type": "line_comment", "text": clean_text}
                    )
                # Mark as processed
                processed_ranges.add((node.start_byte, node.end_byte))

            for node in block_comment_nodes:
                # Skip if we've already processed this range
                if (node.start_byte, node.end_byte) in processed_ranges:
                    continue
                self._process_block_comment(node, content, elements)
                processed_ranges.add((node.start_byte, node.end_byte))

        except Exception as e:
            self.logger.error("Error extracting C# comments: %s", e)

    def _process_block_comment(self, node, content, elements):
        """Process a C# block comment and add it to the elements dictionary"""
        comment_text = content[node.start_byte : node.end_byte]

        # Check if it's a documentation block comment
        if comment_text.startswith("/**"):
            # XML doc block comment - clean up
            clean_text = self._clean_doc_block_comment(comment_text)
            elements["comments"].append(
                {"type": "doc_block_comment", "text": clean_text}
            )
        else:
            # Regular block comment - clean up
            clean_text = self._clean_block_comment(comment_text)
            elements["comments"].append({"type": "block_comment", "text": clean_text})

    def _clean_doc_block_comment(self, comment_text):
        """Clean documentation block comments by removing comment markers and preserving XML"""
        # Remove the opening and closing markers
        text = comment_text.strip()
        if text.startswith("/**"):
            text = text[3:]
        if text.endswith("*/"):
            text = text[:-2]

        # Process each line to remove leading asterisks
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith("*"):
                line = line[1:].strip()
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()

    def _clean_block_comment(self, comment_text):
        """Clean regular block comments by removing comment markers"""
        # Remove the opening and closing markers
        text = comment_text.strip()
        if text.startswith("/*"):
            text = text[2:]
        if text.endswith("*/"):
            text = text[:-2]

        # Process each line to remove leading asterisks
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line.startswith("*"):
                line = line[1:].strip()
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines).strip()
