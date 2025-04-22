#!/usr/bin/env python
"""
Script to test the analyse_code_chunk node in isolation.

This script creates a sample CodeChunkAnalysisState with test data and passes it to the
analyse_code_chunk function to test it independently of the full LangGraph.
"""

import asyncio
import json
import logging
import os
import re
import sys
from logging import getLogger
from pathlib import Path

# Fix the Python path to properly find modules
project_root = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(project_root))

# Now import the required modules
from app.code_analysis.agents.nodes.analyse_code_chunk import analyse_code_chunk  # noqa: E402, I001
from app.code_analysis.agents.states.code_chuck_analysis import CodeChunkAnalysisState  # noqa: E402, I001
from app.code_analysis.models.code_chunk import CodeChunk  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = getLogger(__name__)


def load_env_file(file_path: str) -> dict[str, str]:
    """
    Load environment variables from a .env file.

    Args:
        file_path: Path to the .env file

    Returns:
        Dictionary of environment variables
    """
    env_vars = {}

    try:
        with open(file_path) as file:
            for line in file:
                # Skip comments and empty lines
                line = line.strip()
                if not line or line.startswith(("#", "//")):
                    continue

                # Parse key-value pairs
                match = re.match(r"^([A-Za-z0-9_]+)=(.*)$", line)
                if match:
                    key, value = match.groups()
                    # Remove quotes if present
                    value = value.strip("'\"")
                    env_vars[key] = value

        logger.info("Loaded environment variables from %s", file_path)
        return env_vars

    except FileNotFoundError:
        logger.warning("Environment file not found: %s", file_path)
        return {}
    except Exception as e:
        logger.error("Error loading environment file %s: %s", file_path, e)
        return {}


def set_env_vars_from_files() -> None:
    """
    Load environment variables from secrets.env and aws.env files
    and set them in the current environment.
    """
    # Get the project root directory (2 levels up from script)
    project_root = Path(__file__).parents[2].absolute()

    # File paths
    secrets_env_path = os.path.join(project_root, "compose", "secrets.env")
    aws_env_path = os.path.join(project_root, "compose", "aws.env")

    logger.info("Loading environment variables from project root: %s", project_root)

    # Load environment variables from files
    secrets_vars = load_env_file(secrets_env_path)
    aws_vars = load_env_file(aws_env_path)

    # Set environment variables
    for key, value in {**secrets_vars, **aws_vars}.items():
        os.environ[key] = value

    # Log loaded variables (without sensitive info)
    if secrets_vars or aws_vars:
        safe_keys = [
            k
            for k in {**secrets_vars, **aws_vars}
            if not any(x in k.lower() for x in ["key", "secret", "password", "token"])
        ]
        logger.info("Loaded environment variables: %s", ", ".join(safe_keys))


def create_test_state() -> CodeChunkAnalysisState:
    """
    Creates a test CodeChunkAnalysisState with sample data from a JSON file.

    Returns:
        A CodeChunkAnalysisState instance with test data

    Raises:
        FileNotFoundError: If the test data file is not found
        json.JSONDecodeError: If the JSON file cannot be parsed
        KeyError: If required fields are missing from the JSON data
    """
    # Get the current script directory and the json file path in the data subfolder
    script_dir = Path(__file__).parent
    json_file_path = os.path.join(script_dir, "data", "code_chunk.json")

    logger.info("Loading test data from %s", json_file_path)

    try:
        with open(json_file_path) as f:
            code_chunk_data = json.load(f)

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

    except FileNotFoundError:
        logger.error("Test data file not found: %s", json_file_path)
        logger.error(
            "Please ensure the test data file exists before running this script."
        )
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in test data file: %s", json_file_path)
        raise
    except KeyError as e:
        logger.error("Missing required field in test data: %s", e)
        raise


async def check_env_vars() -> bool:
    """
    Check if required environment variables are set.

    Returns:
        bool: True if all required variables are set, False otherwise
    """
    required_vars = [
        "AWS_BEDROCK_MODEL",
        "AWS_REGION",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
    ]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        logger.error(
            "Missing required environment variables: %s", ", ".join(missing_vars)
        )
        logger.error(
            "Please check that compose/secrets.env and compose/aws.env files exist and contain these variables."
        )
        return False

    return True


def main() -> None:
    """Main function to run the test."""
    # Configure logging is already done at module level

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

        # Save the full analysis to a JSON file in the same directory as the script
        script_dir = Path(__file__).parent
        output_file = os.path.join(script_dir, "data", "analyze_code_chunk_result.json")

        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(analyzed_chunk.model_dump(), f, indent=2)

        logger.info("Analysis result saved to %s", output_file)

    except Exception as e:
        logger.exception("Error running the node: %s", e)


if __name__ == "__main__":
    main()
