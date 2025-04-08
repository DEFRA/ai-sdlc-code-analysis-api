"""
LangGraph agent implementation for code analysis.
"""

import asyncio
from logging import getLogger

from langgraph.checkpoint.mongodb import AsyncMongoDBSaver
from langgraph.graph import END, START, StateGraph

from app.code_analysis.agents.nodes.code_chunker_node import code_chunker
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
    workflow.add_node("code_chunker", code_chunker)

    # Set the entry point
    workflow.add_edge(START, "code_chunker")
    workflow.add_edge("code_chunker", END)

    return workflow


async def create_code_analysis_agent(thread_id: str, repo_url: str) -> None:
    """
    Creates and runs a LangGraph agent for code analysis with MongoDB checkpointing.
    Designed to be run as a background task without blocking.

    Args:
        thread_id: The unique identifier for this analysis thread
        repo_url: The URL of the repository to analyze
    """
    try:
        logger.info("Creating code analysis agent for thread %s", thread_id)

        # Initialize state with default values for all required fields to ensure proper checkpointing
        initial_state = CodeAnalysisState(
            repo_url=repo_url,
            file_structure="",  # Empty initially, will be populated by code_chunker
            languages_used=[],  # Empty initially, will be populated by code_chunker
            ingested_repo_chunks=[],  # Empty initially, will be populated by code_chunker
        )

        logger.info("Initial state created: %s", initial_state.model_dump())

        # Get the state graph
        workflow = create_code_analysis_graph()

        # Initialize database connection - this should be non-blocking
        db = await get_db()

        # Create a checkpointer for MongoDB using the async-specific version
        checkpointer = AsyncMongoDBSaver(
            db.client,
            db_name=config.mongo_database,
            checkpoint_collection_name="code_analysis_checkpoints",
        )

        logger.info(
            "MongoDB checkpointer created for database: %s", config.mongo_database
        )

        # Compile the graph with checkpointing
        graph = workflow.compile(checkpointer=checkpointer)

        # Configure the graph with thread_id
        graph_config = {"configurable": {"thread_id": thread_id}}

        # Set a timeout to prevent indefinite blocking
        try:
            # Use wait_for to apply a timeout to the graph execution
            logger.info(
                "Running code analysis agent for thread %s with timeout", thread_id
            )
            final_state = await asyncio.wait_for(
                graph.ainvoke(initial_state, graph_config),
                timeout=600,  # 10 minute timeout for the entire analysis
            )
            logger.info("Final state after graph execution: %s", final_state)
        except asyncio.TimeoutError:
            logger.error(
                "Code analysis timed out after 10 minutes for thread %s", thread_id
            )

        logger.info("Agent execution completed for thread %s", thread_id)
    except Exception as e:
        logger.error("Error in code analysis agent: %s", e)
        # This exception will be caught by the wrapper in trigger_code_analysis
