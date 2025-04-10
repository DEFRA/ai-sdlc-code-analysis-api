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
        system_prompt = """You are a senior software developer analyzing a code repository.
Your task is to create a detailed, insightful report on the interfaces in the codebase.

Focus on:
- API design and patterns
- Interface definitions (classes, protocols, contracts)
- Component boundaries and communication
- Public vs. private interfaces
- RESTful, GraphQL, or other API styles
- Consistency and adherence to design principles
- Interface documentation and usability

Format your report with clear sections, bullet points, and examples where helpful.
Be specific, factual, and professional."""

        # Define user prompt with interfaces context
        user_prompt = f"""Based on the following code analysis information, create a comprehensive report on the interfaces in the codebase.

Repository URL: {state.repo_url}
Languages used: {", ".join(state.languages_used)}

Context:
{interfaces_context}

Provide a complete, standalone report section focusing only on interfaces, APIs, and component boundaries."""

        report = generate_report(system_prompt, user_prompt)

    # Create the formatted report section
    formatted_report = f"# Interfaces Report\n\n{report}"

    logger.info("Interfaces report generated")

    # Update the state with the new report section
    return state.model_copy(update={"report_sections": [formatted_report]})
