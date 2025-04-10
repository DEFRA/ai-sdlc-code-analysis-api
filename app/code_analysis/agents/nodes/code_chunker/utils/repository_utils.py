"""Repository utilities for the code analyzer.

This module contains functions for managing repositories and temporary directories.
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Callable

from app.code_analysis.agents.nodes.code_chunker.config.exclusion_config import (
    DEFAULT_EXCLUDE_PATTERNS,
)
from app.code_analysis.agents.nodes.code_chunker.repository.clone import (
    clone_repository,
)
from app.code_analysis.agents.nodes.code_chunker.utils.exclusion_utils import (
    create_exclusion_manager,
)


class RepositoryManager:
    """Manages repository operations including cloning and temporary directory handling."""

    def __init__(
        self,
        repo_path_or_url: str,
        logger: logging.Logger,
    ):
        """Initialize the repository manager.

        Args:
            repo_path_or_url: Local path or URL to the repository
            logger: Logger instance to use for logging
        """
        self.repo_path_or_url = repo_path_or_url
        self.logger = logger
        self._temp_dir = None
        self.repo_path = None
        self._base_exclude_patterns = DEFAULT_EXCLUDE_PATTERNS
        self.exclusion_manager = None
        self._setup_repo_path()

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

    def _copy_repository(self, source: str, dest: str):
        """Copy repository contents respecting exclude patterns and gitignore rules.

        Args:
            source: Source directory path
            dest: Destination directory path
        """
        # Create an exclusion manager for the source repository
        self.exclusion_manager = create_exclusion_manager(
            source, self._base_exclude_patterns, self.logger
        )

        # Use the pattern matcher during the copy process
        source_path = Path(source)
        for root, dirs, files in os.walk(source):
            # Convert to relative paths for matching
            rel_root = str(Path(root).relative_to(source_path))
            if rel_root == ".":
                rel_root = ""

            # Check if this directory should be excluded
            if self.exclusion_manager.should_exclude(root):
                self.logger.debug("Skipping excluded directory: %s", root)
                # Clear the dirs list to skip processing subdirectories
                dirs[:] = []
                continue

            # Filter directories using our pattern matcher
            dirs[:] = [
                d
                for d in dirs
                if not self.exclusion_manager.should_exclude(os.path.join(root, d))
            ]

            # Create the corresponding destination directory
            dest_root = os.path.join(dest, rel_root)
            os.makedirs(dest_root, exist_ok=True)

            # Copy files that aren't excluded
            for file in files:
                src_file = os.path.join(root, file)
                if not self.exclusion_manager.should_exclude(src_file):
                    dst_file = os.path.join(dest_root, file)
                    shutil.copy2(src_file, dst_file)
                else:
                    self.logger.debug("Skipping excluded file: %s", src_file)

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

            # Create the exclusion manager for the cloned repository
            self.exclusion_manager = create_exclusion_manager(
                self.repo_path, self._base_exclude_patterns, self.logger
            )

            # Clean the repository to remove excluded files
            removed_count = self.exclusion_manager.clean_directory(self.repo_path)
            if removed_count > 0:
                self.logger.info(
                    "Removed %d excluded files from cloned repository", removed_count
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
        if not self.exclusion_manager:
            self.logger.warning("ExclusionManager not initialized, initializing now")
            self.exclusion_manager = create_exclusion_manager(
                self.repo_path, self._base_exclude_patterns, self.logger
            )

        return self.exclusion_manager.should_exclude(directory_path)

    def should_skip_file(self, filename: str) -> bool:
        """Determine if a file should be skipped during analysis.

        Args:
            filename: Name of the file or full path to the file

        Returns:
            True if the file should be skipped, False otherwise
        """
        if not self.exclusion_manager:
            self.logger.warning("ExclusionManager not initialized, initializing now")
            self.exclusion_manager = create_exclusion_manager(
                self.repo_path, self._base_exclude_patterns, self.logger
            )

        return self.exclusion_manager.should_exclude_file(filename)

    def get_excluded_files(self) -> list[str]:
        """Get the list of files and patterns that should be excluded from analysis.

        Returns:
            List of file and directory patterns to exclude
        """
        if not self.exclusion_manager:
            return self._base_exclude_patterns

        return self.exclusion_manager.exclude_patterns
