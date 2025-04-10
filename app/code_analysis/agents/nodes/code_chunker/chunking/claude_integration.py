"""Claude API integration for code chunking."""

import json
import logging
import time
from typing import Any, Callable

# System prompt used for all Claude API calls
CLAUDE_SYSTEM_PROMPT = "You are a meticulous code organization expert who ensures complete coverage when analyzing codebases. Your specialty is identifying logical structures in code repositories and ensuring no files are overlooked. Always verify completeness before providing your analysis and return only valid JSON in your responses, with no additional text."


def create_chunking_prompt(
    directory_structure: str, simplified_structure: dict[str, Any]
) -> str:
    """Create a prompt for Claude to chunk the codebase.

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
```
"""


def get_chunks_from_claude(
    prompt: str,
    anthropic_client: Any,
    timeout: int,
    logger: logging.Logger,
    operation_with_retry: Callable,
) -> list[dict[str, Any]]:
    """Send request to Claude API and get chunks data.

    Args:
        prompt: The prompt to send to Claude
        anthropic_client: Anthropic client instance
        timeout: Timeout in seconds for the API call
        logger: Logger instance for logging
        operation_with_retry: Function to handle retrying operations

    Returns:
        List of chunk data dictionaries

    Raises:
        RuntimeError: If API call fails or response processing fails
    """
    logger.info("Sending request to Anthropic API for chunking analysis...")

    # Validate that Anthropic client is properly initialized
    if anthropic_client is None:
        error_msg = "Anthropic client is not initialized. Check API key configuration."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Define the API call function for retry
    def make_api_call():
        try:
            logger.debug("Calling Anthropic API with model: claude-3-5-sonnet-latest")
            return anthropic_client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=8192,
                temperature=0,
                timeout=timeout,
                system=CLAUDE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
        except AttributeError as e:
            logger.error("Anthropic client attribute error: %s", str(e))
            logger.error("Client type: %s", type(anthropic_client))
            logger.error("Client attributes: %s", dir(anthropic_client))
            raise
        except Exception as e:
            logger.error("Unexpected error during API call: %s", str(e))
            raise

    # Make the API call with retry
    start_time = time.time()
    response = operation_with_retry(
        make_api_call, "Anthropic API call failed, retrying", logger, 3
    )
    elapsed_time = time.time() - start_time
    logger.info("Received response from Anthropic API in %.2f seconds", elapsed_time)

    # Process the response
    logger.info("Starting to parse Claude response...")

    # Extract and process the response content
    content = response.content
    logger.debug("Raw response content type: %s", type(content))

    # Extract the text content
    text_content = extract_text_from_response(content, logger)

    # Parse JSON and extract chunks
    return parse_chunks_from_response(text_content, logger)


def extract_text_from_response(content: Any, logger: logging.Logger) -> str:
    """Extract text content from Claude API response.

    Args:
        content: Response content from Claude API
        logger: Logger instance for logging

    Returns:
        Text content as string

    Raises:
        ValueError: If content format is unexpected
    """
    # Handle list-type content
    if isinstance(content, list):
        logger.debug("Response content is a list, taking first element")
        if not content:
            error_msg = "Empty response list from Claude"
            raise ValueError(error_msg)
        content = content[0]

    # Extract text based on content type
    if hasattr(content, "text"):
        logger.debug("Found text attribute in response")
        return content.text
    if isinstance(content, (dict, list)):
        logger.debug("Response is already parsed JSON")
        return json.dumps(content)
    if isinstance(content, str):
        logger.debug("Response is raw text")
        return content
    error_msg = f"Unexpected response type: {type(content)}"
    raise ValueError(error_msg)


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
