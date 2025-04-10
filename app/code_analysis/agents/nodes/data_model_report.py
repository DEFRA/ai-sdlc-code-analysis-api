"""
Node for generating data model reports.
"""

from logging import getLogger

from app.code_analysis.agents.nodes.report_utils import generate_report
from app.code_analysis.agents.states.code_analysis import CodeAnalysisState

logger = getLogger(__name__)


async def generate_data_model_report(state: CodeAnalysisState) -> CodeAnalysisState:
    """
    Generates a report on the data models in the codebase.

    Args:
        state: The current state of the code analysis

    Returns:
        Updated state with the data model report section added
    """
    # Extract data model information from analyzed chunks
    data_model_context = "\n\n".join(
        [
            f"Chunk {chunk.chunk_id}:\n{chunk.data_model}"
            for chunk in state.analyzed_code_chunks
            if chunk.data_model
        ]
    )

    if not data_model_context.strip():
        report = "No data model information found in the analyzed code chunks."
    else:
        # Define system prompt for data model analysis
        system_prompt = """You are a senior software developer analyzing a code repository.
Your task is to create a detailed, insightful report on the data model aspects of the codebase.

Focus on:
- Entity relationships and data structures
- Database schema design (if applicable)
- Data validation and integrity mechanisms
- ORM or data access patterns
- Strengths and potential improvements in the data model
- Best practices implemented or missing

Format your report with clear sections, bullet points, and examples where helpful.
Be specific, factual, and professional."""

        # Define user prompt with data model context
        user_prompt = f"""Based on the following code analysis information, create a comprehensive report on the data model aspects of the codebase.

Repository URL: {state.repo_url}
Languages used: {", ".join(state.languages_used)}

Context:
{data_model_context}

Provide a complete, standalone report section focusing only on data models, entities, and data structures."""

        report = generate_report(system_prompt, user_prompt)

    # Create the formatted report section
    formatted_report = f"# Data Model Report\n\n{report}"

    logger.info("Data model report generated")

    # Update the state with the new report section
    return state.model_copy(update={"report_sections": [formatted_report]})
