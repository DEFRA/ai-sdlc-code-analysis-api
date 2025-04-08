import logging

import pytest

from app.code_analysis.agents.nodes.code_chunker.parsers import JavaScriptParser
from app.code_analysis.agents.nodes.code_chunker.utils.parser_utils import ParserManager

# Sample JavaScript code with various constructs
SAMPLE_CODE = """
// This is a comment
/* This is a block comment */

/**
 * This is a JSDoc comment
 * @param {string} name
 * @returns {string}
 */
function greet(name) {
    return `Hello, ${name}!`;
}

// Arrow function
const sayHello = (name) => {
    return `Hello, ${name}!`;
};

// Class with methods
class Person {
    /**
     * Constructor for Person
     * @param {string} name - The person's name
     */
    constructor(name) {
        this.name = name;
    }

    // Method in a class
    sayHello() {
        return `Hello, my name is ${this.name}`;
    }

    // Static method
    static create(name) {
        return new Person(name);
    }
}

// Nested class example (less common in JS but possible)
class School {
    constructor(name) {
        this.name = name;
        this.students = [];
    }

    // Inner class via class expression
    createStudentClass() {
        this.StudentClass = class Student {
            constructor(name) {
                this.name = name;
            }

            getSchoolName() {
                return School.name;
            }
        };
    }
}

// Import statements
import { useState } from 'react';
import React from 'react';
"""


@pytest.fixture
def logger():
    """Get a logger for testing"""
    return logging.getLogger("test_javascript_parser")


@pytest.fixture
def parser_manager(logger):
    """Get a parser manager for testing"""
    return ParserManager(logger)


@pytest.fixture
def javascript_parser(logger):
    """Get a JavaScript parser"""
    return JavaScriptParser(logger)


@pytest.fixture
def tree_sitter_parser(parser_manager):
    """Get a tree-sitter parser for JavaScript"""
    if not parser_manager.using_tree_sitter:
        pytest.skip("Tree-sitter is not available")
    return parser_manager.parsers["JavaScript"]


def test_extract_functions(javascript_parser, tree_sitter_parser):
    """Test extraction of functions"""
    result = javascript_parser.extract_elements(SAMPLE_CODE, tree_sitter_parser)

    # We expect 6 functions:
    # - greet (standalone function)
    # - sayHello (arrow function - should be captured)
    # - constructor, sayHello, static create (methods in Person)
    # - constructor in School
    assert len(result["functions"]) >= 4, f"Found functions: {result['functions']}"

    # Verify specific functions are found
    function_names = [f["name"] for f in result["functions"]]
    assert "greet" in function_names, "Standalone function not found"

    # Check for function types
    assert any(f.get("type") == "method" for f in result["functions"]), (
        "No methods found"
    )


def test_extract_classes(javascript_parser, tree_sitter_parser):
    """Test extraction of classes"""
    result = javascript_parser.extract_elements(SAMPLE_CODE, tree_sitter_parser)

    # We expect 2 classes: Person and School
    assert len(result["classes"]) >= 2, f"Found classes: {result['classes']}"

    class_names = [c["name"] for c in result["classes"]]
    assert "Person" in class_names, "Person class not found"
    assert "School" in class_names, "School class not found"


def test_extract_imports(javascript_parser, tree_sitter_parser):
    """Test extraction of imports"""
    result = javascript_parser.extract_elements(SAMPLE_CODE, tree_sitter_parser)

    # We expect 2 import statements
    assert len(result["imports"]) == 2, f"Found imports: {result['imports']}"


def test_extract_comments(javascript_parser, tree_sitter_parser):
    """Test extraction of comments"""
    result = javascript_parser.extract_elements(SAMPLE_CODE, tree_sitter_parser)

    # We should find at least 5 comments (line, block, and JSDoc)
    assert len(result["comments"]) >= 5, f"Found comments: {result['comments']}"

    # Check for JSDoc comments
    jsdoc_comments = [c for c in result["comments"] if c["text"].startswith("/**")]
    assert len(jsdoc_comments) >= 1, "No JSDoc comments found"
