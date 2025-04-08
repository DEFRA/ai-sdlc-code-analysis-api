"""
Node implementation for code chunking functionality.
"""

import os
from logging import getLogger

from app.code_analysis.agents.nodes.code_chunker.analyzer import CodeAnalyzer
from app.code_analysis.agents.nodes.code_chunker.config.analyzer_config import (
    AnalyzerConfig,
)
from app.code_analysis.agents.states.code_analysis import CodeAnalysisState
from app.code_analysis.models.code_analysis import CodeChunk

logger = getLogger(__name__)


async def code_chunker(state: CodeAnalysisState) -> CodeAnalysisState:
    """
    Analyze the repository and populate state with code chunks.
    Uses CodeAnalyzer to perform the actual analysis.
    """
    logger.info("Analyzing code repository: %s", state.repo_url)

    # Get Anthropic API key from environment variables
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY environment variable is not set")
        state.file_structure = (
            "Error: ANTHROPIC_API_KEY environment variable is not set"
        )
        state.languages_used = []
        state.ingested_repo_chunks = []
        return state

    # Configure the analyzer with the repository URL and API key
    config = AnalyzerConfig(
        repo_path_or_url=state.repo_url,
        anthropic_api_key=anthropic_api_key,
    )

    # Create analyzer and run the analysis
    analyzer = CodeAnalyzer(config)

    try:
        # Perform the repository analysis
        analysis_results = analyzer.analyze_repository()

        # Update state with analysis results
        state.file_structure = analysis_results.file_structure
        state.languages_used = analysis_results.languages_used
        state.ingested_repo_chunks = [
            CodeChunk(
                chunk_id=chunk.chunk_id,
                description=chunk.description,
                files=chunk.files,
                content=chunk.content,
            )
            for chunk in analysis_results.ingested_repo_chunks
        ]

        # Log updated state summary
        logger.info(
            "Analysis completed: %d chunks processed, languages: %s",
            len(state.ingested_repo_chunks),
            ", ".join(state.languages_used),
        )

    except Exception as e:
        logger.error("Error during repository analysis: %s", str(e))
        # In case of error, initialize with empty data rather than failing the node
        state.file_structure = "Error analyzing repository structure"
        state.languages_used = []
        state.ingested_repo_chunks = []

    return state
