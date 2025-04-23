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
        system_prompt = """You are a senior software developer analyzing a code repository. Your task is to create a detailed report on the data model aspects of the codebase. Format your report in markdown format with clear sections"""

        # Define user prompt with data model context
        user_prompt = f"""Based on the following code analysis information, create a comprehensive report on the data model aspects of the codebase.
        The Context contains code from multiple code chunks, and you should combine them into a single report. Ensure there is no duplicate or redundant code in the final report.

Repository URL: {state.repo_url}
Languages used: {", ".join(state.languages_used)}

Context:
{data_model_context}

Your report should include the following sections:
   - Logical data models and entities
   - Mermaid ERD diagram as a string (wrapped in triple backticks with "mermaid" tag)
   - Detailed breakdown of each model's fields, types, and relationships
   - Data flow and transformations
   - Data validation and integrity checks

Ensure there are no duplicates or redundancy in the final report.
"""

        report = generate_report(system_prompt, user_prompt)

    # Create the formatted report section
    formatted_report = f"# Data Model Report\n\n{report}"

    logger.info("Data model report generated")

    # Add debugging information
    logger.debug(
        "Report sections before update: %s", state.report_sections.model_dump()
    )

    # Update the state with the new report section
    updated_report_sections = state.report_sections.model_copy(
        update={"data_model": formatted_report}
    )

    # More debugging
    logger.debug(
        "Report sections after update: %s", updated_report_sections.model_dump()
    )

    return state.model_copy(update={"report_sections": updated_report_sections})
