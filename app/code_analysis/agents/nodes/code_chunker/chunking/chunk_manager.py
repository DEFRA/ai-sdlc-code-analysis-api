import logging
from typing import Any, Callable, Optional

from anthropic import Anthropic

from app.code_analysis.agents.nodes.code_chunker.models.code_chunk import CodeChunk
from app.code_analysis.agents.nodes.code_chunker.utils.logging_utils import PromptLogger

from .chunk_processor import process_chunk
from .claude_integration import create_chunking_prompt, get_chunks_from_claude


class ChunkManager:
    """Manages chunking operations for code repositories."""

    def __init__(
        self,
        anthropic_client: Optional[Anthropic],
        api_timeout: int,
        logger: logging.Logger,
        prompt_logger: PromptLogger,
        filter_comments_above_tokens: int,
    ):
        """Initialize the chunk manager.

        Args:
            anthropic_client: Anthropic client for API calls
            api_timeout: Timeout for API calls in seconds
            logger: Logger instance
            prompt_logger: Logger for prompts and responses
            filter_comments_above_tokens: Threshold for filtering comments
        """
        self.anthropic_client = anthropic_client
        self.api_timeout = api_timeout
        self.logger = logger
        self.prompt_logger = prompt_logger
        self.filter_comments_above_tokens = filter_comments_above_tokens

    def chunk_codebase(
        self,
        simplified_structure: dict[str, Any],
        repo_path: str,
        directory_structure: str,
        handle_operation: Callable,
        operation_with_retry: Callable,
    ) -> list[CodeChunk]:
        """Chunk the codebase based on features.

        Args:
            simplified_structure: Dictionary containing the simplified code structure
            repo_path: Path to the repository
            directory_structure: Pre-generated directory structure string
            handle_operation: Function for handling operations with error handling
            operation_with_retry: Function for handling operations with retry

        Returns:
            List of CodeChunk objects

        Raises:
            RuntimeError: If chunking fails
        """
        try:
            # Create the prompt for Claude using the provided directory structure
            prompt = create_chunking_prompt(directory_structure, simplified_structure)

            # Log the prompt if enabled
            self.prompt_logger.log_prompt(prompt)

            # Get chunks from Claude
            chunks_data = get_chunks_from_claude(
                prompt,
                self.anthropic_client,
                self.api_timeout,
                self.logger,
                operation_with_retry,
            )

            # Log the response
            self.prompt_logger.log_response(chunks_data)

            # Process chunks
            chunks = []
            self.logger.info("Found %s chunks to process", len(chunks_data))
            for i, chunk_data in enumerate(chunks_data):
                result, exception = handle_operation(
                    process_chunk,
                    f"Error processing chunk {i}",
                    chunk_data,
                    i,
                    repo_path,
                    self.logger,
                    handle_operation,
                )
                if result:
                    chunks.append(result)

            self.logger.info("Successfully processed %s chunks", len(chunks))
            return chunks

        except Exception as e:
            self.logger.error("Failed to chunk codebase with Claude: %s", e)
            error_msg = f"Failed to chunk codebase: {e}"
            raise RuntimeError(error_msg) from e
