#!/usr/bin/env python
"""
Utility functions for running LangGraph nodes in isolation.

This module provides common functionality used by scripts that test individual
LangGraph nodes separately from the full graph.
"""

import json
import logging
import os
import re
import sys
from logging import getLogger
from pathlib import Path
from typing import Any

# Configure project root path
PROJECT_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = getLogger(__name__)

# Define data directories
SETUP_DATA_DIR = "data/setup"
RESULTS_DATA_DIR = "data/results"


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
    # File paths
    secrets_env_path = os.path.join(PROJECT_ROOT, "compose", "secrets.env")
    aws_env_path = os.path.join(PROJECT_ROOT, "compose", "aws.env")

    logger.info("Loading environment variables from project root: %s", PROJECT_ROOT)

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


def get_setup_data_path(script_dir: Path, filename: str) -> str:
    """
    Get the path to a setup data file.

    Args:
        script_dir: The directory of the calling script
        filename: The name of the setup data file

    Returns:
        Full path to the setup data file
    """
    return os.path.join(script_dir, SETUP_DATA_DIR, filename)


def get_results_data_path(script_dir: Path, filename: str) -> str:
    """
    Get the path to a results data file.

    Args:
        script_dir: The directory of the calling script
        filename: The name of the results data file

    Returns:
        Full path to the results data file
    """
    return os.path.join(script_dir, RESULTS_DATA_DIR, filename)


def load_json_data(file_path: str) -> dict[str, Any]:
    """
    Load JSON data from a file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Dictionary containing the parsed JSON data

    Raises:
        FileNotFoundError: If the file is not found
        json.JSONDecodeError: If the JSON file cannot be parsed
    """
    try:
        with open(file_path) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("JSON file not found: %s", file_path)
        logger.error("Please ensure the file exists before running this script.")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in file: %s", file_path)
        raise


def save_output(data: dict[str, Any], script_dir: Path, filename: str) -> None:
    """
    Save output data to a JSON file in the results data directory.

    Args:
        data: The data to save
        script_dir: The directory of the calling script
        filename: The name of the output file
    """
    # Create full path to the results directory
    output_file = get_results_data_path(script_dir, filename)

    # Create results directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Save the data to the output file
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    logger.info("Output saved to %s", output_file)
