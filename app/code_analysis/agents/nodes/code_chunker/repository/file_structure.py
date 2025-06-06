"""File structure functionality for analyzing repository structure."""

import logging
import os


def generate_file_structure(repo_path: str, logger: logging.Logger) -> str:
    """Generate a text representation of the repository's file structure.

    Args:
        repo_path: Path to the repository
        logger: Logger instance for logging

    Returns:
        String representation of the directory tree
    """
    logger.info("Generating file structure representation")
    tree = _generate_tree(repo_path, logger)
    logger.debug(
        "File structure representation generated (%s lines)",
        len(tree.split(os.linesep)),
    )
    return tree


def _generate_tree(startpath: str, logger: logging.Logger) -> str:
    """Generate a text representation of the directory structure.

    Args:
        startpath: Path to start the tree from
        logger: Logger instance for logging

    Returns:
        String representation of the directory tree
    """
    logger.debug("Generating directory tree for %s", startpath)

    output = []
    prefix = "│   "

    # Recursively add the directory contents
    _add_directory_contents(startpath, "", output, prefix, logger)

    logger.debug("Generated tree with %s lines", len(output))
    return "\n".join(output)


def _add_directory_contents(
    path: str,
    indent: str,
    output: list,
    prefix: str,
    logger: logging.Logger,
):
    """Recursively add directory contents to output."""
    dirs, files = _get_directory_contents(path, logger)

    # Sort for consistent output
    dirs.sort()
    files.sort()

    # Process subdirectories
    _add_subdirectories(path, dirs, files, indent, output, prefix, logger)

    # Process files
    _add_files(files, indent, output)


def _get_directory_contents(path: str, logger: logging.Logger):
    """Get the contents of a directory, handling permissions."""
    dirs = []
    files = []

    try:
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_dir():
                    dirs.append(entry.name)
                else:
                    files.append(entry.name)
    except PermissionError as e:
        logger.warning("Permission error accessing %s: %s", path, e)

    return dirs, files


def _add_subdirectories(
    path: str,
    dirs: list,
    files: list,
    indent: str,
    output: list,
    prefix: str,
    logger: logging.Logger,
):
    """Add subdirectories to the output."""
    for i, name in enumerate(dirs):
        is_last = (i == len(dirs) - 1) and not files
        marker = "└── " if is_last else "├── "
        output.append(f"{indent}{marker}{name}/")

        new_indent = indent + ("    " if is_last else prefix)
        _add_directory_contents(
            os.path.join(path, name), new_indent, output, prefix, logger
        )


def _add_files(files: list, indent: str, output: list):
    """Add files to the output."""
    for i, name in enumerate(files):
        is_last = i == len(files) - 1
        marker = "└── " if is_last else "├── "
        output.append(f"{indent}{marker}{name}")


def detect_languages(
    repo_path: str,
    supported_languages: list[str] | dict[str, str],
    logger: logging.Logger,
) -> list[str]:
    """Detect programming languages used in the repository.

    Args:
        repo_path: Path to the repository
        supported_languages: List of supported file extensions or dictionary mapping file extensions to language names
        logger: Logger instance for logging

    Returns:
        List of detected languages
    """
    logger.debug("Detecting languages in %s", repo_path)
    languages = set()

    for _root, _, files in os.walk(repo_path):
        for file in files:
            ext = os.path.splitext(file)[1]
            if isinstance(supported_languages, dict):
                if ext in supported_languages:
                    lang = supported_languages[ext]
                    languages.add(lang)
                    logger.debug("Detected language %s from file %s", lang, file)
            else:  # List of extensions
                if ext in supported_languages:
                    languages.add(ext)
                    logger.debug("Detected language %s from file %s", ext, file)

    result = list(languages)
    logger.debug("Detected languages: %s", result)
    return result
