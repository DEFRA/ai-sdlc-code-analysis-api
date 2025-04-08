"""Code chunk processing functionality."""

import glob
import logging
import os
from typing import Any, Callable

from ..models.code_chunk import CodeChunk


def create_simplified_structure(
    code_structure: dict[str, Any],
    repo_path: str,
    logger: logging.Logger,
    filter_comments: bool = False,
) -> tuple[dict[str, Any], int]:
    """Create a simplified version of the code structure for API consumption.

    Args:
        code_structure: Dictionary mapping file paths to code elements
        repo_path: Path to the repository
        logger: Logger instance for logging
        filter_comments: Whether to exclude comments from the simplified structure

    Returns:
        Tuple containing the simplified structure and the number of files processed
    """
    simplified_structure = {}

    # Limit the number of files to analyze to prevent token limit issues
    max_files = 300  # Limit to 300 files
    file_count = 0
    estimated_tokens = 0
    token_limit = 180000  # Leave room for system prompt and formatting overhead

    # Sort files by path to ensure consistency
    sorted_files = sorted(code_structure.keys())

    for file_path in sorted_files:
        # Skip if we've reached the maximum file count or estimated token limit
        if file_count >= max_files or estimated_tokens >= token_limit:
            logger.info(
                "Limiting analysis to %s files (token estimate: %s) to prevent token limit issues",
                file_count,
                estimated_tokens,
            )
            break

        elements = code_structure[file_path]
        # Use relative paths for better readability
        rel_path = os.path.relpath(file_path, repo_path)

        # Estimate tokens for this file's content
        file_tokens = len(rel_path) * 2  # Path tokens (rough estimate)

        # Add function and class names with details
        if "functions" in elements and elements["functions"]:
            file_tokens += sum(len(str(f)) for f in elements["functions"])

        if "classes" in elements and elements["classes"]:
            file_tokens += sum(len(str(c)) for c in elements["classes"])

        # Add comments only if not filtering them out
        if not filter_comments and "comments" in elements and elements["comments"]:
            file_tokens += sum(len(c["text"]) for c in elements["comments"])

        # Check if adding this file would exceed token limit
        if estimated_tokens + file_tokens >= token_limit:
            logger.info(
                "Reached estimated token limit at %s files (tokens: %s)",
                file_count,
                estimated_tokens,
            )
            break

        # Add file to simplified structure
        simplified_structure[rel_path] = {}

        # Add function and class names with details
        if "functions" in elements and elements["functions"]:
            logger.debug("Found functions: %s", elements["functions"])
            simplified_structure[rel_path]["functions"] = [
                {
                    "name": f["name"],
                    "type": f.get("type", "function"),
                    "class": f.get("class", None),
                }
                for f in elements["functions"]
            ]

        if "classes" in elements and elements["classes"]:
            simplified_structure[rel_path]["classes"] = [
                {"name": c["name"]} for c in elements["classes"]
            ]

        # Add comments only if not filtering them out
        if not filter_comments and "comments" in elements and elements["comments"]:
            comment_texts = [c["text"] for c in elements["comments"]]
            if comment_texts:
                simplified_structure[rel_path]["comments"] = comment_texts

        file_count += 1
        estimated_tokens += file_tokens

    return simplified_structure, file_count


def expand_glob_patterns(
    files_list: list[str], repo_path: str, logger: logging.Logger
) -> list[str]:
    """Expand any glob patterns in file paths to individual file paths.

    This function takes a list of file paths that may contain glob patterns
    (wildcards) and expands them to a list of individual file paths that match
    the patterns. It supports standard glob patterns as well as recursive patterns
    using "**" for subdirectory traversal.

    Pattern types supported:
    - Basic wildcards: "*.py", "file?.txt"
    - Character classes: "[abc].py"
    - Directory wildcards: "src/*.py"
    - Recursive wildcards: "**/*.py" (matches in all subdirectories)

    When a pattern contains "**", recursive directory traversal is automatically
    enabled. Patterns are resolved relative to the repository path if they are
    relative paths.

    Note that this function filters out directories and only includes actual files
    in the result. Duplicate files are also removed from the result.

    Args:
        files_list: List of file paths that may contain glob patterns
        repo_path: Path to the repository
        logger: Logger instance for logging

    Returns:
        List of expanded file paths with glob patterns resolved
    """
    expanded_files = []

    for file_pattern in files_list:
        # Handle absolute and relative paths
        abs_pattern = (
            os.path.join(repo_path, file_pattern)
            if not os.path.isabs(file_pattern)
            else file_pattern
        )

        # Check if pattern contains ** which requires recursive glob
        is_recursive = "**" in file_pattern

        # Use glob to expand the pattern with recursive support if needed
        matched_files = glob.glob(abs_pattern, recursive=is_recursive)

        # Filter out directories, we only want files
        matched_files = [f for f in matched_files if os.path.isfile(f)]

        if matched_files:
            # Convert absolute paths back to relative if the original was relative
            if not os.path.isabs(file_pattern):
                for file_path in matched_files:
                    expanded_files.append(os.path.relpath(file_path, repo_path))
            else:
                expanded_files.extend(matched_files)
        else:
            logger.warning("No files matched pattern: %s", file_pattern)

    # Remove duplicates but preserve order
    unique_files = []
    for file_path in expanded_files:
        if file_path not in unique_files:
            unique_files.append(file_path)

    return unique_files


