import logging

import pytest

from app.code_analysis.agents.nodes.code_chunker.parsers import JavaParser
from app.code_analysis.agents.nodes.code_chunker.utils.parser_utils import ParserManager

# Sample Java code with various constructs
SAMPLE_CODE = """
// This is a line comment
/* This is a block comment */

/**
 * This is a JavaDoc comment for a class
 * @author TestDeveloper
 */
public class Person {
    private String name;
    private int age;

    /**
     * Constructor for Person class
     * @param name Person's name
     * @param age Person's age
     */
    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }

    /**
     * Returns person's name
     * @return the name
     */
    public String getName() {
        return name;
    }

    /**
     * Sets person's name
     * @param name the name to set
     */
    public void setName(String name) {
        this.name = name;
    }

    // Inner class example
    public class Address {
        private String street;

        public Address(String street) {
            this.street = street;
        }

        public String getStreet() {
            return street;
        }
    }

    // Static nested class
    public static class Builder {
        private String name;
        private int age;

        public Builder withName(String name) {
            this.name = name;
            return this;
        }

        public Builder withAge(int age) {
            this.age = age;
            return this;
        }

        public Person build() {
            return new Person(name, age);
        }
    }
}

// Standalone function-like class
class Utility {
    public static void printPerson(Person person) {
        System.out.println(person.getName());
    }
}

// Java imports
import java.util.List;
import java.util.ArrayList;
"""


@pytest.fixture
def logger():
    """Get a logger for testing"""
    return logging.getLogger("test_java_parser")


@pytest.fixture
def parser_manager(logger):
    """Get a parser manager for testing"""
    return ParserManager(logger)


@pytest.fixture
def java_parser(logger):
    """Get a Java parser"""
    return JavaParser(logger)


@pytest.fixture
def tree_sitter_parser(parser_manager):
    """Get a tree-sitter parser for Java"""
    if not parser_manager.using_tree_sitter:
        pytest.skip("Tree-sitter is not available")
    return parser_manager.parsers["Java"]


def test_extract_methods(java_parser, tree_sitter_parser):
    """Test extraction of methods and constructors"""
    result = java_parser.extract_elements(SAMPLE_CODE, tree_sitter_parser)

    # We expect 8 methods:
    # - Person constructor
    # - getName and setName
    # - Address constructor and getStreet
    # - Builder: withName, withAge, build
    # - Utility.printPerson
    assert len(result["functions"]) >= 8, f"Found functions: {result['functions']}"

    # Check for method types
    assert any(f.get("type") == "constructor" for f in result["functions"]), (
        "No constructors found"
    )
    assert any(f.get("type") == "method" for f in result["functions"]), (
        "No methods found"
    )

    # Check for specific methods
    function_names = [f["name"] for f in result["functions"]]
    assert "getName" in function_names, "getName method not found"
    assert "Person" in function_names, "Person constructor not found"


def test_extract_classes(java_parser, tree_sitter_parser):
    """Test extraction of classes including nested classes"""
    result = java_parser.extract_elements(SAMPLE_CODE, tree_sitter_parser)

    # We expect 4 classes: Person, Address, Builder, and Utility
    assert len(result["classes"]) >= 3, f"Found classes: {result['classes']}"

    class_names = [c["name"] for c in result["classes"]]
    assert "Person" in class_names, "Person class not found"

    # Check for nested class identification
    nested_classes = [c for c in result["classes"] if c.get("parent_class")]
    assert len(nested_classes) >= 1, "No nested classes found"


def test_extract_imports(java_parser, tree_sitter_parser):
    """Test extraction of imports"""
    result = java_parser.extract_elements(SAMPLE_CODE, tree_sitter_parser)

    # We expect 2 import statements
    assert len(result["imports"]) == 2, f"Found imports: {result['imports']}"


def test_extract_comments(java_parser, tree_sitter_parser):
    """Test extraction of comments"""
    result = java_parser.extract_elements(SAMPLE_CODE, tree_sitter_parser)

    # We should find at least 6 comments (line, block, and JavaDoc)
    assert len(result["comments"]) >= 6, f"Found comments: {result['comments']}"

    # Check for JavaDoc comments
    javadoc_comments = [
        c for c in result["comments"] if c.get("type") == "javadoc_comment"
    ]
    assert len(javadoc_comments) >= 1, "No JavaDoc comments found"
