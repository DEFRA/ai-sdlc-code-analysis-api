"""
Node for generating consolidated reports.
"""

from logging import getLogger

from app.code_analysis.agents.states.code_analysis import CodeAnalysisState

logger = getLogger(__name__)


async def generate_consolidated_report(state: CodeAnalysisState) -> CodeAnalysisState:
    """
    Generates a consolidated report from all individual report sections.

    Args:
        state: The current state of the code analysis

    Returns:
        Updated state with the consolidated report
    """
    # Combine all report sections into a single document
    consolidated_report = "\n\n".join(state.report_sections)

    # Add a header with repository information
    header = f"""# Code Analysis Report

## Repository Information
- **Repository URL:** {state.repo_url}
- **Languages Used:** {", ".join(state.languages_used)}

"""

    # Add the header to the consolidated report
    full_report = header + consolidated_report

    logger.info("Consolidated report generated")

    # Update the state with the consolidated report
    return state.model_copy(update={"consolidated_report": full_report})
