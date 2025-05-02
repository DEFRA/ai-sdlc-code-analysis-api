#!/usr/bin/env python
"""
Script to test the generate_consolidated_report node in isolation.

This script creates a sample CodeAnalysisState with test data and passes it to the
generate_consolidated_report function to test it independently of the full LangGraph.
"""

import asyncio
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
from app.code_analysis.agents.nodes.consolidated_report import (  # noqa: E402
    generate_consolidated_report,  # noqa: E402
)
from app.code_analysis.agents.states.code_analysis import (  # noqa: E402
    CodeAnalysisState,  # noqa: E402
)
from app.code_analysis.models.report_section import ReportSection  # noqa: E402

# Get logger
logger = getLogger(__name__)


def create_test_state() -> CodeAnalysisState:
    """
    Creates a test CodeAnalysisState with sample data from a JSON file.

    For the consolidated report test, we use a different JSON file that contains
    pre-populated report sections rather than code chunks.

    Returns:
        A CodeAnalysisState instance with test data

    Raises:
        KeyError: If required fields are missing from the JSON data
    """
    # Get the current script directory
    script_dir = Path(__file__).parent

    # Get the setup data file path using the utility function
    json_file_path = get_setup_data_path(script_dir, "report_sections.json")

    logger.info("Loading test data from %s", json_file_path)

    try:
        # Load JSON data using the utility function
        state_data = load_json_data(json_file_path)

        # Create report sections from the loaded data
        report_sections = ReportSection(**state_data.get("report_sections", {}))

        # Create the state object
        state = CodeAnalysisState(
            repo_url=state_data["repo_url"],
            file_structure=state_data["file_structure"],
            languages_used=state_data["languages_used"],
            ingested_repo_chunks=[],  # Not needed for this test
            analyzed_code_chunks=[],  # Not needed for this test since we're using pre-populated report sections
            report_sections=report_sections,
        )

        logger.info("Successfully loaded test state for consolidated report generation")
        return state

    except KeyError as e:
        logger.error("Missing required field in test data: %s", e)
        raise


async def main() -> None:
    """Main function to run the test."""
    logger.info("Starting generate_consolidated_report node test")

    # Load environment variables from files
    set_env_vars_from_files()

    # Check environment variables
    if not await check_env_vars():
        return

    logger.info("Creating test state...")
    state = create_test_state()

    logger.info("Calling generate_consolidated_report node...")
    try:
        # The function returns a CodeAnalysisState, but we need to await it since it's async
        result = await generate_consolidated_report(state)

        logger.info("Node execution completed successfully")

        # Print the consolidated report
        print("\n=== Consolidated Report ===\n")
        print(result.consolidated_report)

        # Save the report to a file using the utility function
        script_dir = Path(__file__).parent
        save_output(
            {"consolidated_report": result.consolidated_report},
            script_dir,
            "consolidated_report_result.json",
        )

    except Exception as e:
        logger.exception("Error running the node: %s", e)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
