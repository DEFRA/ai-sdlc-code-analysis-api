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
    # Collect all report sections that have content
    report_parts = []

    # Debug the report sections model
    logger.debug("Report sections object: %s", state.report_sections)
    logger.debug("Report sections fields: %s", state.report_sections.model_dump())

    # Get all fields from the report_sections object that are not None
    for field_name, field_value in state.report_sections.model_dump().items():
        logger.debug(
            "Processing field %s with value: %s",
            field_name,
            "Non-empty" if field_value else "Empty",
        )
        if field_value is not None:
            report_parts.append(field_value)

    logger.debug("Collected %d non-empty report parts", len(report_parts))

    # Combine all report sections into a single document
    consolidated_report = "\n\n".join(report_parts)

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
