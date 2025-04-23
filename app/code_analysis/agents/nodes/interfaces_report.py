"""
Node for generating interfaces reports.
"""

from logging import getLogger

from app.code_analysis.agents.nodes.report_utils import generate_report
from app.code_analysis.agents.states.code_analysis import CodeAnalysisState

logger = getLogger(__name__)


async def generate_interfaces_report(state: CodeAnalysisState) -> CodeAnalysisState:
    """
    Generates a report on the interfaces in the codebase.

    Args:
        state: The current state of the code analysis

    Returns:
        Updated state with the interfaces report section added
    """
    # Extract interfaces information from analyzed chunks
    interfaces_context = "\n\n".join(
        [
            f"Chunk {chunk.chunk_id}:\n{chunk.interfaces}"
            for chunk in state.analyzed_code_chunks
            if chunk.interfaces
        ]
    )

    if not interfaces_context.strip():
        report = "No interfaces information found in the analyzed code chunks."
    else:
        # Define system prompt for interfaces analysis
        system_prompt = """You are a senior software developer analyzing a code repository. Your task is to create a detailed report on the interfaces exposed by a codebase. Format your report in markdown format with clear sections"""

        # Define user prompt with interfaces context
        user_prompt = f"""Based on the following code analysis information, create a comprehensive report on the interfaces exposed by the codebase.
The <context> block contains code from multiple code chunks, and you should generate a single report as defined below.

<context>
Repository URL: {state.repo_url}
Languages used: {", ".join(state.languages_used)}
Code chunks:
{interfaces_context}
</context>

Your report should be titled "Interfaces Report" and should include the following sections:
- User interfaces (UI)
- API endpoints with request/response formats
- Batch processing interfaces
- Event-driven interfaces (e.g., message queues)
- Any other interfaces exposed by the code

Ensure to only include external interfaces and exclude any internal interface details.

Ensure there are no duplicates or redundancy in the single report.
"""

    report = generate_report(system_prompt, user_prompt)

    logger.info("Interfaces report generated")

    # Update the state with the new report section
    updated_report_sections = state.report_sections.model_copy(
        update={"interfaces": report}
    )
    return state.model_copy(update={"report_sections": updated_report_sections})
