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

            # First identify all classes and their ranges to detect nesting
            class_ranges = {}

            for node in class_nodes:
                name_node = self._find_child(node, "identifier")
                if name_node:
                    name = content[name_node.start_byte : name_node.end_byte]
                    class_ranges[name] = (node.start_byte, node.end_byte)

            # Process each class, checking for nesting
            for node in class_nodes:
                name_node = self._find_child(node, "identifier")
                if name_node:
                    name = content[name_node.start_byte : name_node.end_byte]
                    class_info = {
                        "name": name,
                    }

                    # Check if this is a nested class
                    parent = node.parent
                    while parent:
                        if parent.type == "declaration_list":
                            # This might be a nested class
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
                                    class_info["type"] = "nested_class"
                                break
                        parent = parent.parent

                    # If not a nested class, check for modifiers to identify static classes
                    if "type" not in class_info:
                        modifier_node = self._find_child(node, "modifier")
                        if (
                            modifier_node
                            and "static"
                            in content[
                                modifier_node.start_byte : modifier_node.end_byte
                            ]
                        ):
                            class_info["type"] = "static_class"
                        else:
                            class_info["type"] = "class"

                    elements["classes"].append(class_info)
        except Exception as e:
            self.logger.error("Error extracting C# classes: %s", e)

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
                        if parent.type == "declaration_list":
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
                    modifier_node = self._find_child(node, "modifier")
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
                        if parent.type == "declaration_list":
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

            # Process property declarations
            for node in property_nodes:
                name_node = self._find_child(node, "identifier")
                if name_node:
                    property_name = content[name_node.start_byte : name_node.end_byte]

                    property_info = {
                        "name": property_name,
                        "type": "property",
                    }

                    # Find parent class
                    parent_class = None
                    parent = node.parent
                    while parent:
                        if parent.type == "declaration_list":
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
                                    property_info["class"] = parent_class
                            break
                        parent = parent.parent

                    # Check if property has getter and/or setter
                    accessors = []
                    accessor_list = self._find_child(node, "accessor_list")
                    if accessor_list:
                        for child in accessor_list.children:
                            if (
                                child.type == "accessor_declaration"
                                and child.child_count > 0
                            ):
                                accessor_type = child.children[0]
                                if accessor_type.type == "get":
                                    accessors.append("get")
                                elif accessor_type.type == "set":
                                    accessors.append("set")

                    if accessors:
                        property_info["accessors"] = accessors

                    elements["functions"].append(property_info)
        except Exception as e:
            self.logger.error("Error extracting C# methods and properties: %s", e)

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
            # Find comments
            comment_nodes = (
                self._query_nodes(root_node, "comment")
                + self._query_nodes(root_node, "line_comment")
                + self._query_nodes(root_node, "block_comment")
            )

            # If no comment nodes found using tree-sitter, try manual extraction
            if not comment_nodes:
                self.logger.debug(
                    "No C# comment nodes found, trying manual comment extraction"
                )

                # Find line comments (//)
                line_comments = []
                for m in re.finditer(r"//.*?$", content, re.MULTILINE):
                    line_comments.append((m.start(), m.end()))

                # Find block comments (/* ... */)
                block_comments = []
                for m in re.finditer(r"/\*.*?\*/", content, re.DOTALL):
                    block_comments.append((m.start(), m.end()))

                # Find XML doc comments (///)
                xml_doc_comments = []
                # This regex is simplified - proper XML doc comments can span multiple lines
                # and have specific XML tags
                for m in re.finditer(r"///.*?$", content, re.MULTILINE):
                    xml_doc_comments.append((m.start(), m.end()))

                # Convert to comment objects
                for start, end in line_comments:
                    text = content[start:end]
                    elements["comments"].append({"text": text, "type": "line_comment"})

                for start, end in block_comments:
                    text = content[start:end]
                    elements["comments"].append({"text": text, "type": "block_comment"})

                # Extract XML doc comments
                for start, end in xml_doc_comments:
                    text = content[start:end]
                    elements["comments"].append(
                        {"text": text, "type": "xml_doc_comment"}
                    )

                # Return early since we've handled comments manually
                return

            # Process tree-sitter comment nodes
            for node in comment_nodes:
                try:
                    comment_text = content[node.start_byte : node.end_byte]
                    comment_info = {
                        "text": comment_text,
                        "type": "comment",
                    }

                    # Detect comment type
                    if comment_text.startswith("///"):
                        comment_info["type"] = "xml_doc_comment"

                        # Try to associate the XML doc with the following code element
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
                            elif next_sibling.type == "property_declaration":
                                name_node = self._find_child(next_sibling, "identifier")
                                if name_node:
                                    comment_info["associated_with"] = content[
                                        name_node.start_byte : name_node.end_byte
                                    ]
                                    comment_info["associated_type"] = "property"
                    elif comment_text.startswith("//"):
                        comment_info["type"] = "line_comment"
                    elif comment_text.startswith("/*"):
                        comment_info["type"] = "block_comment"

                    elements["comments"].append(comment_info)
                except Exception as e:
                    self.logger.error("Error processing C# comment: %s", e)
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
            self.logger.error("Error extracting C# comments: %s", e)
