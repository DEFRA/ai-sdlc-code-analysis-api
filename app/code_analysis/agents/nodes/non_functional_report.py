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
        system_prompt = """You are a senior software developer analyzing a code repository.
Your task is to create a detailed, insightful report on the non-functional aspects of the codebase.

Focus on:
- Security implementations and potential vulnerabilities
- Performance optimization techniques
- Scalability approaches
- Reliability and fault tolerance mechanisms
- Maintainability and code quality
- Testing strategies and code coverage
- Accessibility considerations
- Monitoring and observability

Format your report with clear sections, bullet points, and examples where helpful.
Be specific, factual, and professional."""

        # Define user prompt with non-functional context
        user_prompt = f"""Based on the following code analysis information, create a comprehensive report on the non-functional aspects of the codebase.

Repository URL: {state.repo_url}
Languages used: {", ".join(state.languages_used)}

Context:
{non_functional_context}

Provide a complete, standalone report section focusing only on non-functional aspects like security, performance, scalability, and maintainability."""

        report = generate_report(system_prompt, user_prompt)

    # Create the formatted report section
    formatted_report = f"# Non-Functional Report\n\n{report}"

    logger.info("Non-functional report generated")

    # Update the state with the new report section
    updated_report_sections = state.report_sections.model_copy(
        update={"non_functional": formatted_report}
    )
    return state.model_copy(update={"report_sections": updated_report_sections})
