import os
import tempfile
from unittest.mock import MagicMock

import pytest

from app.code_analysis.agents.nodes.code_chunker import CodeAnalyzer


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    mock_client = MagicMock()
    # Mock the messages.create method with a valid chunk response
    mock_response = MagicMock()
    mock_response.content = {
        "chunks": [
            {
                "chunk_id": "test_chunk",
                "description": "Test chunk",
                "files": ["sample.py", "module/__init__.py"],
            }
        ]
    }
    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_code():
    """Sample Python code for testing."""
    return """
def hello():
    print("Hello, World!")

class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b

def main():
    calc = Calculator()
    result = calc.add(1, 2)
    print(f"Result: {result}")
    """


@pytest.fixture
def temp_repo(sample_code):
    """Create a temporary repository with sample code for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a sample Python file
        with open(os.path.join(temp_dir, "sample.py"), "w") as f:
            f.write(sample_code)
        # Create a simple module structure
        os.makedirs(os.path.join(temp_dir, "module"))
        with open(os.path.join(temp_dir, "module", "__init__.py"), "w") as f:
            f.write("")
        yield temp_dir


@pytest.fixture
def code_analyzer(temp_repo, mock_anthropic_client):
    """Create a CodeAnalyzer instance for testing."""
    analyzer = CodeAnalyzer(temp_repo, api_timeout=2)
    analyzer.anthropic_client = mock_anthropic_client
    return analyzer


@pytest.fixture
def page_with_timeout(page):
    """Configure page with default timeout."""
    page.set_default_timeout(5000)
    return page
