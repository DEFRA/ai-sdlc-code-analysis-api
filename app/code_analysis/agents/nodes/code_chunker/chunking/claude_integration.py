"""Bedrock API integration for code chunking."""

import json
import logging
import os
import time
from typing import Any, Callable

from langchain_aws import ChatBedrock

# System prompt used for all LLM API calls
SYSTEM_PROMPT = "You are a meticulous code organization expert who ensures complete coverage when analyzing codebases. Your specialty is identifying logical structures in code repositories and ensuring no files are overlooked. Always verify completeness before providing your analysis and return only valid JSON in your responses, with no additional text."


def create_chunking_prompt(
    directory_structure: str, simplified_structure: dict[str, Any]
) -> str:
    """Create a prompt for the LLM to chunk the codebase.

    Args:
        directory_structure: String representation of the directory structure
        simplified_structure: Simplified code structure

    Returns:
        Formatted prompt string
    """
    # Log the directory structure
    logging.info("Directory structure passed to chunking prompt:")
    logging.info(directory_structure)

    return f"""# Feature-Based Codebase Chunking for Requirements Analysis

Analyze the codebase and chunk it according to product features and functionality. The goal is to create logical, feature-based groups that represent complete product capabilities, regardless of the technical architecture.

## Chunking Guidelines:

1. **Feature-First Approach**: Identify distinct product features or capabilities and group ALL related files together - including models, views, controllers, tests, and configuration specific to that feature.
2. **Complete Feature Representation**: Each chunk should contain everything needed to understand that feature's requirements, including:
    - Data models and schemas
    - Business logic and services
    - User interface components
    - API endpoints and controllers
    - Feature-specific utilities
    - Tests related to the feature
    - Feature-specific assets or resources
3. **Cross-Cutting Concerns**: Create separate chunks for technical capabilities that support multiple features:
    - Authentication/Authorization
    - Core infrastructure
    - Database abstractions
    - Shared UI components
    - Common utilities
    - Configuration/Build systems
4. **Naming Clarity**: Name each chunk based on what the feature does from a user perspective (e.g., "Document_Upload_And_Processing" rather than "FileHandlers").
5. **Include configuration files**: Include configuration files in the chunks. This includes files like .env.example, .gitignore, docker-compose.yml, etc.
6. **Completeness Check**: CRITICAL - Ensure EVERY file in the codebase directory structure appears in at least one chunk. Files may appear in multiple chunks if they support multiple features.

Directory Structure:
{directory_structure}

Code Elements by File:
{json.dumps(simplified_structure, indent=2, default=str, sort_keys=True)}

**VERIFICATION PROCESS REQUIRED:**

After creating your chunks, verify that:

- Every file from the codebase directory structure is included in at least one chunk
- Each feature chunk contains all components needed to understand that feature (views, models, controllers, etc.)
- Your chunks represent user-facing capabilities, not just technical organization

Return the chunks in the following JSON format:

```json
{{
    "chunks": [
        {{
            "chunk_id": "unique_id",
            "description": "Description of the feature/functionality/purpose",
            "files": ["file_path1", "file_path2", ...]
        }}
    ]
}}
"""


def get_chunks_from_bedrock(
    prompt: str,
    config: Any,
    logger: logging.Logger,
    operation_with_retry: Callable,
) -> list[dict[str, Any]]:
    """Send request to AWS Bedrock and get chunks data.

    Args:
        prompt: The prompt to send to Bedrock
        config: Configuration with AWS Bedrock settings
        timeout: Timeout in seconds for the API call
        logger: Logger instance for logging
        operation_with_retry: Function to handle retrying operations

    Returns:
        List of chunk data dictionaries

    Raises:
        RuntimeError: If API call fails or response processing fails
    """
    logger.info("Sending request to AWS Bedrock for chunking analysis...")

    # Get model ID and region from config or environment variables
    model_id = config.aws_bedrock_model or os.environ.get("AWS_BEDROCK_MODEL")
    region = config.aws_region or os.environ.get("AWS_REGION")

    # Validate that required configuration is available
    if not model_id:
        error_msg = "AWS Bedrock model ID is not specified. Check configuration or AWS_BEDROCK_MODEL environment variable."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    if not region:
        error_msg = "AWS region is not specified. Check configuration or AWS_REGION environment variable."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Define the API call function for retry
    def make_api_call():
        try:
            logger.debug("Calling AWS Bedrock with model: %s", model_id)

            # Initialize the ChatBedrock model
            model = ChatBedrock(
                model_id=model_id,
                region_name=region,
                model_kwargs={"temperature": 0, "max_tokens": 8192},
            )

            # Prepare messages
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]

            # Call the model - note: ChatBedrock does not support with_timeout directly
            # Use standard invoke method instead
            result = model.invoke(messages)

            # Return the content of the response
            return result.content

        except Exception as e:
            logger.error("Unexpected error during Bedrock API call: %s", str(e))
            raise

    # Make the API call with retry
    start_time = time.time()
    response = operation_with_retry(
        make_api_call, "AWS Bedrock API call failed, retrying", logger, 3
    )
    elapsed_time = time.time() - start_time
    logger.info("Received response from AWS Bedrock in %.2f seconds", elapsed_time)

    # Process the response
    logger.info("Starting to parse Bedrock response...")

    # Parse JSON and extract chunks
    return parse_chunks_from_response(response, logger)


def parse_chunks_from_response(
    text_content: str, logger: logging.Logger
) -> list[dict[str, Any]]:
    """Parse chunks data from JSON response text.

    Args:
        text_content: JSON text content
        logger: Logger instance for logging

    Returns:
        List of chunk data dictionaries

    Raises:
        ValueError: If JSON parsing fails or chunks are missing
    """
    try:
        # Parse JSON content
        parsed_content = json.loads(text_content)
        logger.debug("Successfully parsed JSON structure: %s", type(parsed_content))

        # Extract chunks array
        if isinstance(parsed_content, dict):
            if "chunks" not in parsed_content:
                logger.error("No 'chunks' key in parsed content")
                logger.error("Available keys: %s", list(parsed_content.keys()))
                error_msg = "Missing 'chunks' key in response"
                raise ValueError(error_msg)
            chunks_data = parsed_content["chunks"]
        else:
            chunks_data = parsed_content

        if not isinstance(chunks_data, list):
            error_msg = f"Expected chunks_data to be a list, got {type(chunks_data)}"
            raise ValueError(error_msg)

        return chunks_data

    except json.JSONDecodeError as e:
        logger.error("JSON parsing failed: %s", e)
        logger.error("Problematic content: %s", text_content)
        error_msg = f"Failed to parse JSON response: {e}"
        raise ValueError(error_msg) from e
