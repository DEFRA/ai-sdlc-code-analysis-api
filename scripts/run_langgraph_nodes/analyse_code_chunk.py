#!/usr/bin/env python
"""
Script to test the analyse_code_chunk node in isolation.

This script creates a sample CodeChunkAnalysisState with test data and passes it to the
analyse_code_chunk function to test it independently of the full LangGraph.
"""

from logging import getLogger
from pathlib import Path

# Import utility module (already adds project root to sys.path)
from utils import (
    check_env_vars,
    get_setup_data_path,
    load_json_data,
    save_output,
    set_env_vars_from_files,
)

# Now import the required modules
from app.code_analysis.agents.nodes.analyse_code_chunk import (
    analyse_code_chunk,  # noqa: E402
)
from app.code_analysis.agents.states.code_chuck_analysis import (
    CodeChunkAnalysisState,  # noqa: E402
)
from app.code_analysis.models.code_chunk import CodeChunk  # noqa: E402

# Get logger
logger = getLogger(__name__)


def create_test_state() -> CodeChunkAnalysisState:
    """
    Creates a test CodeChunkAnalysisState with sample data from a JSON file.

    Returns:
        A CodeChunkAnalysisState instance with test data

    Raises:
        KeyError: If required fields are missing from the JSON data
    """
    # Get the current script directory
    script_dir = Path(__file__).parent

    # Get the setup data file path using the utility function
    json_file_path = get_setup_data_path(script_dir, "code_chunk.json")

    logger.info("Loading test data from %s", json_file_path)

    try:
        # Load JSON data using the utility function
        code_chunk_data = load_json_data(json_file_path)

        # Create a CodeChunk object from the JSON data
        code_chunk = CodeChunk(
            chunk_id=code_chunk_data["chunk_id"],
            description=code_chunk_data["description"],
            files=code_chunk_data["files"],
            content=code_chunk_data["content"],
        )

        logger.info("Successfully loaded test data for chunk '%s'", code_chunk.chunk_id)

        # Create and return the state
        return CodeChunkAnalysisState(code_chunk=code_chunk)

    except KeyError as e:
        logger.error("Missing required field in test data: %s", e)
        raise


def main() -> None:
    """Main function to run the test."""
    logger.info("Starting analyse_code_chunk node test")

    # Load environment variables from files
    set_env_vars_from_files()

    # Check environment variables
    if not asyncio.run(check_env_vars()):
        return

    logger.info("Creating test state...")
    state = create_test_state()

    logger.info("Calling analyse_code_chunk node...")
    try:
        result = analyse_code_chunk(state)

        logger.info("Node execution completed successfully")

        # Print the analysis results in a readable format
        analyzed_chunk = result["analyzed_code_chunk"]

        print("\n=== Analysis Results for Code Chunk ===\n")
        print(f"Chunk ID: {analyzed_chunk.chunk_id}")
        print(f"Summary: {analyzed_chunk.summary}\n")

        # Print each analysis section if available
        sections = [
            ("Data Model", analyzed_chunk.data_model),
            ("Interfaces", analyzed_chunk.interfaces),
            ("Business Logic", analyzed_chunk.business_logic),
            ("Dependencies", analyzed_chunk.dependencies),
            ("Configuration", analyzed_chunk.configuration),
            ("Infrastructure", analyzed_chunk.infrastructure),
            ("Non-Functional", analyzed_chunk.non_functional),
        ]

        for section_name, content in sections:
            if content:
                print(f"--- {section_name} ---")
                print(f"{content}\n")

        # Save the full analysis to a JSON file using the utility function
        script_dir = Path(__file__).parent
        save_output(
            analyzed_chunk.model_dump(), script_dir, "analyze_code_chunk_result.json"
        )

    except Exception as e:
        logger.exception("Error running the node: %s", e)


if __name__ == "__main__":
    import asyncio

    main()
