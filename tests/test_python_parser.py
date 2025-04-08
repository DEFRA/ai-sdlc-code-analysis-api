"""Tests for Python parser method extraction"""

import logging

import pytest

from app.code_analysis.agents.nodes.code_chunker.parsers import PythonParser
from app.code_analysis.agents.nodes.code_chunker.utils.parser_utils import ParserManager

# Sample Python code with functions and methods
SAMPLE_CODE = """
# This is a file level comment
# Multiple lines comment

def standalone_function():
    # Comment inside function
    return "This is a standalone function"

class MyClass:
    '''Class level docstring for MyClass'''
    def __init__(self, name):
        # Constructor comment
        self.name = name

    def method1(self):
        # Method comment
        return f"Method 1 from {self.name}"

    def method2(self, param):
        '''Docstring for method2'''
        return f"Method 2 with param {param}"

class AnotherClass:
    # AnotherClass comment
    def another_method(self):
        return "Another method"

    class NestedClass:
        # NestedClass comment
        def nested_method(self):
            return "Nested method"

def another_function():
    # Another function comment
    return "Another standalone function"
"""


@pytest.fixture
def logger():
    """Create a logger for testing"""
    return logging.getLogger("test_python_parser")


@pytest.fixture
def parser_manager(logger):
    """Create a parser manager for testing"""
    return ParserManager(logger)


@pytest.fixture
def python_parser(logger):
    """Create a Python parser for testing"""
    return PythonParser(logger)


@pytest.fixture
def tree_sitter_parser(parser_manager):
    """Get a tree-sitter parser for Python"""
    if not parser_manager.using_tree_sitter:
        pytest.skip("Tree-sitter is not available")
    return parser_manager.parsers["Python"]


def test_extract_standalone_functions(python_parser, tree_sitter_parser):
    """Test extraction of standalone functions"""
    result = python_parser.extract_elements(SAMPLE_CODE, tree_sitter_parser)

    # Find standalone functions
    standalone_funcs = [f for f in result["functions"] if f.get("type") == "function"]

    assert len(standalone_funcs) == 2
    func_names = {f["name"] for f in standalone_funcs}
    assert func_names == {"standalone_function", "another_function"}


def test_extract_methods(python_parser, tree_sitter_parser):
    """Test extraction of class methods"""
    result = python_parser.extract_elements(SAMPLE_CODE, tree_sitter_parser)

    # Find methods
    methods = [f for f in result["functions"] if f.get("type") == "method"]

    # We now expect 5 methods total: 3 in MyClass, 1 in AnotherClass, 1 in NestedClass
    assert len(methods) == 5

    # Check MyClass methods
    myclass_methods = [m for m in methods if m.get("class") == "MyClass"]
    assert len(myclass_methods) == 3
    myclass_method_names = {m["name"] for m in myclass_methods}
    assert myclass_method_names == {"__init__", "method1", "method2"}

    # Check AnotherClass methods
    another_class_methods = [m for m in methods if m.get("class") == "AnotherClass"]
    assert len(another_class_methods) >= 1
    assert any(m["name"] == "another_method" for m in another_class_methods)


def test_extract_nested_class_methods(python_parser, tree_sitter_parser):
    """Test extraction of nested class methods"""
    result = python_parser.extract_elements(SAMPLE_CODE, tree_sitter_parser)

    # Find methods in either NestedClass directly or as part of AnotherClass
    nested_methods = [
        f
        for f in result["functions"]
        if f.get("type") == "method"
        and (
            f.get("class") == "NestedClass"
            or (f.get("name") == "nested_method" and f.get("class") == "AnotherClass")
        )
    ]

    # We should have at least one nested method
    assert len(nested_methods) >= 1
    assert any(m["name"] == "nested_method" for m in nested_methods)


def test_extract_classes(python_parser, tree_sitter_parser):
    """Test extraction of class definitions"""
    result = python_parser.extract_elements(SAMPLE_CODE, tree_sitter_parser)

    # We should have both MyClass and AnotherClass, and possibly NestedClass
    assert len(result["classes"]) >= 2

    class_names = {c["name"] for c in result["classes"]}
    assert "MyClass" in class_names
    assert "AnotherClass" in class_names

    # Find any nested classes
    nested_classes = [c for c in result["classes"] if c.get("parent_class") is not None]
    if nested_classes:
        assert any(c["name"] == "NestedClass" for c in nested_classes)


def test_extract_comments(python_parser, tree_sitter_parser):
    """Test extraction of comments and docstrings"""
    result = python_parser.extract_elements(SAMPLE_CODE, tree_sitter_parser)

    # Check that comments are extracted
    assert "comments" in result
    assert len(result["comments"]) >= 8  # At least 8 comments in the sample code

    # Check for specific comments
    comment_texts = [c["text"] for c in result["comments"]]

    # Convert to lowercase and strip for easier matching
    normalized_comments = [c.lower().strip() for c in comment_texts]

    # Check for presence of specific comments
    assert any("file level comment" in c for c in normalized_comments)
    assert any("comment inside function" in c for c in normalized_comments)

    # Check that we correctly identify docstrings vs regular comments
    regular_comments = [c for c in result["comments"] if c.get("type") == "comment"]
    docstrings = [c for c in result["comments"] if c.get("type") == "docstring"]

    # We should have both regular comments and docstrings
    assert len(regular_comments) > 0, "No regular comments found"
    assert len(docstrings) > 0, "No docstrings found"

    # Check for specific docstrings
    docstring_texts = [d["text"].lower().strip() for d in docstrings]
    assert any(
        "class level docstring" in d or "docstring for myclass" in d
        for d in docstring_texts
    )
    assert any("docstring for method2" in d for d in docstring_texts)

    # Verify comment types are properly captured
    for comment in result["comments"]:
        assert "type" in comment
        assert comment["type"] in ["comment", "docstring"]
