import logging
from dataclasses import dataclass
from typing import Optional


@dataclass
class AnalyzerConfig:
    """Configuration for code analyzer.

    Args:
        repo_path_or_url: Local path or URL to the repository
        aws_bedrock_model: AWS Bedrock model ID
        aws_region: AWS region for Bedrock
        log_prompts: Whether to log prompts sent to LLM
        log_file_path: Path to the log file
        log_responses: Whether to log responses from LLM
        api_timeout: Timeout in seconds for API calls
        log_level: Logging level to use
        max_files_to_parse: Maximum number of files to parse
        filter_comments_above_tokens: Token threshold above which to filter out comments
        use_tree_sitter: Whether to use tree-sitter for code parsing
    """

    # Repository settings
    repo_path_or_url: str

    # API settings
    aws_bedrock_model: Optional[str] = None
    aws_region: Optional[str] = None
    api_timeout: int = 120

    # Logging settings
    log_prompts: bool = False
    log_responses: bool = False
    log_file_path: Optional[str] = None
    log_level: int = logging.INFO

    # Analysis settings
    max_files_to_parse: int = 10000
    filter_comments_above_tokens: int = 200000
    use_tree_sitter: bool = True

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.repo_path_or_url:
            error_msg = "Repository path or URL must be provided"
            raise ValueError(error_msg)

        # Set default log file path if logging is enabled but no path is provided
        if (self.log_prompts or self.log_responses) and not self.log_file_path:
            self.log_file_path = "bedrock_prompts.log"
