"""Chunking module.

This module provides functionality for chunking code repositories into logical units
for analysis by AI models. It includes tools for organizing and preparing code
content for analysis.

The chunking process divides a codebase into meaningful segments (chunks) based on
features, components, or other logical structures.

Features:
- Codebase organization into logical chunks
- File content extraction and preparation
- Support for glob patterns/wildcards in file paths (e.g., "**/*.py")
- Integration with language models for guided chunking
"""

from app.code_analysis.agents.nodes.code_chunker.models.code_chunk import CodeChunk

from .chunk_manager import ChunkManager
from .chunk_processor import (
    create_simplified_structure,
    process_chunk,
    read_file_content,
)
from .claude_integration import (
    create_chunking_prompt,
    extract_text_from_response,
    get_chunks_from_claude,
    parse_chunks_from_response,
)

__all__ = [
    "create_simplified_structure",
    "process_chunk",
    "read_file_content",
    "create_chunking_prompt",
    "get_chunks_from_claude",
    "extract_text_from_response",
    "parse_chunks_from_response",
    "ChunkManager",
    "CodeChunk",
]
