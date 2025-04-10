"""Tests for the exclusion utilities module."""

import os
import shutil
import tempfile
from unittest.mock import MagicMock

import pytest

from app.code_analysis.agents.nodes.code_chunker.config.exclusion_config import (
    DEFAULT_EXCLUDE_PATTERNS,
)
from app.code_analysis.agents.nodes.code_chunker.utils.exclusion_utils import (
    ExclusionManager,
    create_exclusion_manager,
    get_combined_exclude_patterns,
)


class TestExclusionUtils:
    """Tests for the exclusion utilities."""

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
        # Create directories
        os.makedirs(os.path.join(temp_dir, "src"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "node_modules"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, ".git"), exist_ok=True)

        # Create files
        with open(os.path.join(temp_dir, "src", "main.py"), "w") as f:
            f.write("print('Hello, World!')")

        with open(os.path.join(temp_dir, "package-lock.json"), "w") as f:
            f.write("{}")

        with open(os.path.join(temp_dir, "README.md"), "w") as f:
            f.write("# Test Repository")

        # Create .gitignore
        with open(os.path.join(temp_dir, ".gitignore"), "w") as f:
            f.write("*.log\ntmp/\n*.cache\n")

        return temp_dir

    def test_get_combined_exclude_patterns(self, sample_repo, mock_logger):
        """Test combining exclude patterns with gitignore patterns."""
        gitignore_path = os.path.join(sample_repo, ".gitignore")
        base_patterns = ["*.pyc", "*.egg-info/"]

        # Get combined patterns
        combined = get_combined_exclude_patterns(
            base_patterns, gitignore_path, mock_logger
        )

        # Check that the base patterns are included
        for pattern in base_patterns:
            assert pattern in combined

        # Check that .gitignore patterns are included
        assert "*.log" in combined
        assert "tmp/" in combined
        assert "*.cache" in combined

    def test_create_exclusion_manager(self, sample_repo, mock_logger):
        """Test creating an exclusion manager."""
        # Create exclusion manager
        manager = create_exclusion_manager(
            sample_repo, DEFAULT_EXCLUDE_PATTERNS, mock_logger
        )

        # Check that it's properly initialized
        assert isinstance(manager, ExclusionManager)
        assert manager.repo_path == sample_repo
        assert manager.logger == mock_logger
        assert manager.gitignore_spec is not None

        # Check that the patterns include both default and gitignore patterns
        patterns = manager.exclude_patterns
        assert "*.pyc" in patterns  # From DEFAULT_EXCLUDE_WILDCARDS
        assert "node_modules/" in patterns  # From DEFAULT_EXCLUDE_DIRS
        assert "package-lock.json" in patterns  # From DEFAULT_EXCLUDE_FILES
        assert "*.log" in patterns  # From .gitignore
        assert "tmp/" in patterns  # From .gitignore

    def test_exclusion_manager_should_exclude(self, sample_repo, mock_logger):
        """Test exclusion manager's should_exclude method."""
        # Create exclusion manager
        manager = create_exclusion_manager(
            sample_repo, DEFAULT_EXCLUDE_PATTERNS, mock_logger
        )

        # Test excluding dot directories
        assert manager.should_exclude(os.path.join(sample_repo, ".git"))

        # Test excluding specified directories
        assert manager.should_exclude(os.path.join(sample_repo, "node_modules"))

        # Test excluding files matching patterns
        assert manager.should_exclude(os.path.join(sample_repo, "package-lock.json"))
        assert manager.should_exclude(os.path.join(sample_repo, "test.pyc"))

        # Test excluding files from .gitignore
        assert manager.should_exclude(os.path.join(sample_repo, "debug.log"))
        assert manager.should_exclude(os.path.join(sample_repo, "src", "package.cache"))
        assert manager.should_exclude(os.path.join(sample_repo, "tmp"))

        # Test not excluding normal files and directories
        assert not manager.should_exclude(os.path.join(sample_repo, "src"))
        assert not manager.should_exclude(os.path.join(sample_repo, "README.md"))
        assert not manager.should_exclude(os.path.join(sample_repo, "src", "main.py"))

    def test_exclusion_manager_should_exclude_file(self, sample_repo, mock_logger):
        """Test exclusion manager's should_exclude_file method."""
        # Create exclusion manager
        manager = create_exclusion_manager(
            sample_repo, DEFAULT_EXCLUDE_PATTERNS, mock_logger
        )

        # Test with full paths
        assert manager.should_exclude_file(
            os.path.join(sample_repo, "package-lock.json")
        )
        assert not manager.should_exclude_file(os.path.join(sample_repo, "README.md"))

        # Test with filenames only
        assert manager.should_exclude_file("package-lock.json")
        assert manager.should_exclude_file(".env")  # Hidden file
        assert manager.should_exclude_file("test.pyc")  # Matching wildcard
        assert not manager.should_exclude_file("README.md")

    def test_clean_directory(self, sample_repo, mock_logger):
        """Test cleaning a directory of excluded files."""
        # Create additional test files
        with open(os.path.join(sample_repo, "app.log"), "w") as f:
            f.write("log file")

        with open(os.path.join(sample_repo, "script.pyc"), "w") as f:
            f.write("compiled python")

        os.makedirs(os.path.join(sample_repo, "tmp"), exist_ok=True)
        with open(os.path.join(sample_repo, "tmp", "temp.txt"), "w") as f:
            f.write("temporary file")

        # Create exclusion manager
        manager = create_exclusion_manager(
            sample_repo, DEFAULT_EXCLUDE_PATTERNS, mock_logger
        )

        # Count files before cleanup
        file_count_before = 0
        for _, _, files in os.walk(sample_repo):
            file_count_before += len(files)

        # Clean the directory
        removed_count = manager.clean_directory(sample_repo)

        # Count files after cleanup
        file_count_after = 0
        for _, _, files in os.walk(sample_repo):
            file_count_after += len(files)

        # Check that files were removed
        assert removed_count > 0
        assert file_count_after < file_count_before

        # Check specific excluded files
        assert not os.path.exists(os.path.join(sample_repo, "package-lock.json"))
        assert not os.path.exists(os.path.join(sample_repo, "app.log"))
        assert not os.path.exists(os.path.join(sample_repo, "script.pyc"))
        assert not os.path.exists(os.path.join(sample_repo, "tmp", "temp.txt"))

        # Check that non-excluded files remain
        assert os.path.exists(os.path.join(sample_repo, "README.md"))
        assert os.path.exists(os.path.join(sample_repo, "src", "main.py"))
