"""Data models for the code analyzer.

This package contains data models used throughout the code analyzer:

- code_chunk: Models for code chunks and repository analysis results
"""

from .code_chunk import CodeChunk, RepositoryAnalysis

__all__ = [
    "CodeChunk",
    "RepositoryAnalysis",
]
