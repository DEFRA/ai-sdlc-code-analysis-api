"""
Service for code analysis functionality.
"""

import asyncio
from logging import getLogger

from bson import ObjectId

from app.code_analysis.agents.code_analysis import create_code_analysis_agent
from app.code_analysis.models.code_analysis import CodeAnalysisState
from app.code_analysis.repositories.code_analysis import get_analysis_state

logger = getLogger(__name__)


async def trigger_code_analysis(repo_url: str) -> str:
    """
    Triggers a new code analysis for the given repository URL.

    Args:
        repo_url: The URL of the repository to analyze

    Returns:
        The thread ID for the analysis
    """
    # Generate a unique thread ID
    thread_id = str(ObjectId())
    logger.info(
        "Triggering code analysis for repo %s with thread ID %s", repo_url, thread_id
    )

    # Start the agent asynchronously with proper error handling
    async def run_analysis():
        try:
            await create_code_analysis_agent(thread_id, repo_url)
            logger.info("Code analysis completed for thread %s", thread_id)
        except Exception as e:
            logger.error("Error in code analysis background task: %s", e)

    # Create task with explicit name for better debugging
    task = asyncio.create_task(run_analysis(), name=f"code_analysis_{thread_id}")

    # Add task to event loop without waiting for it
    asyncio.ensure_future(task)

    return thread_id


async def get_code_analysis_state(thread_id: str) -> CodeAnalysisState:
    """
    Gets the current state of a code analysis.

    Args:
        thread_id: The unique identifier for the analysis thread

    Returns:
        The current state of the analysis

    Raises:
        ValueError: If the thread ID is not found
    """
    logger.info("Getting code analysis state for thread %s", thread_id)
    return await get_analysis_state(thread_id)
