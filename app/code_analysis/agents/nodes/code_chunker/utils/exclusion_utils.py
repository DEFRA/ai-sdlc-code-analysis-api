"""Exclusion utilities for code analysis.

This module contains functions for determining which files and directories
should be excluded from code analysis.
"""

import logging
import os
import shutil
from fnmatch import fnmatch
from typing import Callable

from pathspec import PathSpec


class ExclusionManager:
    """Manages exclusion patterns and provides utilities for checking paths."""

    def __init__(
        self,
        exclude_patterns: list[str],
        gitignore_spec: PathSpec = None,
        repo_path: str = None,
        logger: logging.Logger = None,
    ):
        """Initialize the exclusion manager.

        Args:
            exclude_patterns: List of patterns to exclude
            gitignore_spec: PathSpec object with gitignore patterns
            repo_path: Path to the repository (needed for gitignore)
            logger: Logger instance to use for logging
        """
        self.exclude_patterns = exclude_patterns
        self.gitignore_spec = gitignore_spec
        self.repo_path = repo_path
        self.logger = logger or logging.getLogger(__name__)
        self._pattern_matcher = self._create_pattern_matcher()

    def _is_gitignored(self, path: str) -> bool:
        """Check if path is matched by gitignore patterns.

        Args:
            path: Path to check against gitignore patterns

        Returns:
            True if path is matched by gitignore patterns, False otherwise
        """
        if not self.gitignore_spec or not self.repo_path:
            return False

        try:
            rel_path = os.path.relpath(path, self.repo_path)
            if self.gitignore_spec.match_file(rel_path):
                self.logger.debug("Skipping gitignored path: %s", path)
                return True
        except ValueError:
            # This can happen if the paths are on different drives on Windows
            pass

        return False

    def _is_hidden_path(self, path_parts: list[str]) -> bool:
        """Check if any path component is hidden (starts with dot).

        Args:
            path_parts: List of path components

        Returns:
            True if any path component is hidden, False otherwise
        """
        for part in path_parts:
            if part and part.startswith(".") and part != "." and part != "..":
                self.logger.debug("Skipping hidden path: %s", "/".join(path_parts))
                return True
        return False

    def _matches_directory_pattern(
        self, path: str, path_parts: list[str], pattern: str
    ) -> bool:
        """Check if path matches a directory pattern (ending with /).

        Args:
            path: Full path to check
            path_parts: List of path components
            pattern: Pattern to check against

        Returns:
            True if path matches the directory pattern, False otherwise
        """
        if not pattern.endswith("/"):
            return False

        dir_pattern = pattern[:-1]  # Remove the trailing slash

        # Check if the pattern appears anywhere in the path
        if f"/{dir_pattern}/" in f"/{path}/" or path.endswith(f"/{dir_pattern}"):
            self.logger.debug(
                "Excluding directory path %s matching pattern %s",
                path,
                pattern,
            )
            return True

        # Check if any directory in the path matches the pattern
        for part in path_parts:
            if part == dir_pattern:
                self.logger.debug(
                    "Excluding path %s with directory component %s matching pattern %s",
                    path,
                    part,
                    pattern,
                )
                return True

        return False

    def _matches_file_pattern(
        self, path: str, path_parts: list[str], basename: str, pattern: str
    ) -> bool:
        """Check if file matches a pattern.

        Args:
            path: Full path to check
            path_parts: List of path components
            basename: Basename of the path
            pattern: Pattern to check against

        Returns:
            True if path matches the file pattern, False otherwise
        """
        # Check if any part of the path matches the pattern
        if any(fnmatch(part, pattern) for part in path_parts):
            self.logger.debug(
                "Excluding path %s with component matching pattern %s",
                path,
                pattern,
            )
            return True

        # Check basename against pattern
        if fnmatch(basename, pattern):
            self.logger.debug("Excluding path %s matching pattern %s", path, pattern)
            return True

        return False

    def _create_pattern_matcher(self) -> Callable[[str], bool]:
        """Create a function that checks if a path should be excluded.

        Returns:
            Function that checks if a path should be excluded
        """

        def should_exclude(path: str) -> bool:
            """Check if path should be excluded based on patterns."""
            basename = os.path.basename(path)
            path_parts = path.split(os.sep)

            # Check gitignore patterns
            if self._is_gitignored(path):
                return True

            # Skip hidden files and directories
            if self._is_hidden_path(path_parts):
                return True

            # Check against exclude patterns
            for pattern in self.exclude_patterns:
                # Check directory patterns
                if self._matches_directory_pattern(path, path_parts, pattern):
                    return True

                # Check file patterns
                if self._matches_file_pattern(path, path_parts, basename, pattern):
                    return True

            return False

        return should_exclude

    def should_exclude(self, path: str) -> bool:
        """Determine if a path should be excluded during analysis.

        Args:
            path: Path to check

        Returns:
            True if the path should be excluded, False otherwise
        """
        return self._pattern_matcher(path)

    def should_exclude_file(self, filename: str) -> bool:
        """Determine if a file should be excluded during analysis.

        Args:
            filename: Name of the file or full path to the file

        Returns:
            True if the file should be excluded, False otherwise
        """
        # If given a full path
        if os.path.dirname(filename):
            return self._pattern_matcher(filename)

        # If only a filename is provided (no directory path)
        # Skip hidden files
        if filename.startswith("."):
            self.logger.debug("Skipping hidden file: %s", filename)
            return True

        # Check against the exclude patterns with wildcard matching
        for pattern in self.exclude_patterns:
            if fnmatch(filename, pattern):
                self.logger.debug(
                    "Skipping file %s matching pattern %s", filename, pattern
                )
                return True

        return False

    def clean_directory(self, directory_path: str) -> int:
        """Remove files that match exclusion patterns from a directory.

        Args:
            directory_path: Path to the directory to clean

        Returns:
            Number of files removed
        """
        removed_count = 0
        for root, dirs, files in os.walk(directory_path, topdown=True):
            # Process directories first
            dirs_to_remove = []
            for d in dirs:
                dir_path = os.path.join(root, d)
                if self.should_exclude(dir_path):
                    # Mark directory for removal but keep it in dirs list
                    # so we can process its contents first
                    dirs_to_remove.append(d)
                    self.logger.debug("Directory marked for removal: %s", dir_path)

            # Process files in current directory
            for file in files:
                file_path = os.path.join(root, file)
                if self.should_exclude(file_path):
                    try:
                        os.remove(file_path)
                        self.logger.debug("Removed excluded file: %s", file_path)
                        removed_count += 1
                    except OSError as e:
                        self.logger.warning(
                            "Failed to remove file %s: %s", file_path, e
                        )

            # After processing all files, remove the excluded directories
            for d in dirs_to_remove:
                dir_path = os.path.join(root, d)
                try:
                    # Use shutil.rmtree to remove directory and all contents
                    shutil.rmtree(dir_path)
                    # Count removed files (approximate)
                    for _, _, fs in os.walk(dir_path):
                        removed_count += len(fs)
                    self.logger.debug("Removed excluded directory: %s", dir_path)
                except OSError as e:
                    self.logger.warning(
                        "Failed to remove directory %s: %s", dir_path, e
                    )

            # Update dirs list to skip directories we've removed
            dirs[:] = [d for d in dirs if d not in dirs_to_remove]

        return removed_count


