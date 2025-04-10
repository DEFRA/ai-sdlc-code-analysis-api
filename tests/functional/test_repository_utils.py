import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.code_analysis.agents.nodes.code_chunker.repository.file_structure import (
    detect_languages,
    generate_file_structure,
)
from app.code_analysis.agents.nodes.code_chunker.utils.exclusion_utils import (
    create_exclusion_manager,
)
from app.code_analysis.agents.nodes.code_chunker.utils.repository_utils import (
    RepositoryManager,
)


class TestRepositoryUtils:
    """Functional tests for repository utilities."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger for testing."""
        return MagicMock()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Clean up
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_repo(self, temp_dir):
        """Create a sample repository structure for testing."""
        # Create a sample directory structure
        os.makedirs(os.path.join(temp_dir, "src", "main", "python"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "src", "main", "java"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "docs"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, ".git"), exist_ok=True)

        # Create some sample files
        with open(
            os.path.join(temp_dir, "src", "main", "python", "example.py"), "w"
        ) as f:
            f.write("def example():\n    return 'Hello, World!'\n")

        with open(
            os.path.join(temp_dir, "src", "main", "java", "Example.java"), "w"
        ) as f:
            f.write(
                'public class Example {\n    public static void main(String[] args) {\n        System.out.println("Hello, World!");\n    }\n}\n'
            )

        with open(os.path.join(temp_dir, "README.md"), "w") as f:
            f.write(
                "# Example Repository\n\nThis is an example repository for testing.\n"
            )

        return temp_dir

    def test_repository_manager_local_path(self, sample_repo, mock_logger):
        """Test repository manager with a local path."""
        # Create a repository manager with a local path
        repo_manager = RepositoryManager(sample_repo, mock_logger)

        # Check that the repo_path is set correctly
        expected_path = os.path.join(repo_manager._temp_dir, "local_repo")
        assert repo_manager.repo_path == expected_path
        assert repo_manager.repo_path_or_url == sample_repo
        # Local paths should be copied to a temporary directory
        assert os.path.isdir(repo_manager.repo_path)

    @patch(
        "app.code_analysis.agents.nodes.code_chunker.repository.clone.subprocess.run"
    )
    def test_repository_manager_remote_url(self, mock_subprocess_run, mock_logger):
        """Test repository manager with a remote URL."""
        # Setup subprocess mock
        mock_subprocess_run.return_value.returncode = 0

        # Create a repository manager with a remote URL
        repo_url = "https://github.com/ee-todd/test-standards-set/"
        repo_manager = RepositoryManager(repo_url, mock_logger)

        # Check that it's correctly identified as remote URL
        assert repo_manager.repo_path_or_url == repo_url
        assert repo_manager._temp_dir is not None
        assert repo_manager.repo_path == repo_manager._temp_dir

    def test_ensure_local_repository_local(self, sample_repo, mock_logger):
        """Test ensuring a local repository is available when given a local path."""
        repo_manager = RepositoryManager(sample_repo, mock_logger)

        # Mock handle_operation to call the original function
        def handle_operation(operation, _error_msg, *args, **kwargs):
            return operation(*args, **kwargs), None

        # Call ensure_local_repository
        repo_manager.ensure_local_repository(handle_operation, 30)

        # The repo_path should be in a temporary directory
        expected_path = os.path.join(repo_manager._temp_dir, "local_repo")
        assert repo_manager.repo_path == expected_path

    @patch(
        "app.code_analysis.agents.nodes.code_chunker.repository.clone.subprocess.run"
    )
    @patch("shutil.which")
    @patch("tempfile.mkdtemp")
    def test_ensure_local_repository_remote(
        self, mock_mkdtemp, mock_which, mock_subprocess_run, mock_logger
    ):
        """Test ensuring a local repository is available when given a remote URL."""
        # Set up mocks
        mock_mkdtemp.return_value = os.path.join(tempfile.gettempdir(), "mock_temp_dir")
        mock_which.return_value = "/usr/bin/git"
        mock_subprocess_run.return_value.returncode = 0

        # Create a repository manager with a remote URL
        repo_url = "https://github.com/ee-todd/test-standards-set/"

        # We need to patch os.path.exists before the object is initialized
        with patch("os.path.exists") as mock_exists:
            # Return False first (repo doesn't exist) then True for all other calls
            mock_exists.side_effect = [False] + [True] * 10
            repo_manager = RepositoryManager(repo_url, mock_logger)

            # Mock handle_operation to call a simulated version of the operation
            def handle_operation(_operation, _error_msg, *_args, **_kwargs):
                # Just return a successful repo path
                return repo_manager.repo_path, None

            # Mock the is_valid_git_url function
            with patch(
                "app.code_analysis.agents.nodes.code_chunker.repository.clone.is_valid_git_url",
                return_value=True,
            ):
                # Call ensure_local_repository with our simplified handle_operation
                repo_manager.ensure_local_repository(handle_operation, 30)

        # Verify the repo_path
        assert repo_manager.repo_path == os.path.join(
            tempfile.gettempdir(), "mock_temp_dir"
        )

    def test_should_skip_directory(self, sample_repo, mock_logger):
        """Test directory skipping logic."""
        repo_manager = RepositoryManager(sample_repo, mock_logger)

        # Check that .git directories are skipped
        assert repo_manager.should_skip_directory(os.path.join(sample_repo, ".git"))

        # Check that normal directories are not skipped
        assert not repo_manager.should_skip_directory(os.path.join(sample_repo, "src"))

    def test_should_skip_file(self, mock_logger, temp_dir):
        """Test file skipping logic."""
        # Create a temporary directory instead of using /tmp
        repo_manager = RepositoryManager(temp_dir, mock_logger)

        # Check that hidden files are skipped
        assert repo_manager.should_skip_file(".gitignore")
        assert repo_manager.should_skip_file(".env")

        # Check that normal files are not skipped
        assert not repo_manager.should_skip_file("example.py")
        assert not repo_manager.should_skip_file("README.md")

    def test_cleanup(self, mock_logger, temp_dir):
        """Test cleanup with a temporary repository."""
        # Create a repository manager with the temporary directory
        repo_manager = RepositoryManager(temp_dir, mock_logger)
        repo_path = repo_manager.repo_path

        # Create a file in the repository path
        test_file = os.path.join(repo_path, "test.txt")
        with open(test_file, "w") as f:
            f.write("test")

        # Verify the file exists
        assert os.path.exists(test_file)

        # Replace rmtree with a mock to avoid actual deletion
        with patch("shutil.rmtree") as mock_rmtree:
            # Call cleanup
            repo_manager.cleanup()

            # Verify that rmtree was called with the correct directory
            mock_rmtree.assert_called_once_with(repo_manager._temp_dir)

    def test_generate_file_structure(self, sample_repo, mock_logger):
        """Test generating file structure representation."""
        # Generate file structure
        structure = generate_file_structure(sample_repo, mock_logger)

        # Check that it contains the expected directories and files
        assert "src" in structure
        assert "main" in structure
        assert "python" in structure
        assert "java" in structure
        assert "example.py" in structure
        assert "Example.java" in structure
        assert "README.md" in structure

    def test_detect_languages(self, sample_repo, mock_logger):
        """Test language detection."""
        # Define supported languages
        supported_languages = [".py", ".java", ".js"]

        # Detect languages
        languages = detect_languages(sample_repo, supported_languages, mock_logger)

        # Check that Python and Java are detected
        assert ".py" in languages
        assert ".java" in languages
        assert ".js" not in languages  # No JavaScript files in the sample repo

    def test_clean_directory(self, sample_repo, mock_logger):
        """Test cleaning excluded files from a directory."""
        # Create a test repository with files that should be excluded
        os.makedirs(os.path.join(sample_repo, "node_modules"), exist_ok=True)
        os.makedirs(os.path.join(sample_repo, "venv"), exist_ok=True)

        # Create some excluded files
        with open(os.path.join(sample_repo, "package-lock.json"), "w") as f:
            f.write("package lock file")

        with open(os.path.join(sample_repo, "node_modules", "test.js"), "w") as f:
            f.write("test module file")

        with open(os.path.join(sample_repo, "example.pyc"), "w") as f:
            f.write("compiled python file")

        # Create a repository manager
        repo_manager = RepositoryManager(sample_repo, mock_logger)

        # Now manually clean the directory
        if not repo_manager.exclusion_manager:
            repo_manager.exclusion_manager = create_exclusion_manager(
                sample_repo, repo_manager._base_exclude_patterns, mock_logger
            )

        # Test cleaning the directory
        removed_count = repo_manager.exclusion_manager.clean_directory(sample_repo)

        # Check that excluded files are removed
        assert removed_count > 0
        assert not os.path.exists(os.path.join(sample_repo, "package-lock.json"))
        assert not os.path.exists(os.path.join(sample_repo, "example.pyc"))

        # Check that node_modules directory was excluded (its pattern ends with /)
        assert not os.path.exists(os.path.join(sample_repo, "node_modules", "test.js"))

    def test_exclusion_manager_initialization(self, sample_repo, mock_logger):
        """Test ExclusionManager initialization from the RepositoryManager."""
        # Create a mock .gitignore file
        with open(os.path.join(sample_repo, ".gitignore"), "w") as f:
            f.write("*.log\ntmp/\n")

        # Create a repository manager
        repo_manager = RepositoryManager(sample_repo, mock_logger)

        # Check that the exclusion_manager is created and has the correct patterns
        assert repo_manager.exclusion_manager is not None

        # Check if .gitignore patterns were loaded
        exclusion_patterns = repo_manager.get_excluded_files()
        assert "*.log" in exclusion_patterns
        assert "tmp/" in exclusion_patterns
