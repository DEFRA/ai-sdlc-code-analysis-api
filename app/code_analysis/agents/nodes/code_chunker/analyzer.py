import logging
import os
from typing import Any, Optional

import tiktoken
from anthropic import Anthropic

from .chunking.chunk_manager import ChunkManager
from .chunking.chunk_processor import create_simplified_structure
from .chunking.claude_integration import CLAUDE_SYSTEM_PROMPT, create_chunking_prompt
from .config.analyzer_config import AnalyzerConfig
from .models.code_chunk import RepositoryAnalysis
from .repository.file_structure import detect_languages, generate_file_structure
from .utils.error_handling import handle_operation, operation_with_retry
from .utils.logger import logger as custom_logger
from .utils.logging_utils import PromptLogger, log_message
from .utils.parser_utils import ParserManager
from .utils.repository_utils import RepositoryManager


class CodeAnalyzer:
    """Analyzes a Git repository and chunks its code based on features."""

    def __init__(
        self,
        config: AnalyzerConfig,
    ):
        """Initialize the code analyzer with configuration.

        Args:
            config: AnalyzerConfig instance with all settings
        """
        self.config = config

        # Use custom logger if available
        self.logger = custom_logger
        self.logger.setLevel(config.log_level)

        # Initialize Anthropic client if API key is provided
        self.anthropic_client = (
            Anthropic(api_key=config.anthropic_api_key)
            if config.anthropic_api_key
            else None
        )

        # Log Anthropic client initialization status
        if self.anthropic_client is None:
            self.logger.warning(
                "Anthropic client not initialized. API key is missing or invalid."
            )
        else:
            self.logger.info("Anthropic client successfully initialized.")

        # Set up logging for prompts and responses
        self.prompt_logger = PromptLogger(
            config.log_file_path, config.log_prompts, config.log_responses
        )

        # Initialize repository manager
        self.repo_manager = RepositoryManager(config.repo_path_or_url, self.logger)

        # Initialize parser manager
        self.parser_manager = ParserManager(self.logger)
        if not config.use_tree_sitter:
            self.parser_manager.using_tree_sitter = False
            self.logger.info("Tree-sitter parsing disabled by configuration")

        # Initialize chunk manager
        self.chunk_manager = ChunkManager(
            self.anthropic_client,
            config.api_timeout,
            self.logger,
            self.prompt_logger,
            config.filter_comments_above_tokens,
        )

        # Initialize token counter
        self.token_counter = tiktoken.get_encoding("cl100k_base")

    @classmethod
    def from_params(
        cls,
        repo_path_or_url: str,
        anthropic_api_key: Optional[str] = None,
        log_prompts: bool = False,
        log_file_path: Optional[str] = None,
        log_responses: bool = False,
        api_timeout: int = 120,
        log_level: int = logging.INFO,
        max_files_to_parse: int = 1000,
        use_tree_sitter: bool = False,
    ):
        """Create an analyzer from individual parameters for backward compatibility.

        Args:
            repo_path_or_url: Local path or URL to the repository
            anthropic_api_key: API key for Anthropic
            log_prompts: Whether to log prompts sent to Anthropic
            log_file_path: Path to the log file
            log_responses: Whether to log responses from Anthropic
            api_timeout: Timeout in seconds for API calls
            log_level: Logging level to use
            max_files_to_parse: Maximum number of files to parse
            use_tree_sitter: Whether to use tree-sitter for code parsing

        Returns:
            CodeAnalyzer instance
        """
        config = AnalyzerConfig(
            repo_path_or_url=repo_path_or_url,
            anthropic_api_key=anthropic_api_key,
            log_prompts=log_prompts,
            log_file_path=log_file_path,
            log_responses=log_responses,
            api_timeout=api_timeout,
            log_level=log_level,
            max_files_to_parse=max_files_to_parse,
            use_tree_sitter=use_tree_sitter,
        )
        return cls(config)

    def __enter__(self):
        """Support context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when exiting context."""
        self.repo_manager.cleanup()

        if exc_type is not None:
            log_message(
                self.logger,
                logging.ERROR,
                f"Exception during context exit: {exc_type.__name__}: {exc_val}",
            )
            log_message(
                self.logger,
                logging.DEBUG,
                f"Exception traceback: {exc_tb}",
                include_traceback=True,
            )

    def _handle_operation(self, operation, error_message, *args, **kwargs):
        """Wrapper for handle_operation with logger included."""
        return handle_operation(operation, error_message, self.logger, *args, **kwargs)

    def _operation_with_retry(
        self, operation, error_message, logger=None, max_retries=3, *args, **kwargs
    ):
        """Wrapper for operation_with_retry with logger included."""
        # Remove max_retries from kwargs if present to avoid duplicate parameters
        if "max_retries" in kwargs:
            kwargs.pop("max_retries")
        # Use self.logger if logger is not provided
        logger = logger or self.logger
        return operation_with_retry(
            operation, error_message, logger, max_retries, *args, **kwargs
        )

    def count_tokens(self, prompt: str) -> int:
        """Count the number of tokens in a text string using tiktoken.

        This includes both the user prompt and the system prompt that will be sent to Claude,
        plus overhead for message formatting and metadata.

        Args:
            prompt: Text to count tokens for

        Returns:
            Number of tokens
        """
        try:
            # Count tokens for both system and user prompts
            system_tokens = len(self.token_counter.encode(CLAUDE_SYSTEM_PROMPT))
            user_tokens = len(self.token_counter.encode(prompt))

            # Add overhead for message formatting and metadata (approximately 100-200 tokens)
            formatting_overhead = 200
            total_tokens = system_tokens + user_tokens + formatting_overhead

            self.logger.debug(
                "Token count breakdown - System: %d, User: %d, Formatting: %d, Total: %d",
                system_tokens,
                user_tokens,
                formatting_overhead,
                total_tokens,
            )

            return total_tokens
        except Exception as e:
            self.logger.error("Error counting tokens: %s", e)
            return 0

    def analyze_repository(self) -> RepositoryAnalysis:
        """Analyze a repository and return chunked code analysis."""
        try:
            # Ensure repository is available locally
            self.repo_manager.ensure_local_repository(
                self._handle_operation, self.config.api_timeout
            )

            # Generate file structure first since we need it for token counting
            self.logger.info("Generating file structure")
            file_structure = generate_file_structure(
                self.repo_manager.repo_path, self.logger
            )

            # Detect languages
            self.logger.info("Detecting programming languages")
            languages = detect_languages(
                self.repo_manager.repo_path,
                self.parser_manager.SUPPORTED_LANGUAGES,
                self.logger,
            )
            self.logger.info("Detected languages: %s", ", ".join(languages))

            # Parse code structure
            self.logger.info("Parsing code structure")
            code_structure = self.parse_code_structure()
            self.logger.info("Parsed %s files", len(code_structure))

            # Create initial prompt with directory structure to check total token count
            simplified_structure, file_count = create_simplified_structure(
                code_structure,
                self.repo_manager.repo_path,
                self.logger,
                filter_comments=False,
            )
            prompt = create_chunking_prompt(file_structure, simplified_structure)
            token_count = self.count_tokens(prompt)
            self.logger.info(
                "Initial prompt token count (with directory structure): %s", token_count
            )

            # If token count is too high, recreate structure without comments
            if (
                token_count > self.config.filter_comments_above_tokens
                and self.config.filter_comments_above_tokens > 0
            ):
                self.logger.info(
                    "Token count %s exceeds threshold %s, filtering out comments",
                    token_count,
                    self.config.filter_comments_above_tokens,
                )
                simplified_structure, file_count = create_simplified_structure(
                    code_structure,
                    self.repo_manager.repo_path,
                    self.logger,
                    filter_comments=True,
                )
                prompt = create_chunking_prompt(file_structure, simplified_structure)
                token_count = self.count_tokens(prompt)
                self.logger.info(
                    "New token count after filtering comments (with directory structure): %s",
                    token_count,
                )

                # If still over Claude's limit, we need to handle this case
                if token_count > 200000:  # Claude's limit
                    self.logger.error(
                        "Token count still exceeds Claude's limit of 200k tokens even after filtering comments. "
                        "Consider reducing the number of files or implementing pagination."
                    )
                    error_msg = "Token count exceeds Claude's limit even after filtering comments"
                    raise RuntimeError(error_msg)

            # Chunk the codebase using the already processed structure and file structure
            self.logger.info("Chunking codebase with Claude AI")
            chunks = self.chunk_manager.chunk_codebase(
                simplified_structure,
                self.repo_manager.repo_path,
                file_structure,  # Pass the pre-generated file structure
                self._handle_operation,
                self._operation_with_retry,
            )
            self.logger.info("Created %s code chunks", len(chunks))

            # Create and return analysis result
            self.logger.info("Creating analysis result")
            return RepositoryAnalysis(
                repository_url=self.repo_manager.repo_path_or_url,
                file_structure=file_structure,
                languages_used=languages,
                ingested_repo_chunks=chunks,
            )

        except Exception as e:
            self.logger.error("Failed to analyze repository: %s", str(e))
            error_msg = f"Failed to analyze repository: {str(e)}"
            raise RuntimeError(error_msg) from e

    def _process_file(self, file_path: str, ext: str) -> tuple[dict[str, Any], int]:
        """Process a single file and extract its structure.

        Args:
            file_path: Path to the file
            ext: File extension

        Returns:
            Tuple containing file structure and count (0 or 1)
        """
        if ext not in self.parser_manager.SUPPORTED_LANGUAGES:
            self.logger.debug("Skipping unsupported file type: %s", file_path)
            return {}, 0

        result, error = self._handle_operation(
            self.parser_manager.parse_file,
            f"Failed to parse {file_path}",
            file_path,
            ext,
        )

        if error:
            self.logger.debug("Error parsing file %s: %s", file_path, error)
            return {}, 0

        if result is None:
            self.logger.debug("No result from parsing file %s", file_path)
            return {}, 0

        if isinstance(result, tuple) and result[0] is None:
            self.logger.debug("Tuple result with None content for file %s", file_path)
            return {}, 0

        return {file_path: result[0] if isinstance(result, tuple) else result}, 1

    def parse_code_structure(self) -> dict[str, Any]:
        """Parse code files and extract structure using tree-sitter if available."""
        code_structure = {}
        file_count = 0

        if self.parser_manager.using_tree_sitter:
            self.logger.info("Using tree-sitter for code structure extraction")
        else:
            self.logger.info("Using simplified code structure extraction")

        self.logger.info("Scanning repository at: %s", self.repo_manager.repo_path)

        for root, _dirs, files in os.walk(self.repo_manager.repo_path):
            self.logger.debug("Walking directory: %s", root)

            # Skip directory if it should be ignored
            if self.repo_manager.should_skip_directory(root):
                continue

            for file in files:
                # Skip file if it should be ignored
                if self.repo_manager.should_skip_file(file):
                    continue

                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1]
                self.logger.debug("Checking file: %s (extension: %s)", file_path, ext)

                file_structure, count = self._process_file(file_path, ext)
                code_structure.update(file_structure)
                file_count += count

                if file_count > self.config.max_files_to_parse:
                    self.logger.warning(
                        "Reached maximum file limit (%s). Stopping analysis.",
                        self.config.max_files_to_parse,
                    )
                    return code_structure

        self.logger.info("Completed code analysis. Processed %s files.", file_count)
        return code_structure
