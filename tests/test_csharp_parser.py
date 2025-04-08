import logging

import pytest

from app.code_analysis.agents.nodes.code_chunker.parsers import CSharpParser
from app.code_analysis.agents.nodes.code_chunker.utils.parser_utils import ParserManager

# Sample C# code with various constructs
SAMPLE_CODE = """
// This is a line comment
/* This is a block comment */

/// <summary>
/// This is an XML documentation comment for a class
/// </summary>
public class Person
{
    private string name;
    private int age;

    /// <summary>
    /// Constructor for Person class
    /// </summary>
    /// <param name="name">Person's name</param>
    /// <param name="age">Person's age</param>
    public Person(string name, int age)
    {
        this.name = name;
        this.age = age;
    }

    /// <summary>
    /// Gets the person's name
    /// </summary>
    /// <returns>The name</returns>
    public string GetName()
    {
        return name;
    }

    /// <summary>
    /// Sets the person's name
    /// </summary>
    /// <param name="name">The new name</param>
    public void SetName(string name)
    {
        this.name = name;
    }

    // Property example
    public string Name
    {
        get { return name; }
        set { name = value; }
    }

    // Nested class example
    public class Address
    {
        private string street;

        public Address(string street)
        {
            this.street = street;
        }

        public string GetStreet()
        {
            return street;
        }
    }
}

// Static class example
public static class Utility
{
    public static void PrintPerson(Person person)
    {
        Console.WriteLine(person.GetName());
    }
}

// Using directives (imports)
using System;
using System.Collections.Generic;
"""


@pytest.fixture
def logger():
    """Get a logger for testing"""
    return logging.getLogger("test_csharp_parser")


@pytest.fixture
def parser_manager(logger):
    """Get a parser manager for testing"""
    return ParserManager(logger)


@pytest.fixture
def csharp_parser(logger):
    """Get a C# parser"""
    return CSharpParser(logger)


@pytest.fixture
def tree_sitter_parser(parser_manager):
    """Get a tree-sitter parser for C#"""
    if not parser_manager.using_tree_sitter:
        pytest.skip("Tree-sitter is not available")
    return parser_manager.parsers["C#"]


def test_extract_methods(csharp_parser, tree_sitter_parser):
    """Test extraction of methods, constructors, and properties"""
    result = csharp_parser.extract_elements(SAMPLE_CODE, tree_sitter_parser)

    # We expect at least 7 methods/properties:
    # - Person constructor
    # - GetName and SetName
    # - Name property (getter/setter counted as methods)
    # - Address constructor and GetStreet
    # - Utility.PrintPerson
    assert len(result["functions"]) >= 6, f"Found functions: {result['functions']}"

    # Check for method types
    assert any(f.get("type") == "constructor" for f in result["functions"]), (
        "No constructors found"
    )

    # Check for specific methods
    function_names = [f["name"] for f in result["functions"]]
    assert "GetName" in function_names, "GetName method not found"
    assert "Person" in function_names, "Person constructor not found"


def test_extract_classes(csharp_parser, tree_sitter_parser):
    """Test extraction of classes including nested classes"""
    result = csharp_parser.extract_elements(SAMPLE_CODE, tree_sitter_parser)

    # We expect 3 classes: Person, Address, and Utility
    assert len(result["classes"]) >= 2, f"Found classes: {result['classes']}"

    class_names = [c["name"] for c in result["classes"]]
    assert "Person" in class_names, "Person class not found"

    # Check for nested class identification
    nested_classes = [c for c in result["classes"] if c.get("parent_class")]
    assert len(nested_classes) >= 1, "No nested classes found"


def test_extract_imports(csharp_parser, tree_sitter_parser):
    """Test extraction of imports (using directives)"""
    result = csharp_parser.extract_elements(SAMPLE_CODE, tree_sitter_parser)

    # We expect 2 using directives
    assert len(result["imports"]) == 2, f"Found imports: {result['imports']}"


def test_extract_comments(csharp_parser, tree_sitter_parser):
    """Test extraction of comments"""
    result = csharp_parser.extract_elements(SAMPLE_CODE, tree_sitter_parser)

    # We should find at least 6 comments (line, block, and XML doc)
    assert len(result["comments"]) >= 6, f"Found comments: {result['comments']}"

    # Check for XML doc comments
    xml_doc_comments = [
        c for c in result["comments"] if c.get("type") == "xml_doc_comment"
    ]
    assert len(xml_doc_comments) >= 1, "No XML doc comments found"
