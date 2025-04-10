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
        system_prompt = """You are a senior software developer analyzing a code repository.
Your task is to create a detailed, insightful report on the infrastructure aspects of the codebase.

Focus on:
- Deployment configuration and infrastructure as code
- Cloud services integration
- Containerization and orchestration
- CI/CD pipeline setup
- Scalability and high availability provisions
- Infrastructure monitoring and observability
- Resource management and provisioning

Format your report with clear sections, bullet points, and examples where helpful.
Be specific, factual, and professional."""

        # Define user prompt with infrastructure context
        user_prompt = f"""Based on the following code analysis information, create a comprehensive report on the infrastructure aspects of the codebase.

Repository URL: {state.repo_url}
Languages used: {", ".join(state.languages_used)}

Context:
{infrastructure_context}

Provide a complete, standalone report section focusing only on infrastructure, deployment, and DevOps aspects."""

        report = generate_report(system_prompt, user_prompt)

    # Create the formatted report section
    formatted_report = f"# Infrastructure Report\n\n{report}"

    logger.info("Infrastructure report generated")

    # Update the state with the new report section
    return state.model_copy(update={"report_sections": [formatted_report]})
