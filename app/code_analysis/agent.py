from logging import getLogger

from langgraph.checkpoint.mongodb import AsyncMongoDBSaver
from langgraph.graph import StateGraph

from app.code_analysis.models import CodeAnalysisState
from app.common.mongo import get_db
from app.config import config

logger = getLogger(__name__)


async def initialize_state(state: CodeAnalysisState) -> CodeAnalysisState:
    """Initialize the code analysis state."""
    logger.info("Initializing code analysis state for repository: %s", state.repo_url)
    return state


async def create_code_analysis_agent(thread_id: str, repo_url: str) -> None:
    """
    Creates and runs a LangGraph agent for code analysis with MongoDB checkpointing.

    Args:
        thread_id: The unique identifier for this analysis thread
        repo_url: The URL of the repository to analyze
    """
    logger.info("Creating code analysis agent for thread %s", thread_id)

    # Initialize state
    initial_state = CodeAnalysisState(repo_url=repo_url)

    # Create the state graph
    workflow = StateGraph(CodeAnalysisState)

    # Add nodes to the graph
    workflow.add_node("initialize", initialize_state)

    # Set the entry point
    workflow.set_entry_point("initialize")

    # Create a checkpointer for MongoDB using the async-specific version
    db = await get_db()
    # Pass database name in the constructor
    checkpointer = AsyncMongoDBSaver(
        db.client,
        db_name=config.mongo_database,
        checkpoint_collection_name="code_analysis_checkpoints",
    )

    # Compile the graph with checkpointing
    graph = workflow.compile(checkpointer=checkpointer)

    # Run the graph asynchronously with thread_id as the configurable
    logger.info("Running code analysis agent for thread %s", thread_id)
    graph_config = {"configurable": {"thread_id": thread_id}}
    await graph.ainvoke(initial_state, graph_config)

    logger.info("Agent execution completed for thread %s", thread_id)


async def get_analysis_state(thread_id: str) -> CodeAnalysisState:
    """
    Retrieves the current state of a code analysis thread.

    Args:
        thread_id: The unique identifier for the analysis thread

    Returns:
        The current state of the analysis

    Raises:
        ValueError: If the thread ID is not found
    """
    logger.info("Retrieving state for thread %s", thread_id)

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
