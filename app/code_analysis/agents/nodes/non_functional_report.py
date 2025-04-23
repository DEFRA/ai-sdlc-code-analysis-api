"""
Node for generating non-functional aspects reports.
"""

from logging import getLogger

from app.code_analysis.agents.nodes.report_utils import generate_report
from app.code_analysis.agents.states.code_analysis import CodeAnalysisState

logger = getLogger(__name__)


async def generate_non_functional_report(state: CodeAnalysisState) -> CodeAnalysisState:
    """
    Generates a report on the non-functional aspects in the codebase.

    Args:
        state: The current state of the code analysis

    Returns:
        Updated state with the non-functional report section added
    """
    # Extract non-functional information from analyzed chunks
    non_functional_context = "\n\n".join(
        [
            f"Chunk {chunk.chunk_id}:\n{chunk.non_functional}"
            for chunk in state.analyzed_code_chunks
            if chunk.non_functional
        ]
    )

    if not non_functional_context.strip():
        report = "No non-functional information found in the analyzed code chunks."
    else:
        # Define system prompt for non-functional analysis
        system_prompt = """You are a senior software developer analyzing a code repository. Your task is to create a detailed report on the non-functional aspects of the codebase. Format your report in markdown format with clear sections"""

        # Define user prompt with data model context
        user_prompt = f"""Based on the following code analysis information, create a comprehensive report on the non-functional aspects of the codebase.
The <context> block contains code from multiple code chunks, and you should generate a single report as defined below.

<context>
Repository URL: {state.repo_url}
Languages used: {", ".join(state.languages_used)}

Code chunks:
{non_functional_context}
</context>

Your report should be titled "Non-Functional Aspects Report" and should include the following sections:
- Performance and reliability aspects
- Security considerations and potential vulnerabilities
- Volume and load considerations
- Significant error handling and recovery mechanisms
- Logging, monitoring, and alerting
- Compliance considerations
- Data and privacy considerations
- Testing strategies and code coverage

Ensure there are no duplicates or redundancy in the single report."""

    report = generate_report(system_prompt, user_prompt)

    logger.info("Non-functional report generated")

    # Update the state with the new report section
    updated_report_sections = state.report_sections.model_copy(
        update={"non_functional": report}
    )
    return state.model_copy(update={"report_sections": updated_report_sections})
