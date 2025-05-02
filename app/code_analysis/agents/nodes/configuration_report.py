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
        system_prompt = """You are a senior software developer analyzing a code repository. Your task is to create a detailed report on the configuration aspects of the codebase. Format your report in markdown format with clear sections"""

        # Define user prompt with data model context
        user_prompt = f"""Based on the following code analysis information, create a comprehensive report on the configuration aspects of the codebase.
The <context> block contains code from multiple code chunks, and you should generate a single report as defined below.

<context>
Repository URL: {state.repo_url}
Languages used: {", ".join(state.languages_used)}

Code chunks:
{configuration_context}
</context>

Your report should be titled "Configuration Report" and should include the following sections:
- Configuration files (e.g., YAML, JSON)
- Configuration variables with defaults and valid options
- Environment variables and config files
- Secrets management and sensitive data handling

Ensure there are no duplicates or redundancy in the single report."""

    report = generate_report(system_prompt, user_prompt)

    logger.info("Configuration report generated")

    # Update the state with the new report section
    updated_report_sections = state.report_sections.model_copy(
        update={"configuration": report}
    )
    return state.model_copy(update={"report_sections": updated_report_sections})
