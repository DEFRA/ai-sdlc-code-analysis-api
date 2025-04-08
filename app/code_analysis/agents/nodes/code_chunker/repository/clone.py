"""Repository cloning functionality."""

import logging
import os
import re
import shutil
import subprocess
import time
from typing import Callable, TypeVar

# Type variable for generic return type
T = TypeVar("T")


def clone_repository(
    repository_url: str,
    repo_path: str,
    logger: logging.Logger,
    handle_operation: Callable,
    timeout: int,
) -> str:
    """Clone the repository to the specified path.

    Args:
        repository_url: URL of the repository to clone
        repo_path: Path where to clone the repository
        logger: Logger instance for logging
        handle_operation: Function to handle operations with error handling
        timeout: Timeout in seconds for the clone operation

    Returns:
        Path to the cloned repository

    Raises:
        RuntimeError: If clone operation fails
    """
    # If it's a local path, just return the existing repo path
    if not repository_url.startswith(("http://", "https://", "git@")):
        logger.debug("Using local repository path: %s", repo_path)
        return repo_path

    # For remote URLs, clone the repository
    def _clone_operation():
        nonlocal repository_url, repo_path, logger, timeout
        start_time = time.time()

        try:
            # Validate and prepare for cloning
            _validate_git_url(repository_url, logger)
            _clean_existing_repo(repo_path, logger)

            # Clone the repository
            logger.info("Cloning repository from %s to %s", repository_url, repo_path)
            _initialize_git_repo(repo_path, repository_url, timeout, logger)

            logger.info(
                "Successfully cloned repository in %.2f seconds",
                time.time() - start_time,
            )
            return repo_path
        except Exception as e:
            # Ensure proper cleanup on any exception
            _cleanup_on_error(repo_path, logger)
            raise e

    # Use the _handle_operation pattern for consistent error handling
    result, error = handle_operation(
        _clone_operation,
        "Failed to clone repository",
    )

    if error:
        # Clean up on failure
        _cleanup_on_error(repo_path, logger)
        error_msg = f"Failed to clone repository: {str(error)}"
        raise RuntimeError(error_msg)

    return result


def _validate_git_url(repository_url, logger):
    """Validate the git URL to ensure it's safe"""
    if not is_valid_git_url(repository_url):
        error_msg = f"Invalid repository URL format: {repository_url}"
        logger.error("Invalid repository URL format detected")
        raise ValueError(error_msg)


def _clean_existing_repo(repo_path, logger):
    """Clean up any existing repository directory"""
    if os.path.exists(repo_path):
        logger.debug("Removing existing repository directory: %s", repo_path)
        shutil.rmtree(repo_path)


def _initialize_git_repo(repo_path, repository_url, timeout, logger):
    """Initialize a new git repository and set it up with the remote"""
    # Find git executable
    git_executable = shutil.which("git")
    if not git_executable:
        error_msg = "Git executable not found in PATH"
        raise RuntimeError(error_msg)

    # Prepare the normalized arguments for safety
    normalized_repo_path = os.path.abspath(os.path.normpath(repo_path))

    # Execute git clone safely
    try:
        # Save the original directory
        original_dir = os.getcwd()
        os.makedirs(normalized_repo_path, exist_ok=True)
        os.chdir(normalized_repo_path)

        # Initialize repository
        _run_git_init(git_executable, logger)
        _add_git_remote(git_executable, repository_url, logger)
        _fetch_from_remote(git_executable, timeout, logger)
        _checkout_branch(git_executable, logger)

        # Return to original directory
        os.chdir(original_dir)
    except subprocess.TimeoutExpired as e:
        # Return to original directory if we changed it
        if "original_dir" in locals():
            os.chdir(original_dir)

        logger.warning("Git operation timed out after %s seconds", timeout)
        timeout_msg = f"Git operation timed out after {timeout} seconds"
        raise TimeoutError(timeout_msg) from e


def _run_git_init(git_executable, logger):
    """Initialize a new git repository"""
    init_result = subprocess.run(  # noqa: S603
        [git_executable, "init"],
        timeout=30,
        capture_output=True,
        text=True,
        check=False,
    )

    if init_result.returncode != 0:
        error_msg = init_result.stderr
        logger.error("Git init failed: %s", error_msg)
        git_error_msg = f"Git init failed: {error_msg}"
        raise RuntimeError(git_error_msg)


def _add_git_remote(git_executable, repository_url, logger):
    """Add a remote to the git repository"""
    add_remote_result = subprocess.run(  # noqa: S603
        [git_executable, "remote", "add", "origin", repository_url],
        timeout=30,
        capture_output=True,
        text=True,
        check=False,
    )

    if add_remote_result.returncode != 0:
        error_msg = add_remote_result.stderr
        logger.error("Git remote add failed: %s", error_msg)
        git_error_msg = f"Git remote add failed: {error_msg}"
        raise RuntimeError(git_error_msg)


