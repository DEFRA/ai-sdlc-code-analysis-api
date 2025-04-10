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
        system_prompt = """You are a senior software developer analyzing a code repository.
Your task is to create a detailed, insightful report on the business logic aspects of the codebase.

Focus on:
- Core business rules and domain logic
- Service layer implementations
- Business process flows
- Implementation of business requirements
- Separation of concerns between business logic and other layers
- Domain-driven design patterns (if applicable)
- Code organization around business concepts

Format your report with clear sections, bullet points, and examples where helpful.
Be specific, factual, and professional."""

        # Define user prompt with business logic context
        user_prompt = f"""Based on the following code analysis information, create a comprehensive report on the business logic aspects of the codebase.

Repository URL: {state.repo_url}
Languages used: {", ".join(state.languages_used)}

Context:
{business_logic_context}

Provide a complete, standalone report section focusing only on business logic, rules, and domain-specific implementations."""

        report = generate_report(system_prompt, user_prompt)

    # Create the formatted report section
    formatted_report = f"# Business Logic Report\n\n{report}"

    logger.info("Business logic report generated")

    # Update the state with the new report section
    return state.model_copy(update={"report_sections": [formatted_report]})
