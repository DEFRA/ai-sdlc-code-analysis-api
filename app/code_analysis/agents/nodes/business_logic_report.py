"""
Node for generating business logic reports.
"""

from logging import getLogger

from app.code_analysis.agents.nodes.report_utils import generate_report
from app.code_analysis.agents.states.code_analysis import CodeAnalysisState

logger = getLogger(__name__)


async def generate_business_logic_report(state: CodeAnalysisState) -> CodeAnalysisState:
    """
    Generates a report on the business logic in the codebase.

    Args:
        state: The current state of the code analysis

    Returns:
        Updated state with the business logic report section added
    """
    # Extract business logic information from analyzed chunks
    business_logic_context = "\n\n".join(
        [
            f"Chunk {chunk.chunk_id}:\n{chunk.business_logic}"
            for chunk in state.analyzed_code_chunks
            if chunk.business_logic
        ]
    )

    if not business_logic_context.strip():
        report = "No business logic information found in the analyzed code chunks."
    else:
        # Define system prompt for business logic analysis
        system_prompt = """You are a senior software developer analyzing a code repository. Your task is to create a detailed report on the business logic aspects of the codebase. Format your report in markdown format with clear sections"""

        # Define user prompt with business logic context
        user_prompt = f"""Based on the following code analysis information, create a comprehensive report on the business logic aspects of the codebase.
The <context> block contains code from multiple code chunks, and you should generate a single report as defined below.

<context>
Repository URL: {state.repo_url}
Languages used: {", ".join(state.languages_used)}
Code chunks:
{business_logic_context}
</context>

Your report should be titled "Business Logic Report" and should include the following sections:
   - Core business rules and domain logic
   - Business process flows
   - Business rules
   - Separation of concerns between business logic and other layers
   - Domain-driven design patterns
   - Set to null if no significant business logic exists

Ensure there are no duplicates or redundancy in the single report."""

    report = generate_report(system_prompt, user_prompt)

    logger.info("Business logic report generated")

    # Update the state with the new report section
    updated_report_sections = state.report_sections.model_copy(
        update={"business_logic": report}
    )
    return state.model_copy(update={"report_sections": updated_report_sections})
