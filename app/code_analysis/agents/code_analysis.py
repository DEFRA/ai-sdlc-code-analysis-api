"""
LangGraph agent implementation for code analysis.
"""

import asyncio
from logging import getLogger

from langgraph.checkpoint.mongodb import AsyncMongoDBSaver
from langgraph.graph import END, START, StateGraph

from app.code_analysis.agents.nodes.business_logic_report import (
    generate_business_logic_report,
)
from app.code_analysis.agents.nodes.code_chunker_node import code_chunker
from app.code_analysis.agents.nodes.configuration_report import (
    generate_configuration_report,
)
from app.code_analysis.agents.nodes.consolidated_report import (
    generate_consolidated_report,
)
from app.code_analysis.agents.nodes.data_model_report import generate_data_model_report
from app.code_analysis.agents.nodes.dependencies_report import (
    generate_dependencies_report,
)
from app.code_analysis.agents.nodes.infrastructure_report import (
    generate_infrastructure_report,
)
from app.code_analysis.agents.nodes.interfaces_report import generate_interfaces_report
from app.code_analysis.agents.nodes.non_functional_report import (
    generate_non_functional_report,
)
from app.code_analysis.agents.nodes.process_code_chunks import process_code_chunks
from app.code_analysis.agents.nodes.product_requirements_report import (
    generate_product_requirements,
)
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

    workflow.add_node("code_chunker", code_chunker)
    workflow.add_node("process_code_chunks", process_code_chunks)
    workflow.add_node("generate_data_model_report", generate_data_model_report)
    workflow.add_node("generate_interfaces_report", generate_interfaces_report)
    workflow.add_node("generate_business_logic_report", generate_business_logic_report)
    workflow.add_node("generate_dependencies_report", generate_dependencies_report)
    workflow.add_node("generate_configuration_report", generate_configuration_report)
    workflow.add_node("generate_infrastructure_report", generate_infrastructure_report)
    workflow.add_node("generate_non_functional_report", generate_non_functional_report)
    workflow.add_node("generate_consolidated_report", generate_consolidated_report)
    workflow.add_node("generate_product_requirements", generate_product_requirements)

    workflow.add_edge(START, "code_chunker")
    workflow.add_edge("code_chunker", "process_code_chunks")
    workflow.add_edge("process_code_chunks", "generate_data_model_report")
    workflow.add_edge("generate_data_model_report", "generate_interfaces_report")
    workflow.add_edge("generate_interfaces_report", "generate_business_logic_report")
    workflow.add_edge("generate_business_logic_report", "generate_dependencies_report")
    workflow.add_edge("generate_dependencies_report", "generate_configuration_report")
    workflow.add_edge("generate_configuration_report", "generate_infrastructure_report")
    workflow.add_edge(
        "generate_infrastructure_report", "generate_non_functional_report"
    )
    workflow.add_edge("generate_non_functional_report", "generate_consolidated_report")
    workflow.add_edge("generate_consolidated_report", "generate_product_requirements")
    workflow.add_edge("generate_product_requirements", END)

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

        logger.debug("Initial state created: %s", initial_state.model_dump())
        # Instead of trying to call model_dump() on the FieldInfo object, just log that it exists
        logger.debug("Report sections structure initialized")

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
                timeout=7200,  # 2 hour timeout for the entire analysis
            )
            logger.debug("Final state after graph execution: %s", final_state)
        except asyncio.TimeoutError:
            logger.error(
                "Code analysis timed out after 2 hours for thread %s", thread_id
            )

        logger.info("Agent execution completed for thread %s", thread_id)
    except Exception as e:
        logger.error("Error in code analysis agent: %s", e)
        # This exception will be caught by the wrapper in trigger_code_analysis
