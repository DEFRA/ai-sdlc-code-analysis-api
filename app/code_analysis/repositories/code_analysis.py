"""
Repository for code analysis data access.
"""

import json
from logging import getLogger

from langgraph.checkpoint.mongodb import AsyncMongoDBSaver

from app.code_analysis.models.code_analysis import CodeAnalysis, CodeChunk
from app.code_analysis.models.code_analysis_chunk import CodeAnalysisChunk
from app.code_analysis.models.report_section import ReportSection
from app.common.mongo import get_db
from app.config import config

logger = getLogger(__name__)


def _parse_repo_chunks(ingested_chunks_data):
    """Helper to parse repository chunks from checkpoint data."""
    ingested_repo_chunks = []

    if not ingested_chunks_data:
        return ingested_repo_chunks

    for chunk_data in ingested_chunks_data:
        # If it's already a CodeChunk object, use it directly
        if isinstance(chunk_data, CodeChunk):
            ingested_repo_chunks.append(chunk_data)
        else:
            # Otherwise, treat it as a dict and create a CodeChunk from it
            try:
                if isinstance(chunk_data, dict):
                    chunk = CodeChunk(
                        chunk_id=chunk_data.get("chunk_id", ""),
                        description=chunk_data.get("description", ""),
                        files=chunk_data.get("files", []),
                        content=chunk_data.get("content", ""),
                    )
                    ingested_repo_chunks.append(chunk)
            except Exception as e:
                logger.error("Error parsing chunk data: %s - %s", chunk_data, e)

    return ingested_repo_chunks


def _parse_analyzed_chunks(analyzed_chunks_data):
    """Helper to parse analyzed code chunks from checkpoint data."""
    analyzed_code_chunks = []

    if not analyzed_chunks_data:
        return analyzed_code_chunks

    for chunk_data in analyzed_chunks_data:
        # If it's already a CodeAnalysisChunk object, use it directly
        if isinstance(chunk_data, CodeAnalysisChunk):
            analyzed_code_chunks.append(chunk_data)
        else:
            # Otherwise, treat it as a dict and create a CodeAnalysisChunk from it
            try:
                if isinstance(chunk_data, dict):
                    chunk = CodeAnalysisChunk(
                        chunk_id=chunk_data.get("chunk_id", "unknown_id"),
                        summary=chunk_data.get("summary", "No summary available"),
                        data_model=chunk_data.get("data_model"),
                        interfaces=chunk_data.get("interfaces"),
                        business_logic=chunk_data.get("business_logic"),
                        dependencies=chunk_data.get("dependencies"),
                        configuration=chunk_data.get("configuration"),
                        infrastructure=chunk_data.get("infrastructure"),
                        non_functional=chunk_data.get("non_functional"),
                    )
                    analyzed_code_chunks.append(chunk)
            except Exception as e:
                logger.error(
                    "Error parsing analyzed chunk data: %s - %s", chunk_data, e
                )

    return analyzed_code_chunks


async def get_analysis_state(thread_id: str) -> CodeAnalysis:
    """
    Retrieves the current state of a code analysis thread from the database.

    Args:
        thread_id: The unique identifier for the analysis thread

    Returns:
        The current state of the analysis as a CodeAnalysis model

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
        logger.debug("Raw checkpoint structure: %s", checkpoint)

        state_dict = checkpoint.get("channel_values", {})
        # Log the entire state_dict with formatting for better readability
        logger.debug(
            "Full channel values (pretty): %s",
            json.dumps(state_dict, indent=2, default=str),
        )

        # Extract basic fields
        repo_url = state_dict.get("repo_url")
        file_structure = state_dict.get("file_structure", "")
        languages_used = state_dict.get("languages_used", [])

        # Parse data for chunks using helper functions
        ingested_chunks_data = state_dict.get("ingested_repo_chunks", [])
        logger.debug("Ingested chunks data: %s", ingested_chunks_data)
        ingested_repo_chunks = _parse_repo_chunks(ingested_chunks_data)

        analyzed_chunks_data = state_dict.get("analyzed_code_chunks", [])
        logger.debug("Analyzed chunks data: %s", analyzed_chunks_data)
        analyzed_code_chunks = _parse_analyzed_chunks(analyzed_chunks_data)

        # Extract report sections and consolidated report
        report_sections_data = state_dict.get("report_sections", {})
        logger.debug("Raw report sections data: %s", report_sections_data)

        # Create a ReportSection instance from the data
        try:
            # Handle different types of report_sections_data
            if isinstance(report_sections_data, ReportSection):
                # If it's already a ReportSection object, use it directly
                report_sections = report_sections_data
                logger.debug(
                    "Using existing ReportSection object: %s",
                    report_sections.model_dump(),
                )
            elif isinstance(report_sections_data, dict):
                # If it's a dictionary with the expected structure
                report_sections = ReportSection(**report_sections_data)
                logger.debug(
                    "Successfully created ReportSection from dictionary: %s",
                    report_sections.model_dump(),
                )
            else:
                # Try to convert to dictionary if it's a string or another format
                try:
                    # If it's a string representation, try to convert it to a dict
                    if hasattr(report_sections_data, "__dict__"):
                        # If it has __dict__, use that to create the object
                        report_sections = ReportSection(**report_sections_data.__dict__)
                    else:
                        # Default to empty ReportSection
                        logger.warning(
                            "Unable to parse report_sections data type: %s, defaulting to empty ReportSection",
                            type(report_sections_data),
                        )
                        report_sections = ReportSection()
                except Exception as e:
                    logger.warning(
                        "Failed to convert report_sections_data to dictionary: %s",
                        e,
                    )
                    report_sections = ReportSection()
        except Exception as e:
            logger.error(
                "Error creating ReportSection from data: %s - %s",
                report_sections_data,
                e,
            )
            report_sections = ReportSection()

        consolidated_report = state_dict.get("consolidated_report", "")
        product_requirements = state_dict.get("product_requirements", "")

        # Create the API model directly
        result_state = CodeAnalysis(
            repo_url=repo_url,
            file_structure=file_structure,
            languages_used=languages_used,
            ingested_repo_chunks=ingested_repo_chunks,
            analyzed_code_chunks=analyzed_code_chunks,
            report_sections=report_sections,
            consolidated_report=consolidated_report,
            product_requirements=product_requirements,
        )

        logger.debug("Returning API model: %s", result_state.model_dump())
        return result_state

    except Exception as e:
        logger.error("Error retrieving checkpoint for thread %s: %s", thread_id, e)
        error_msg = f"Could not retrieve analysis for thread ID: {thread_id}"
        raise ValueError(error_msg) from e
