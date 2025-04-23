"""
Node for generating consolidated reports.
"""

import re
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
    # Debug the report sections model
    logger.debug("Report sections object: %s", state.report_sections)
    logger.debug("Report sections fields: %s", state.report_sections.model_dump())

    # Store transformed report sections
    transformed_parts = []
    section_index = 0

    # Get all fields from the report_sections object that are not None
    for field_name, field_value in state.report_sections.model_dump().items():
        logger.debug(
            "Processing field %s with value: %s",
            field_name,
            "Non-empty" if field_value else "Empty",
        )

        if field_value is not None:
            # Transform each report section for the consolidated report
            section_index += 1
            transformed_section = transform_report_section(field_value, section_index)
            transformed_parts.append(transformed_section)

    logger.debug("Processed %d non-empty report parts", len(transformed_parts))

    # Combine all transformed report sections into a single document
    consolidated_report = "\n\n".join(transformed_parts)

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


def transform_report_section(section_content: str, section_number: int) -> str:
    """
    Transform a report section by adding proper heading numbering and hierarchy.

    Only applies numbering to H1 and H2 headings:
    - H1 becomes "## N. Heading" (second level with section number)
    - H2 becomes "### N.M. Heading" (third level with section and subsection number)
    - H3+ becomes "####+ Heading" (increased depth, no numbering)

    Args:
        section_content: The original markdown content of the section
        section_number: The number to assign to this section

    Returns:
        Transformed markdown with properly numbered and leveled headings
    """
    # Process the section line by line
    lines = section_content.split("\n")
    transformed_lines = []
    subheading_count = 0

    for line in lines:
        # Check if the line is a heading
        heading_match = re.match(r"^(#+)\s+(.*)", line)
        if heading_match:
            # Extract heading level (number of #) and content
            hashes, heading_text = heading_match.groups()
            heading_level = len(hashes)

            if heading_level == 1:  # Main section heading (H1)
                # Make it an H2 with section number
                transformed_lines.append(f"## {section_number}. {heading_text}")
                # Reset subheading count when we hit a main heading
                subheading_count = 0
            elif heading_level == 2:  # Subheading (H2)
                subheading_count += 1
                # Make it an H3 with section.subsection number
                transformed_lines.append(
                    f"### {section_number}.{subheading_count}. {heading_text}"
                )
            else:
                # For deeper levels, just increase the heading level by one without adding numbers
                new_level = heading_level + 1
                transformed_lines.append(f"{'#' * new_level} {heading_text}")
        else:
            # Not a heading, keep the line as is
            transformed_lines.append(line)

    return "\n".join(transformed_lines)
