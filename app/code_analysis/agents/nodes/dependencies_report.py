"""
Node for generating dependencies reports.
"""

from logging import getLogger

from app.code_analysis.agents.nodes.report_utils import generate_report
from app.code_analysis.agents.states.code_analysis import CodeAnalysisState

logger = getLogger(__name__)


async def generate_dependencies_report(state: CodeAnalysisState) -> CodeAnalysisState:
    """
    Generates a report on the dependencies in the codebase.

    Args:
        state: The current state of the code analysis

    Returns:
        Updated state with the dependencies report section added
    """
    # Extract dependencies information from analyzed chunks
    dependencies_context = "\n\n".join(
        [
            f"Chunk {chunk.chunk_id}:\n{chunk.dependencies}"
            for chunk in state.analyzed_code_chunks
            if chunk.dependencies
        ]
    )

    if not dependencies_context.strip():
        report = "No dependencies information found in the analyzed code chunks."
    else:
        # Define system prompt for dependencies analysis
        # Define system prompt for data model analysis
        system_prompt = """You are a senior software developer analyzing a code repository. Your task is to create a detailed report on the dependencies aspects of the codebase. Format your report in markdown format with clear sections"""

        # Define user prompt with data model context
        user_prompt = f"""Based on the following code analysis information, create a comprehensive report on the dependencies aspects of the codebase.
The <context> block contains code from multiple code chunks, and you should generate a single report as defined below.

<context>
Repository URL: {state.repo_url}
Languages used: {", ".join(state.languages_used)}

Code chunks:
{dependencies_context}
</context>

Your report should be titled "Dependencies Report" and should include the following sections:

- External dependencies (libraries, frameworks)
- API calls or external services
- Database connections and ORM usage
- Third-party integrations
- Any other external dependencies
- Versioning and compatibility considerations

Ensure there are no duplicates or redundancy in the single report."""

    report = generate_report(system_prompt, user_prompt)

    logger.info("Dependencies report generated")

    # Update the state with the new report section
    updated_report_sections = state.report_sections.model_copy(
        update={"dependencies": report}
    )
    return state.model_copy(update={"report_sections": updated_report_sections})
