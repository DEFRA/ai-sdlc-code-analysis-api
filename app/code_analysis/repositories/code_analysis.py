"""
Repository for code analysis data access.
"""

from logging import getLogger

from langgraph.checkpoint.mongodb import AsyncMongoDBSaver

from app.code_analysis.models.code_analysis import CodeAnalysis, CodeChunk
from app.common.mongo import get_db
from app.config import config

logger = getLogger(__name__)


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
        logger.info("Raw checkpoint structure: %s", checkpoint)

        state_dict = checkpoint.get("channel_values", {})
        logger.info("Channel values: %s", state_dict)

        # Check if we have the required state fields directly in channel_values
        repo_url = state_dict.get("repo_url")
        file_structure = state_dict.get("file_structure", "")
        languages_used = state_dict.get("languages_used", [])

        # Parse ingested_repo_chunks which might be CodeChunk objects or dictionaries
        ingested_chunks_data = state_dict.get("ingested_repo_chunks", [])
        logger.info("Ingested chunks data: %s", ingested_chunks_data)

        ingested_repo_chunks = []

        # Check if we have data to process
        if ingested_chunks_data:
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

        # Create the API model directly
        result_state = CodeAnalysis(
            repo_url=repo_url,
            file_structure=file_structure,
            languages_used=languages_used,
            ingested_repo_chunks=ingested_repo_chunks,
        )

        logger.info("Returning API model: %s", result_state.model_dump())
        return result_state

    except Exception as e:
        logger.error("Error retrieving checkpoint for thread %s: %s", thread_id, e)
        error_msg = f"Could not retrieve analysis for thread ID: {thread_id}"
        raise ValueError(error_msg) from e