def process_chunk(
    chunk_data: dict[str, Any],
    chunk_index: int,
    repo_path: str,
    logger: logging.Logger,
    handle_operation: Callable,
) -> CodeChunk:
    """Process a single chunk of data into a CodeChunk object.

    This function processes a chunk definition into a CodeChunk object, expanding
    glob patterns in file paths and reading the content of each file.

    Wildcard support:
    - Standard glob patterns like "*.py" are supported
    - Recursive patterns using "**" (e.g., "**/*.py") match files in all subdirectories
    - Multiple patterns can be specified to match different file types or locations
    - Only actual files (not directories) are included in the result

    Examples of supported patterns:
    - "*.py": All Python files in the root directory
    - "src/*.py": All Python files in the src directory
    - "**/*.py": All Python files in any directory or subdirectory
    - "docs/**/*.md": All Markdown files in the docs directory or its subdirectories

    Args:
        chunk_data: Dictionary with chunk information including files list with patterns
        chunk_index: Index of the chunk for logging purposes
        repo_path: Path to the repository
        logger: Logger instance for logging
        handle_operation: Function to handle operations with error handling

    Returns:
        CodeChunk object with expanded file list and combined content

    Raises:
        ValueError: If chunk data is invalid
    """
    # Validate chunk data
    if not isinstance(chunk_data, dict):
        error_msg = f"Invalid chunk data at index {chunk_index}: {chunk_data}"
        raise ValueError(error_msg)

    # Extract and validate required fields
    chunk_id = chunk_data.get("chunk_id", f"chunk_{chunk_index}")
    description = chunk_data.get("description", f"Auto-generated chunk {chunk_index}")
    files_list = chunk_data.get("files", [])

    if not isinstance(files_list, list):
        error_msg = f"Invalid files list for chunk {chunk_id}: {files_list}"
        raise ValueError(error_msg)

    # Expand glob patterns in file paths
    original_files_list = files_list.copy()
    expanded_files_list = expand_glob_patterns(files_list, repo_path, logger)

    logger.debug(
        "Processing chunk %s with %s files (expanded from %s patterns)",
        chunk_id,
        len(expanded_files_list),
        len(original_files_list),
    )

    # Build content from expanded file list
    content = ""
    for file_path in expanded_files_list:
        result, exception = handle_operation(
            read_file_content,
            f"Failed to read file {file_path}",
            file_path,
            repo_path,
            logger,
        )
        if result:
            content += result

    # Use the expanded files list in the chunk
    chunk = CodeChunk(
        chunk_id=chunk_id,
        description=description,
        files=expanded_files_list,
        content=content,
    )
    logger.debug("Successfully added chunk: %s", chunk_id)
    return chunk


def read_file_content(file_path: str, repo_path: str, logger: logging.Logger) -> str:
    """Read the content of a file.

    Args:
        file_path: Path to the file
        repo_path: Path to the repository
        logger: Logger instance for logging

    Returns:
        File content with header

    Raises:
        FileNotFoundError: If file is not found
        IOError: If file cannot be read
    """
    abs_path = (
        os.path.join(repo_path, file_path)
        if not os.path.isabs(file_path)
        else file_path
    )

    if not os.path.exists(abs_path):
        logger.warning("File not found: %s", abs_path)
        error_msg = f"File not found: {abs_path}"
        raise FileNotFoundError(error_msg)

    with open(abs_path, encoding="utf-8", errors="ignore") as f:
        content = f"\n\n--- {file_path} ---\n"
        content += f.read()

    return content
