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
        system_prompt = """You are a senior software developer analyzing a code repository.
Your task is to create a detailed, insightful report on the dependencies of the codebase.

Focus on:
- External libraries and frameworks used
- Version management and compatibility
- Security implications of dependencies
- Dependency injection patterns
- Module/package dependencies within the codebase
- Potential dependency issues (circular dependencies, outdated versions)
- Build and package management

Format your report with clear sections, bullet points, and examples where helpful.
Be specific, factual, and professional."""

        # Define user prompt with dependencies context
        user_prompt = f"""Based on the following code analysis information, create a comprehensive report on the dependencies of the codebase.

Repository URL: {state.repo_url}
Languages used: {", ".join(state.languages_used)}

Context:
{dependencies_context}

Provide a complete, standalone report section focusing only on dependencies, libraries, and external integrations."""

        report = generate_report(system_prompt, user_prompt)

    # Create the formatted report section
    formatted_report = f"# Dependencies Report\n\n{report}"

    logger.info("Dependencies report generated")

    # Update the state with the new report section
    updated_report_sections = state.report_sections.model_copy(
        update={"dependencies": formatted_report}
    )
    return state.model_copy(update={"report_sections": updated_report_sections})
