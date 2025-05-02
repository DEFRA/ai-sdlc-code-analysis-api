"""Bedrock API integration for code chunking."""

import json
import logging
import os
import re
import time
from typing import Any, Callable

import boto3
import tiktoken
from botocore.config import Config
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
        logger: Logger instance for logging
        operation_with_retry: Function to handle retrying operations

    Returns:
        List of chunk data dictionaries

    Raises:
        RuntimeError: If API call fails or response processing fails
    """
    logger.info("Sending request to AWS Bedrock for chunking analysis...")

    # Get model ID and region from config or environment variables
    # model_id = config.aws_bedrock_model or os.environ.get("AWS_BEDROCK_MODEL")
    model_id = "arn:aws:bedrock:eu-central-1:314146300665:inference-profile/eu.anthropic.claude-3-7-sonnet-20250219-v1:0"
    region_name = "eu-central-1"
    provider = "anthropic"
    logger.info("model_id: %s", model_id)
    logger.info("region_name: %s", region_name)
    logger.info("provider: %s", provider)
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

            # Configure boto3 with extended timeouts
            boto_config = Config(
                connect_timeout=60,  # Connection timeout in seconds
                read_timeout=300,  # Read timeout in seconds (5 minutes)
                retries={"max_attempts": 3},
            )

            # Create the boto3 bedrock-runtime client with extended timeout configuration
            bedrock_client = boto3.client(
                "bedrock-runtime", region_name=region, config=boto_config
            )

            # Initialize the ChatBedrock model with custom client
            model = ChatBedrock(
                model_id=model_id,
                region_name=region_name,
                provider=provider,
                client=bedrock_client,
                model_kwargs={"temperature": 0, "max_tokens": 64000},
            )

            # Prepare messages
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]

            # Call the model
            result = model.invoke(messages)

            # Count tokens in the input prompt
            encoding = tiktoken.encoding_for_model("gpt-4")  # Use a compatible encoder
            input_tokens = encoding.encode(prompt)
            logger.info("Input prompt token count: %d", len(input_tokens))

            # Count tokens in the response
            response_tokens = encoding.encode(result.content)
            logger.info("Response token count: %d", len(response_tokens))

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


def extract_json_from_text(text_content: str, logger: logging.Logger) -> str:
    """Extract JSON content from text that might contain markdown or other text.

    Args:
        text_content: The text content that might contain JSON
        logger: Logger instance for logging

    Returns:
        Extracted JSON string or original string if no JSON block found
    """
    logger.debug("Extracting JSON from response text")

    # Try to find JSON content inside markdown code blocks
    # Pattern for ```json ... ``` blocks
    json_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    matches = re.findall(json_block_pattern, text_content)

    if matches:
        logger.info("Found JSON code block in response")
        # Use the first match as it's likely to be the full JSON response
        extracted_json = matches[0].strip()
        logger.debug("Extracted JSON from code block")
        return extracted_json

    # If no markdown code block found, try to find JSON object directly
    # Look for text starting with { and ending with }
    json_object_pattern = r"(\{[\s\S]*\})"
    matches = re.findall(json_object_pattern, text_content)

    if matches:
        logger.info("Found JSON object pattern in response")
        # Use the first match that looks like a complete JSON object
        for potential_json in matches:
            try:
                # Validate if this is valid JSON
                json.loads(potential_json)
                logger.debug("Found valid JSON object in text")
                return potential_json
            except json.JSONDecodeError:
                # Not a valid JSON object, continue to the next match
                continue

    # If we couldn't extract JSON using patterns, return the original content
    # and let the JSON parser handle potential errors
    logger.warning("Could not extract specific JSON content, returning original text")
    return text_content


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
        # Extract JSON content from the response text
        json_content = extract_json_from_text(text_content, logger)

        # Parse JSON content
        parsed_content = json.loads(json_content)
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
