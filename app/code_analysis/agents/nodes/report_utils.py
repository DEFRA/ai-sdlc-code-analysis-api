"""
Utility functions for report generation nodes.
"""

import os
from logging import getLogger

import boto3
from botocore.config import Config
from langchain_aws import ChatBedrock

logger = getLogger(__name__)


def generate_report(system_prompt: str, user_prompt: str) -> str:
    """
    Generates a report section using Anthropic's model with custom prompts.

    Args:
        system_prompt: The system prompt to use for the report generation
        user_prompt: The user prompt to use for the report generation

    Returns:
        A string containing the generated report section
    """
    logger.info("Generating report using custom prompts")

    # Get environment variables
    model_id = os.environ.get("AWS_BEDROCK_MODEL")
    region = os.environ.get("AWS_REGION")

    # Configure boto3 with extended timeouts
    boto_config = Config(
        connect_timeout=60,  # Connection timeout in seconds
        read_timeout=600,  # Read timeout in seconds (10 minutes)
        retries={"max_attempts": 3},
    )

    # Create the boto3 bedrock-runtime client with extended timeout configuration
    bedrock_client = boto3.client(
        "bedrock-runtime", region_name=region, config=boto_config
    )

    # Initialize the Claude model using Bedrock with custom client
    model = ChatBedrock(
        model_id=model_id,
        client=bedrock_client,
        model_kwargs={"temperature": 0, "max_tokens": 8192},
    )

    # Generate the report section
    response = model.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    # Extract and return the content
    return response.content
