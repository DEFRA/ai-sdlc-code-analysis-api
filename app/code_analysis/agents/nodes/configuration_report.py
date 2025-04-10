"""
Node for generating configuration reports.
"""

from logging import getLogger

from app.code_analysis.agents.nodes.report_utils import generate_report
from app.code_analysis.agents.states.code_analysis import CodeAnalysisState

logger = getLogger(__name__)


async def generate_configuration_report(state: CodeAnalysisState) -> CodeAnalysisState:
    """
    Generates a report on the configuration in the codebase.

    Args:
        state: The current state of the code analysis

    Returns:
        Updated state with the configuration report section added
    """
    # Extract configuration information from analyzed chunks
    configuration_context = "\n\n".join(
        [
            f"Chunk {chunk.chunk_id}:\n{chunk.configuration}"
            for chunk in state.analyzed_code_chunks
            if chunk.configuration
        ]
    )

    if not configuration_context.strip():
        report = "No configuration information found in the analyzed code chunks."
    else:
        # Define system prompt for configuration analysis
        system_prompt = """You are a senior software developer analyzing a code repository.
Your task is to create a detailed, insightful report on the configuration aspects of the codebase.

Focus on:
- Configuration management approaches
- Environment-specific settings
- Configuration files and formats
- Secret and credential management
- Feature flags and toggles
- Dynamic vs. static configuration
- Configuration validation and error handling

Format your report with clear sections, bullet points, and examples where helpful.
Be specific, factual, and professional."""

        # Define user prompt with configuration context
        user_prompt = f"""Based on the following code analysis information, create a comprehensive report on the configuration aspects of the codebase.

Repository URL: {state.repo_url}
Languages used: {", ".join(state.languages_used)}

Context:
{configuration_context}

Provide a complete, standalone report section focusing only on configuration management and settings."""

        report = generate_report(system_prompt, user_prompt)

    # Create the formatted report section
    formatted_report = f"# Configuration Report\n\n{report}"

    logger.info("Configuration report generated")

    # Update the state with the new report section
    return state.model_copy(update={"report_sections": [formatted_report]})
