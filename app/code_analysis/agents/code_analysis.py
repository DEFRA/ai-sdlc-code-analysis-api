"""
LangGraph agent implementation for code analysis.
"""

from logging import getLogger

from langgraph.checkpoint.mongodb import AsyncMongoDBSaver
from langgraph.graph import END, START, StateGraph

from app.code_analysis.agents.nodes.code_analysis import initialize_state
from app.code_analysis.agents.states.code_analysis import CodeAnalysisState
from app.common.mongo import get_db
from app.config import config

logger = getLogger(__name__)


def create_code_analysis_graph() -> StateGraph:
    """
    Creates and returns the StateGraph for code analysis.
    This function is useful for visualization and testing purposes.

    Returns:
        The StateGraph for code analysis
    """
    # Create the state graph
    workflow = StateGraph(CodeAnalysisState)

    # Add nodes to the graph
    workflow.add_node("initialize", initialize_state)

    # Set the entry point
    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", END)

    return workflow


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

    # Get the state graph
    workflow = create_code_analysis_graph()

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
