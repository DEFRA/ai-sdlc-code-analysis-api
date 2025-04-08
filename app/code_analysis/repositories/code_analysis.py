"""
Repository for code analysis data access.
"""

from logging import getLogger

from langgraph.checkpoint.mongodb import AsyncMongoDBSaver

from app.code_analysis.agents.states.code_analysis import CodeAnalysisState
from app.common.mongo import get_db
from app.config import config

logger = getLogger(__name__)


async def get_analysis_state(thread_id: str) -> CodeAnalysisState:
    """
    Retrieves the current state of a code analysis thread from the database.

    Args:
        thread_id: The unique identifier for the analysis thread

    Returns:
        The current state of the analysis

    Raises:
        ValueError: If the thread ID is not found
    """
    logger.info("Retrieving state from DB for thread %s", thread_id)

    # Get MongoDB client
    db = await get_db()
    # Pass database name in the constructor
    checkpointer = AsyncMongoDBSaver(
        db.client,
        db_name=config.mongo_database,
        checkpoint_collection_name="code_analysis_checkpoints",
    )

    try:
        # Get the latest checkpoint for the thread
        graph_config = {"configurable": {"thread_id": thread_id}}
        checkpoint_tuple = await checkpointer.aget_tuple(graph_config)

        if not checkpoint_tuple:
            logger.error("No checkpoint found for thread %s", thread_id)
            error_msg = f"No analysis found for thread ID: {thread_id}"
            raise ValueError(error_msg)

        # The checkpoint contains channel values that include our state
        checkpoint = checkpoint_tuple.checkpoint
        state_dict = checkpoint.get("channel_values", {})

        # Look for repo_url in various possible locations
        repo_url = None

        # First check if repo_url is directly in the channel_values
        if "repo_url" in state_dict:
            repo_url = state_dict["repo_url"]

        # If we don't have a URL, log an error
        if not repo_url:
            logger.error(
                "Could not find repo_url in checkpoint data for thread %s", thread_id
            )
            error_msg = f"No repository URL found for thread ID: {thread_id}"
            raise ValueError(error_msg)

        # Return the state in the expected format
        return CodeAnalysisState(repo_url=repo_url)

    except Exception as e:
        logger.error("Error retrieving checkpoint for thread %s: %s", thread_id, e)
        error_msg = f"Could not retrieve analysis for thread ID: {thread_id}"
        raise ValueError(error_msg) from e
