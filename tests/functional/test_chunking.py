import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.code_analysis.agents.nodes.code_chunker.chunking.chunk_manager import (
    ChunkManager,
)
from app.code_analysis.agents.nodes.code_chunker.chunking.chunk_processor import (
    expand_glob_patterns,
    process_chunk,
)
from app.code_analysis.agents.nodes.code_chunker.chunking.claude_integration import (
    get_chunks_from_bedrock,
)
from app.code_analysis.agents.nodes.code_chunker.models.code_chunk import CodeChunk
from app.code_analysis.agents.nodes.code_chunker.utils.logging_utils import PromptLogger


class TestChunkManager:
    """Functional tests for the chunk manager."""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock the Anthropic client for testing."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[
                MagicMock(
                    text='[{"chunk_id": "chunk1", "description": "Feature 1", "files": ["file1.py"], "content": "code1"},'
                    '{"chunk_id": "chunk2", "description": "Feature 2", "files": ["file2.py"], "content": "code2"}]'
                )
            ]
        )
        return mock_client

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing."""
        return MagicMock()

    @pytest.fixture
    def mock_prompt_logger(self):
        """Create a mock prompt logger for testing."""
        return MagicMock(spec=PromptLogger)

    @pytest.fixture
    def chunk_manager(self, mock_anthropic_client, mock_logger, mock_prompt_logger):
        """Create a test chunk manager instance."""
        return ChunkManager(
            bedrock_config=mock_anthropic_client,
            api_timeout=30,
            logger=mock_logger,
            prompt_logger=mock_prompt_logger,
            filter_comments_above_tokens=200000,
        )

    @pytest.mark.usefixtures("mock_anthropic_client", "mock_logger")
    def test_chunk_codebase(self, chunk_manager):
        """Test chunking a codebase."""
        # Create mock code structure and repo path
        code_structure = {
            "file1.py": {"ast": "mock_ast1"},
            "file2.py": {"ast": "mock_ast2"},
        }

        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as repo_path:
            # Create the test files
            os.makedirs(
                os.path.dirname(os.path.join(repo_path, "file1.py")), exist_ok=True
            )
            os.makedirs(
                os.path.dirname(os.path.join(repo_path, "file2.py")), exist_ok=True
            )

            with open(os.path.join(repo_path, "file1.py"), "w") as f:
                f.write("def test1(): pass")

            with open(os.path.join(repo_path, "file2.py"), "w") as f:
                f.write("def test2(): pass")

            # Create mock handle_operation and operation_with_retry functions
            def mock_handle_operation(operation, _error_msg, *args, **kwargs):
                return operation(*args, **kwargs), None

            def mock_operation_with_retry(
                operation, _error_msg, _logger, _max_retries=3, *args, **kwargs
            ):
                # Remove max_retries from kwargs if present
                if "max_retries" in kwargs:
                    kwargs.pop("max_retries")
                return operation(*args, **kwargs)

            # Mock the necessary functions
            with patch(
                "app.code_analysis.agents.nodes.code_chunker.chunking.chunk_processor.create_simplified_structure"
            ) as mock_create_structure:
                mock_create_structure.return_value = (
                    {"file1.py": "def test1(): pass", "file2.py": "def test2(): pass"},
                    2,  # file count
                )

                with patch(
                    "app.code_analysis.agents.nodes.code_chunker.repository.file_structure.generate_file_structure"
                ) as mock_gen_structure:
                    mock_gen_structure.return_value = "directory structure"

                    with patch(
                        "app.code_analysis.agents.nodes.code_chunker.chunking.chunk_manager.create_chunking_prompt"
                    ) as mock_create_prompt:
                        mock_create_prompt.return_value = "test prompt"

                        with patch(
                            "app.code_analysis.agents.nodes.code_chunker.chunking.chunk_manager.get_chunks_from_bedrock"
                        ) as mock_get_chunks:
                            # Define expected chunks data from Claude
                            expected_chunks_data = [
                                {
                                    "chunk_id": "chunk1",
                                    "description": "Feature 1",
                                    "files": ["file1.py"],
                                    "content": "code1",
                                },
                                {
                                    "chunk_id": "chunk2",
                                    "description": "Feature 2",
                                    "files": ["file2.py"],
                                    "content": "code2",
                                },
                            ]
                            mock_get_chunks.return_value = expected_chunks_data

                            with patch(
                                "app.code_analysis.agents.nodes.code_chunker.chunking.chunk_processor.read_file_content"
                            ) as mock_read_file:
                                # Mock read_file_content to return "code1" and "code2" for the respective files
                                def read_file_side_effect(file_path, *_args, **_kwargs):
                                    if file_path == "file1.py":
                                        return "code1"
                                    if file_path == "file2.py":
                                        return "code2"
                                    return ""

                                mock_read_file.side_effect = read_file_side_effect

                                with patch(
                                    "app.code_analysis.agents.nodes.code_chunker.chunking.chunk_processor.process_chunk"
                                ) as mock_process_chunk:
                                    # Mock processing each chunk
                                    def process_side_effect(
                                        chunk_data,
                                        _index,
                                        _repo_path,
                                        _logger,
                                        _handle_op,
                                    ):
                                        return CodeChunk(
                                            chunk_id=chunk_data["chunk_id"],
                                            description=chunk_data["description"],
                                            files=chunk_data["files"],
                                            content=chunk_data["content"],
                                        )

                                    mock_process_chunk.side_effect = process_side_effect

                                    # Execute the chunking
                                    result = chunk_manager.chunk_codebase(
                                        code_structure,
                                        repo_path,
                                        "directory structure",
                                        mock_handle_operation,
                                        mock_operation_with_retry,
                                    )

                                    # Verify results
                                    assert len(result) == 2
                                    assert isinstance(result[0], CodeChunk)
                                    assert result[0].chunk_id == "chunk1"
                                    assert result[0].description == "Feature 1"
                                    assert result[0].files == ["file1.py"]
                                    assert result[0].content == "code1"

                                    assert isinstance(result[1], CodeChunk)
                                    assert result[1].chunk_id == "chunk2"
                                    assert result[1].description == "Feature 2"
                                    assert result[1].files == ["file2.py"]
                                    assert result[1].content == "code2"

                                    # No need to verify method calls since we're mocking them directly

    @pytest.mark.usefixtures("mock_logger")
    def test_chunk_codebase_error(self, chunk_manager):
        """Test handling errors during chunking."""
        # Create mock code structure and repo path
        code_structure = {"file1.py": {"ast": "mock_ast1"}}
        repo_path = os.path.join(tempfile.gettempdir(), "test_repo")

        # Create mock operation functions
        mock_handle_operation = MagicMock()
        mock_operation_with_retry = MagicMock()

        # Create mock directory structure
        directory_structure = "mock directory structure"

        # Make create_simplified_structure raise an exception
        with patch(
            "app.code_analysis.agents.nodes.code_chunker.chunking.chunk_processor.create_simplified_structure"
        ) as mock_create_structure:
            mock_create_structure.side_effect = Exception("Test error")

            # Verify that the exception is propagated
            with pytest.raises(RuntimeError) as excinfo:
                chunk_manager.chunk_codebase(
                    code_structure,
                    repo_path,
                    directory_structure,
                    mock_handle_operation,
                    mock_operation_with_retry,
                )

            assert "Failed to chunk codebase" in str(excinfo.value)

            # Verify logging
            chunk_manager.logger.error.assert_called()

    @patch(
        "app.code_analysis.agents.nodes.code_chunker.chunking.claude_integration.json.loads"
    )
    @patch(
        "app.code_analysis.agents.nodes.code_chunker.chunking.claude_integration.ChatBedrock"
    )
    def test_get_chunks_from_claude(
        self,
        mock_chatbedrock_class,
        mock_json_loads,
        chunk_manager,
        mock_anthropic_client,
    ):
        """Test getting chunks from Claude."""
        # Configure the mock
        mock_json_loads.return_value = [
            {
                "chunk_id": "chunk1",
                "description": "Test Chunk",
                "files": ["file1.py"],
                "content": "code",
            }
        ]

        # Set up ChatBedrock mock
        mock_chatbedrock_instance = MagicMock()
        mock_chatbedrock_instance.invoke.return_value = MagicMock(
            content="test response content"
        )
        mock_chatbedrock_class.return_value = mock_chatbedrock_instance

        # Mock operation_with_retry to call the actual function
        def mock_operation_with_retry(
            operation, _error_msg, _logger, _max_retries=3, *args, **kwargs
        ):
            # Remove max_retries from kwargs if present
            if "max_retries" in kwargs:
                kwargs.pop("max_retries")
            return operation(*args, **kwargs)

        # Call the function
        result = get_chunks_from_bedrock(
            "test prompt",
            mock_anthropic_client,
            chunk_manager.logger,
            mock_operation_with_retry,
        )

        # Verify results
        assert len(result) == 1
        assert result[0]["chunk_id"] == "chunk1"
        assert result[0]["description"] == "Test Chunk"

        # Verify ChatBedrock was initialized correctly
        mock_chatbedrock_class.assert_called_once()
        # Verify invoke was called on the ChatBedrock instance
        mock_chatbedrock_instance.invoke.assert_called_once()


def test_expand_glob_patterns():
    """Test expanding glob patterns in file paths."""
    # Create a temporary directory structure for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create subdirectories
        os.makedirs(os.path.join(temp_dir, "dir1"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "dir2", "subdir"), exist_ok=True)

        # Create files
        test_files = [
            os.path.join(temp_dir, "file1.py"),
            os.path.join(temp_dir, "file2.txt"),
            os.path.join(temp_dir, "dir1", "test1.py"),
            os.path.join(temp_dir, "dir1", "test2.py"),
            os.path.join(temp_dir, "dir2", "test3.txt"),
            os.path.join(temp_dir, "dir2", "subdir", "test4.py"),
        ]

        # Create the files
        for file_path in test_files:
            with open(file_path, "w") as f:
                f.write(f"Content of {os.path.basename(file_path)}")

        # Create a mock logger
        mock_logger = MagicMock()

        # Test cases
        test_cases = [
            # Simple filename pattern
            (
                ["*.py"],
                [
                    os.path.basename(f)
                    for f in test_files
                    if f.endswith(".py") and os.path.dirname(f) == temp_dir
                ],
            ),
            # Directory pattern
            (
                ["dir1/*.py"],
                [
                    os.path.join("dir1", f)
                    for f in os.listdir(os.path.join(temp_dir, "dir1"))
                    if f.endswith(".py")
                ],
            ),
            # Recursive pattern
            (
                ["**/*.py"],
                [os.path.relpath(f, temp_dir) for f in test_files if f.endswith(".py")],
            ),
            # Multiple patterns
            (
                ["*.py", "dir2/**/*.txt"],
                [
                    os.path.basename(f)
                    for f in test_files
                    if f.endswith(".py") and os.path.dirname(f) == temp_dir
                ]
                + [
                    os.path.relpath(f, temp_dir)
                    for f in test_files
                    if f.endswith(".txt") and "dir2" in f
                ],
            ),
            # Non-matching pattern
            (["nonexistent/*.md"], []),
        ]

        # Run tests
        for patterns, expected in test_cases:
            result = expand_glob_patterns(patterns, temp_dir, mock_logger)
            # Sort both lists to ensure consistent comparison
            assert sorted(result) == sorted(expected), f"Failed for patterns {patterns}"


def test_process_chunk_with_wildcards():
    """Test processing a chunk with wildcard patterns in file paths."""
    # Create a temporary directory structure for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create subdirectories
        os.makedirs(os.path.join(temp_dir, "dir1"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "dir2", "subdir"), exist_ok=True)

        # Create files
        test_files = [
            os.path.join(temp_dir, "file1.py"),
            os.path.join(temp_dir, "file2.txt"),
            os.path.join(temp_dir, "dir1", "test1.py"),
            os.path.join(temp_dir, "dir1", "test2.py"),
            os.path.join(temp_dir, "dir2", "test3.txt"),
            os.path.join(temp_dir, "dir2", "subdir", "test4.py"),
        ]

        # Create the files with unique content
        for file_path in test_files:
            with open(file_path, "w") as f:
                f.write(f"Content of {os.path.basename(file_path)}")

        # Create a mock logger
        mock_logger = MagicMock()

        # Create chunk data with wildcard patterns
        chunk_data = {
            "chunk_id": "test_chunk",
            "description": "Test chunk with wildcards",
            "files": ["**/*.py"],  # Should match all Python files recursively
        }

        # Mock handle_operation to read real files
        def mock_handle_operation(operation, _error_msg, *args, **kwargs):
            return operation(*args, **kwargs), None

        # Process the chunk
        chunk = process_chunk(
            chunk_data=chunk_data,
            chunk_index=0,
            repo_path=temp_dir,
            logger=mock_logger,
            handle_operation=mock_handle_operation,
        )

        # Expected files (all .py files)
        expected_files = [
            os.path.relpath(f, temp_dir) for f in test_files if f.endswith(".py")
        ]

        # Verify the chunk
        assert chunk.chunk_id == "test_chunk"
        assert chunk.description == "Test chunk with wildcards"
        # Sort to ensure consistent comparison
        assert sorted(chunk.files) == sorted(expected_files)
        # Verify content contains all Python files
        for file_path in expected_files:
            file_header = f"\n\n--- {file_path} ---\n"
            assert file_header in chunk.content, f"Content missing for {file_path}"

        # Test with multiple patterns
        chunk_data["files"] = ["*.py", "dir2/**/*.txt"]
        chunk = process_chunk(
            chunk_data=chunk_data,
            chunk_index=0,
            repo_path=temp_dir,
            logger=mock_logger,
            handle_operation=mock_handle_operation,
        )

        # Expected files (root .py files + dir2 .txt files)
        expected_files = [
            os.path.relpath(f, temp_dir)
            for f in test_files
            if (f.endswith(".py") and os.path.dirname(f) == temp_dir)
            or (f.endswith(".txt") and "dir2" in f)
        ]

        # Verify the chunk with multiple patterns
        assert sorted(chunk.files) == sorted(expected_files)
        for file_path in expected_files:
            file_header = f"\n\n--- {file_path} ---\n"
            assert file_header in chunk.content, f"Content missing for {file_path}"
