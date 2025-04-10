"""
Utility functions for report generation nodes.
"""

import os
from logging import getLogger

from langchain_anthropic import ChatAnthropic

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

    # Initialize the Anthropic model using LangChain
    model = ChatAnthropic(
        model="claude-3-5-sonnet-latest",
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        temperature=0,
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
