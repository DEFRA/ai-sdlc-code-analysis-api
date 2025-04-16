"""
Node implementation for code chunking functionality.
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from logging import getLogger

from app.code_analysis.agents.nodes.code_chunker.analyzer import CodeAnalyzer
from app.code_analysis.agents.nodes.code_chunker.config.analyzer_config import (
    AnalyzerConfig,
)
from app.code_analysis.agents.states.code_analysis import CodeAnalysisState
from app.code_analysis.models.code_analysis import CodeChunk

logger = getLogger(__name__)

# Create a dedicated thread pool for CPU-intensive operations
thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="code_analyzer_")


async def code_chunker(state: CodeAnalysisState) -> CodeAnalysisState:
    """
    Analyze the repository and populate state with code chunks.
    Uses CodeAnalyzer to perform the actual analysis.

    This implementation ensures CPU-intensive operations run in a thread pool
    to avoid blocking the event loop.
    """
    logger.info("Analyzing code repository: %s", state.repo_url)

    # Get AWS Bedrock configuration from environment variables
    aws_bedrock_model = os.environ.get("AWS_BEDROCK_MODEL")
    aws_region = os.environ.get("AWS_REGION")

    if not aws_bedrock_model:
        logger.error("AWS_BEDROCK_MODEL environment variable is not set")
        state.file_structure = (
            "Error: AWS_BEDROCK_MODEL environment variable is not set"
        )
        state.languages_used = []
        state.ingested_repo_chunks = []
        return state

    if not aws_region:
        logger.error("AWS_REGION environment variable is not set")
        state.file_structure = "Error: AWS_REGION environment variable is not set"
        state.languages_used = []
        state.ingested_repo_chunks = []
        return state

    # Configure the analyzer with the repository URL and AWS Bedrock settings
    config = AnalyzerConfig(
        repo_path_or_url=state.repo_url,
        aws_bedrock_model=aws_bedrock_model,
        aws_region=aws_region,
    )

    # Create analyzer
    analyzer = CodeAnalyzer(config)

    # Run the potentially CPU-intensive repository analysis in a thread pool
    # to avoid blocking the event loop
    logger.info("Running repository analysis in thread pool")

    # Create a partial function with all necessary arguments
    analyze_func = partial(analyzer.analyze_repository)

    # Run CPU-intensive work in thread pool
    analysis_results = await asyncio.get_event_loop().run_in_executor(
        thread_pool, analyze_func
    )

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

    return state
