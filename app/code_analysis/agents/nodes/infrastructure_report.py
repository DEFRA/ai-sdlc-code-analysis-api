"""
Node for generating infrastructure reports.
"""

from logging import getLogger

from app.code_analysis.agents.nodes.report_utils import generate_report
from app.code_analysis.agents.states.code_analysis import CodeAnalysisState

logger = getLogger(__name__)


async def generate_infrastructure_report(state: CodeAnalysisState) -> CodeAnalysisState:
    """
    Generates a report on the infrastructure in the codebase.

    Args:
        state: The current state of the code analysis

    Returns:
        Updated state with the infrastructure report section added
    """
    # Extract infrastructure information from analyzed chunks
    infrastructure_context = "\n\n".join(
        [
            f"Chunk {chunk.chunk_id}:\n{chunk.infrastructure}"
            for chunk in state.analyzed_code_chunks
            if chunk.infrastructure
        ]
    )

    if not infrastructure_context.strip():
        report = "No infrastructure information found in the analyzed code chunks."
    else:
        # Define system prompt for infrastructure analysis
        system_prompt = """You are a senior software developer analyzing a code repository. Your task is to create a detailed report on the infrastructure aspects of the codebase. Format your report in markdown format with clear sections"""

        # Define user prompt with data model context
        user_prompt = f"""Based on the following code analysis information, create a comprehensive report on the infrastructure aspects of the codebase.
The <context> block contains code from multiple code chunks, and you should generate a single report as defined below.

<context>
Repository URL: {state.repo_url}
Languages used: {", ".join(state.languages_used)}

Code chunks:
{infrastructure_context}
</context>

Your report should be titled "Infrastructure Report" and should include the following sections:
- Deployment configuration and infrastructure as code (IaC)
- Deployment and environment setup
- Cloud services integration
- Containerization and orchestration
- CI/CD pipeline setup

Ensure there are no duplicates or redundancy in the single report."""

    report = generate_report(system_prompt, user_prompt)

    logger.info("Infrastructure report generated")

    # Update the state with the new report section
    updated_report_sections = state.report_sections.model_copy(
        update={"infrastructure": report}
    )
    return state.model_copy(update={"report_sections": updated_report_sections})
