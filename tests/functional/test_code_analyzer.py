import os
import tempfile
from unittest.mock import patch

import pytest

from app.code_analysis.agents.nodes.code_chunker import AnalyzerConfig, CodeAnalyzer
from app.code_analysis.agents.nodes.code_chunker.models.code_chunk import (
    CodeChunk,
    RepositoryAnalysis,
)


class TestCodeAnalyzer:
    """Functional tests for the CodeAnalyzer class."""

    @pytest.fixture
    def mock_bedrock_client(self):
        """Mock the AWS Bedrock client for testing."""
        with patch("boto3.client") as mock_client:
            yield mock_client

    @pytest.fixture
    def test_repo_url(self):
        """Test repository URL."""
        return "https://github.com/ee-todd/test-standards-set/"

    @pytest.fixture
    def test_config(self, test_repo_url):
        """Test configuration for the analyzer."""
        return AnalyzerConfig(
            repo_path_or_url=test_repo_url,
            aws_bedrock_model="anthropic.claude-3-5-sonnet-20240620-v1:0",
            aws_region="eu-west-2",
            log_prompts=True,
            log_responses=True,
            log_file_path="test_logs.log",
            api_timeout=30,
            max_files_to_parse=100,
        )

    @pytest.fixture
    def analyzer(self, test_config):
        """Create a test analyzer instance."""
        with patch(
            "app.code_analysis.agents.nodes.code_chunker.analyzer.RepositoryManager"
        ) as mock_repo_manager:
            # Configure the mock repo manager
            instance = mock_repo_manager.return_value
            instance.repo_path = os.path.join(tempfile.gettempdir(), "test_repo")
            instance.repo_path_or_url = test_config.repo_path_or_url
            instance.ensure_local_repository.return_value = None
            instance.should_skip_directory.return_value = False
            instance.should_skip_file.return_value = False

            # Create the analyzer
            analyzer = CodeAnalyzer(test_config)
            yield analyzer

    def test_init(self, analyzer, test_config):
        """Test initialization of the analyzer."""
        assert analyzer.config == test_config
        assert analyzer.prompt_logger is not None
        assert analyzer.repo_manager is not None
        assert analyzer.parser_manager is not None
        assert analyzer.chunk_manager is not None

    @patch(
        "app.code_analysis.agents.nodes.code_chunker.analyzer.generate_file_structure"
    )
    @patch("app.code_analysis.agents.nodes.code_chunker.analyzer.detect_languages")
    @pytest.mark.usefixtures("mock_bedrock_client")
    def test_analyze_repository(
        self,
        mock_detect_languages,
        mock_generate_file_structure,
        analyzer,
    ):
        """Test repository analysis end-to-end."""
        # Configure mocks
        mock_generate_file_structure.return_value = "file structure"
        mock_detect_languages.return_value = ["python", "javascript"]

        # Mock parse_code_structure
        with patch.object(analyzer, "parse_code_structure") as mock_parse:
            mock_parse.return_value = {"file1.py": {"ast": "mock_ast"}}

            # Mock chunk_codebase
            with patch.object(analyzer.chunk_manager, "chunk_codebase") as mock_chunk:
                # Prepare expected chunks
                expected_chunks = [
                    CodeChunk(
                        chunk_id="chunk1",
                        description="Test chunk",
                        files=["file1.py"],
                        content="def test(): pass",
                    )
                ]
                mock_chunk.return_value = expected_chunks

                # Run the analysis
                result = analyzer.analyze_repository()

                # Verify the results
                assert isinstance(result, RepositoryAnalysis)
                assert result.repository_url == analyzer.repo_manager.repo_path_or_url
                assert result.file_structure == "file structure"
                assert result.languages_used == ["python", "javascript"]
                assert result.ingested_repo_chunks == expected_chunks

                # Verify method calls
                analyzer.repo_manager.ensure_local_repository.assert_called_once()
                mock_generate_file_structure.assert_called_once()
                mock_detect_languages.assert_called_once()
                mock_parse.assert_called_once()
                mock_chunk.assert_called_once()

    def test_parse_code_structure(self, analyzer):
        """Test parsing code structure."""
        # Mock os.walk to return a file structure
        test_files = [
            ("root", ["dir1"], ["file1.py", "file2.js", "README.md"]),
            ("root/dir1", [], ["file3.py"]),
        ]

        with (
            patch("os.walk", return_value=test_files),
            patch.object(analyzer, "_process_file") as mock_process,
        ):
            # Configure mock to return different structures for different files
            def side_effect(file_path, ext):
                if ext == ".py":
                    return {file_path: {"type": "python_file"}}, 1
                if ext == ".js":
                    return {file_path: {"type": "js_file"}}, 1
                return {}, 0

            mock_process.side_effect = side_effect

            # Call the method
            result = analyzer.parse_code_structure()

            # Verify results
            assert "root/file1.py" in result
            assert "root/file2.js" in result
            assert "root/dir1/file3.py" in result
            assert "root/README.md" not in result
            assert result["root/file1.py"]["type"] == "python_file"
            assert result["root/file2.js"]["type"] == "js_file"

            # Verify number of calls
            assert mock_process.call_count == 4

    def test_process_file(self, analyzer):
        """Test processing a single file."""
        # Mock parser manager
        analyzer.parser_manager.SUPPORTED_LANGUAGES = [".py", ".js"]

        with patch.object(analyzer.parser_manager, "parse_file") as mock_parse:
            # Test with a supported file type
            mock_parse.return_value = ({"ast": "test_ast"}, None)
            result, count = analyzer._process_file("test.py", ".py")
            assert result == {"test.py": {"ast": "test_ast"}}
            assert count == 1
            mock_parse.assert_called_once()

            # Reset the mock
            mock_parse.reset_mock()

            # Test with an unsupported file type
            result, count = analyzer._process_file("test.txt", ".txt")
            assert result == {}
            assert count == 0
            mock_parse.assert_not_called()

            # Test with a parsing error
            mock_parse.return_value = (None, "Error parsing file")
            result, count = analyzer._process_file("test.py", ".py")
            assert result == {}
            assert count == 0

    def test_context_manager(self, analyzer):
        """Test the analyzer as a context manager."""
        # Mock the cleanup method
        with patch.object(analyzer.repo_manager, "cleanup") as mock_cleanup:
            # Use the analyzer as a context manager
            with analyzer as ctx:
                assert ctx == analyzer

            # Verify cleanup was called
            mock_cleanup.assert_called_once()

    def test_analyze_repository_error(self, analyzer):
        """Test handling errors during repository analysis."""
        # Mock ensure_local_repository to raise an exception
        analyzer.repo_manager.ensure_local_repository.side_effect = Exception(
            "Test error"
        )

        # Temporarily silence the error log message
        with patch.object(analyzer.logger, "error") as mock_error:
            # Verify that the exception is propagated
            with pytest.raises(RuntimeError) as excinfo:
                analyzer.analyze_repository()

            # Verify the logger was called, but we've suppressed the actual output
            mock_error.assert_called_once()

        assert "Failed to analyze repository" in str(excinfo.value)