def get_combined_exclude_patterns(
    base_patterns: list[str] = None,
    gitignore_path: str = None,
    logger: logging.Logger = None,
) -> list[str]:
    """Get the combined list of exclude patterns from base patterns and gitignore.

    Args:
        base_patterns: List of base patterns to exclude
        gitignore_path: Path to the .gitignore file
        logger: Logger instance to use for logging

    Returns:
        Combined list of patterns to exclude
    """
    logger = logger or logging.getLogger(__name__)
    combined_patterns = base_patterns.copy() if base_patterns else []

    # Add patterns from .gitignore if it exists
    if gitignore_path and os.path.exists(gitignore_path):
        try:
            with open(gitignore_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        combined_patterns.append(line)
            logger.debug(
                "Loaded %d patterns from .gitignore",
                len(combined_patterns) - len(base_patterns or []),
            )
        except Exception as e:
            logger.warning("Error reading .gitignore: %s", e)

    return combined_patterns


def create_exclusion_manager(
    repo_path: str, base_patterns: list[str], logger: logging.Logger = None
) -> ExclusionManager:
    """Create an exclusion manager for a repository.

    Args:
        repo_path: Path to the repository
        base_patterns: List of base patterns to exclude
        logger: Logger instance to use for logging

    Returns:
        Configured ExclusionManager instance
    """
    logger = logger or logging.getLogger(__name__)

    # Combine base patterns with gitignore patterns
    gitignore_path = os.path.join(repo_path, ".gitignore")
    all_patterns = get_combined_exclude_patterns(base_patterns, gitignore_path, logger)

    # Create gitignore PathSpec if .gitignore exists
    gitignore_spec = None
    if os.path.exists(gitignore_path):
        from pathspec import PathSpec
        from pathspec.patterns import GitWildMatchPattern

        gitignore_patterns = []
        try:
            with open(gitignore_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        gitignore_patterns.append(line)
            gitignore_spec = PathSpec.from_lines(
                GitWildMatchPattern, gitignore_patterns
            )
        except Exception as e:
            logger.warning("Error creating gitignore PathSpec: %s", e)

    # Create and return the exclusion manager
    return ExclusionManager(
        exclude_patterns=all_patterns,
        gitignore_spec=gitignore_spec,
        repo_path=repo_path,
        logger=logger,
    )
