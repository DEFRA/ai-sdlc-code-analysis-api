"""Code analyzer for Git repositories.

This module provides tools for analyzing code in Git repositories,
including code structure parsing, chunking, and analysis.

Public API:
    CodeAnalyzer: Main class for analyzing a Git repository
    AnalyzerConfig: Configuration class for the analyzer
"""

# Main analyzer class
from .analyzer import CodeAnalyzer

# Configuration
from .config.analyzer_config import AnalyzerConfig

# Models
from .models.code_chunk import CodeChunk, RepositoryAnalysis

# Utility functions (organized by category)
# Error handling
from .utils.error_handling import handle_operation, operation_with_retry

# Logging
from .utils.logging_utils import PromptLogger, setup_logger

# Parsing
from .utils.parser_utils import ParserManager

# Repository management
from .utils.repository_utils import RepositoryManager

__all__ = [
    # Main classes
    "CodeAnalyzer",
    "AnalyzerConfig",
    # Models
    "CodeChunk",
    "RepositoryAnalysis",
    # Utilities
    "handle_operation",
    "operation_with_retry",
    "setup_logger",
    "PromptLogger",
    "RepositoryManager",
    "ParserManager",
]
