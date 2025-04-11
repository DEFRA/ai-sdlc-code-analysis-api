from typing import List, Optional, Tuple, Dict, Any
from .base_parser import BaseParser
import re

class ScalaParser(BaseParser):
    """Parser for Scala programming language."""
    
    def __init__(self):
        super().__init__()
        self.language = "scala"
        self.file_extensions = [".scala"]
        
        # Scala-specific patterns
        self.class_pattern = r"(?:case\s+)?class\s+(\w+)(?:\[.*?\])?\s*(?:extends|\(|{|$)"
        self.object_pattern = r"object\s+(\w+)(?:\s+extends\s+\w+)?\s*\{"
        self.trait_pattern = r"trait\s+(\w+)(?:\[.*?\])?(?:\s+extends\s+\w+)?\s*\{"
        self.method_pattern = r"(?:def|val|var)\s+(\w+)(?:\[.*?\])?\s*(?:\(.*?\))?(?:\s*:\s*\w+(?:\[.*?\])?)??\s*=?"
        
    def extract_imports(self, content: str) -> List[str]:
        """Extract import statements from Scala code."""
        import_pattern = r"import\s+([^\n;]+)"
        imports = re.finditer(import_pattern, content)
        return [match.group(1).strip() for match in imports]

    def extract_classes(self, content: str) -> List[Dict[str, Any]]:
        """Extract class definitions from Scala code."""
        classes = []
        
        # Find all class, object, and trait definitions
        for pattern, kind in [
            (self.class_pattern, "class"),
            (self.object_pattern, "object"),
            (self.trait_pattern, "trait")
        ]:
            for match in re.finditer(pattern, content, re.MULTILINE):
                class_name = match.group(1)
                start_pos = match.start()
                
                # Find the class body
                class_info = self._extract_block_info(content, start_pos)
                if class_info:
                    classes.append({
                        "name": class_name,
                        "type": kind,
                        "start_line": self._get_line_number(content, start_pos),
                        "end_line": self._get_line_number(content, class_info["end_pos"]),
                        "methods": self._extract_methods(class_info["body"]),
                        "content": class_info["body"]
                    })
        
        return classes

    def _extract_methods(self, class_content: str) -> List[Dict[str, Any]]:
        """Extract method definitions from a class body."""
        methods = []
        
        for match in re.finditer(self.method_pattern, class_content, re.MULTILINE):
            method_name = match.group(1)
            start_pos = match.start()
            
            # Find the method body
            method_info = self._extract_block_info(class_content, start_pos)
            if method_info:
                methods.append({
                    "name": method_name,
                    "start_line": self._get_line_number(class_content, start_pos),
                    "end_line": self._get_line_number(class_content, method_info["end_pos"]),
                    "content": method_info["body"]
                })
        
        return methods

    def _extract_block_info(self, content: str, start_pos: int) -> Optional[Dict[str, Any]]:
        """Extract a code block (class or method body) starting from a given position."""
        pos = start_pos
        while pos < len(content) and content[pos] != '{':
            pos += 1
        
        if pos >= len(content):
            return None
            
        brace_count = 1
        pos += 1
        start_body = pos
        
        while pos < len(content) and brace_count > 0:
            if content[pos] == '{':
                brace_count += 1
            elif content[pos] == '}':
                brace_count -= 1
            pos += 1
            
        if brace_count == 0:
            return {
                "body": content[start_body:pos-1].strip(),
                "end_pos": pos
            }
            
        return None 