def _fetch_from_remote(git_executable, timeout, logger):
    """Fetch from the remote repository"""
    fetch_result = subprocess.run(  # noqa: S603
        [git_executable, "fetch", "--depth", "1", "origin"],
        timeout=timeout,
        capture_output=True,
        text=True,
        check=False,
    )

    if fetch_result.returncode != 0:
        error_msg = fetch_result.stderr
        logger.error("Git fetch failed: %s", error_msg)
        git_error_msg = f"Git fetch failed: {error_msg}"
        raise RuntimeError(git_error_msg)


def _checkout_branch(git_executable, logger):
    """Determine and checkout the default branch"""
    branch_to_checkout = _determine_default_branch(git_executable, logger)

    if not branch_to_checkout:
        logger.error("Could not determine default branch")
        git_error_msg = "Could not determine default branch"
        raise RuntimeError(git_error_msg)

    # Create and checkout the local branch
    create_branch = subprocess.run(  # noqa: S603
        [
            git_executable,
            "checkout",
            "-b",
            branch_to_checkout,
            f"origin/{branch_to_checkout}",
        ],
        timeout=30,
        capture_output=True,
        text=True,
        check=False,
    )

    if create_branch.returncode != 0:
        error_msg = create_branch.stderr
        logger.error("Git branch creation failed: %s", error_msg)
        git_error_msg = f"Git branch creation failed: {error_msg}"
        raise RuntimeError(git_error_msg)


def _determine_default_branch(git_executable, logger):
    """Determine the default branch of the repository"""
    # Try main branch
    checkout_main = subprocess.run(  # noqa: S603
        [git_executable, "checkout", "origin/main"],
        timeout=30,
        capture_output=True,
        text=True,
        check=False,
    )

    if checkout_main.returncode == 0:
        branch_to_checkout = "main"
        logger.info("Using 'main' as default branch")
        return branch_to_checkout

    # Try master branch
    checkout_master = subprocess.run(  # noqa: S603
        [git_executable, "checkout", "origin/master"],
        timeout=30,
        capture_output=True,
        text=True,
        check=False,
    )

    if checkout_master.returncode == 0:
        branch_to_checkout = "master"
        logger.info("Using 'master' as default branch")
        return branch_to_checkout

    # Try to list remote branches and use the first one
    return _find_alternative_branch(git_executable, logger)


def _find_alternative_branch(git_executable, logger):
    """Find an alternative branch when main and master don't exist"""
    list_branches = subprocess.run(  # noqa: S603
        [git_executable, "branch", "-r"],
        timeout=30,
        capture_output=True,
        text=True,
        check=False,
    )

    if list_branches.returncode == 0 and list_branches.stdout.strip():
        # Extract branch names, typically in format "origin/branch-name"
        branches = list_branches.stdout.strip().split("\n")
        if branches:
            # Take the first branch that isn't HEAD
            for branch in branches:
                branch = branch.strip()
                if branch and "HEAD" not in branch:
                    remote_branch = branch
                    # Remove "origin/" prefix if it exists
                    local_branch = (
                        remote_branch.split("/", 1)[1]
                        if "/" in remote_branch
                        else remote_branch
                    )
                    branch_to_checkout = local_branch
                    logger.info(
                        "Using '%s' as default branch",
                        branch_to_checkout,
                    )
                    return branch_to_checkout

    return None


def _cleanup_on_error(repo_path, logger):
    """Clean up repository directory after an error"""
    if os.path.exists(repo_path):
        try:
            logger.debug(
                "Cleaning up repository directory after failure: %s", repo_path
            )
            shutil.rmtree(repo_path)
        except Exception as cleanup_error:
            logger.warning("Failed to clean up after error: %s", cleanup_error)


def is_valid_git_url(url: str) -> bool:
    """Validate git URL for security.

    Args:
        url: Repository URL to validate

    Returns:
        True if URL is valid, False otherwise
    """
    # Only allow specific URL patterns for git repos
    http_pattern = r"^https?://[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](\.[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9])*(/[a-zA-Z0-9\-._~%!$&\'()*+,;=:@/]+)*$"
    ssh_pattern = r"^git@[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](\.[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9])*:[a-zA-Z0-9\-._~%!$&\'()*+,;=:@/]+(/[a-zA-Z0-9\-._~%!$&\'()*+,;=:@/]+)*$"

    return (
        re.match(http_pattern, url) is not None
        or re.match(ssh_pattern, url) is not None
    )
