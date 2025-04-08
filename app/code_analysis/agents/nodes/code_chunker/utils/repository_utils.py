"""Repository utilities for the code analyzer.

This module contains functions for managing repositories and temporary directories.
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Callable

from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

from app.code_analysis.agents.nodes.code_chunker.repository.clone import (
    clone_repository,
)


class RepositoryManager:
    """Manages repository operations including cloning and temporary directory handling."""

    def __init__(self, repo_path_or_url: str, logger: logging.Logger):
        """Initialize the repository manager.

        Args:
            repo_path_or_url: Local path or URL to the repository
            logger: Logger instance to use for logging
        """
        self.repo_path_or_url = repo_path_or_url
        self.logger = logger
        self._temp_dir = None
        self.repo_path = None
        self.gitignore_spec = None
        self._setup_repo_path()

    def _load_gitignore(self, repo_path: str) -> PathSpec:
        """Load .gitignore patterns from the repository.

        Args:
            repo_path: Path to the repository

        Returns:
            PathSpec object with gitignore patterns
        """
        gitignore_path = os.path.join(repo_path, ".gitignore")
        patterns = []

        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            patterns.append(line)
                self.logger.debug("Loaded %d patterns from .gitignore", len(patterns))
            except Exception as e:
                self.logger.warning("Error reading .gitignore: %s", e)

        # Add default patterns
        default_patterns = [
            ".git/",
            "__pycache__/",
            "*.pyc",
            "node_modules/",
            "venv/",
            "dist/",
            "build/",
        ]
        patterns.extend(default_patterns)

        return PathSpec.from_lines(GitWildMatchPattern, patterns)

    def _copy_repository(self, source: str, dest: str):
        """Copy repository contents respecting .gitignore rules.

        Args:
            source: Source directory path
            dest: Destination directory path
        """
        self.gitignore_spec = self._load_gitignore(source)
        source_path = Path(source)

        for root, dirs, files in os.walk(source):
            # Convert to relative paths for gitignore matching
            rel_root = str(Path(root).relative_to(source_path))
            if rel_root == ".":
                rel_root = ""

            # Filter directories using gitignore
            dirs[:] = [
                d
                for d in dirs
                if not self.gitignore_spec.match_file(os.path.join(rel_root, d + "/"))
            ]

            # Create the corresponding destination directory
            dest_root = os.path.join(dest, rel_root)
            os.makedirs(dest_root, exist_ok=True)

            # Copy files that aren't ignored
            for file in files:
                rel_path = os.path.join(rel_root, file)
                if not self.gitignore_spec.match_file(rel_path):
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(dest_root, file)
                    shutil.copy2(src_file, dst_file)

    def _setup_repo_path(self):
        """Set up the repository path, creating a temporary directory if needed."""
        try:
            # Use the system's secure temp directory
            temp_base = tempfile.gettempdir()
            os.makedirs(temp_base, exist_ok=True)
            self._temp_dir = tempfile.mkdtemp(dir=temp_base)
            self.logger.debug("Created temporary directory at: %s", self._temp_dir)
        except (OSError, PermissionError) as e:
            self.logger.warning(
                "Could not create temporary directory in standard location: %s", e
            )
            self._temp_dir = tempfile.mkdtemp()
            self.logger.debug(
                "Created temporary directory at default location: %s", self._temp_dir
            )

        # Set repo path
        if self.repo_path_or_url.startswith(("http://", "https://", "git@")):
            self.repo_path = self._temp_dir
            self.logger.debug("Will clone repository to: %s", self.repo_path)
        else:
            # For local paths, create a copy in temp dir respecting .gitignore
            self.repo_path = os.path.join(self._temp_dir, "local_repo")
            self.logger.debug("Will copy local repository to: %s", self.repo_path)
            if os.path.exists(self.repo_path_or_url):
                self._copy_repository(self.repo_path_or_url, self.repo_path)
                self.logger.debug(
                    "Copied repository from %s to %s",
                    self.repo_path_or_url,
                    self.repo_path,
                )
            else:
                error_msg = (
                    f"Local repository path does not exist: {self.repo_path_or_url}"
                )
                self.logger.error(error_msg)
                raise ValueError(error_msg)

    def ensure_local_repository(
        self, handle_operation: Callable, api_timeout: int
    ) -> None:
        """Ensures repository is available locally, cloning it if necessary.

        Args:
            handle_operation: Function for handling operations with error handling
            api_timeout: Timeout for API operations
        """
        if self.repo_path_or_url.startswith(("http://", "https://", "git@")):
            self.logger.info("Cloning repository: %s", self.repo_path_or_url)
            clone_repository(
                self.repo_path_or_url,
                self.repo_path,
                self.logger,
                handle_operation,
                api_timeout,
            )
        else:
            self.logger.info("Using local repository: %s", self.repo_path)

    def cleanup(self):
        """Clean up temporary directory."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            self.logger.debug("Cleaning up temporary directory: %s", self._temp_dir)
            shutil.rmtree(self._temp_dir)
            self.logger.debug("Temporary directory removed")

    def should_skip_directory(self, directory_path: str) -> bool:
        """Determine if a directory should be skipped during analysis.

        Args:
            directory_path: Path to the directory

        Returns:
            True if the directory should be skipped, False otherwise
        """
        if self.gitignore_spec:
            rel_path = os.path.relpath(directory_path, self.repo_path)
            if self.gitignore_spec.match_file(rel_path + "/"):
                self.logger.debug("Skipping gitignored directory: %s", directory_path)
                return True

        # Skip hidden directories (those starting with a dot)
        path_parts = directory_path.split(os.sep)
        for part in path_parts:
            if part and part.startswith(".") and part != "." and part != "..":
                # It's a hidden directory like .git, .venv
                self.logger.debug("Skipping hidden directory: %s", directory_path)
                return True

        return False

    def should_skip_file(self, filename: str) -> bool:
        """Determine if a file should be skipped during analysis.

        Args:
            filename: Name of the file

        Returns:
            True if the file should be skipped, False otherwise
        """
        # Skip hidden files
        if filename.startswith("."):
            self.logger.debug("Skipping hidden file: %s", filename)
            return True

        return False
