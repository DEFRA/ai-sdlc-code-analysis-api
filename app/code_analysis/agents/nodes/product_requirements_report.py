"""
Node for generating product requirements report.
"""

from logging import getLogger

from app.code_analysis.agents.nodes.report_utils import generate_report
from app.code_analysis.agents.states.code_analysis import CodeAnalysisState

logger = getLogger(__name__)


async def generate_product_requirements(state: CodeAnalysisState) -> CodeAnalysisState:
    """
    Generates detailed product requirements based on the consolidated report.

    Args:
        state: The current state of the code analysis

    Returns:
        Updated state with the product requirements added
    """
    # Check if the consolidated report is available
    if not state.consolidated_report.strip():
        logger.warning(
            "No consolidated report available for product requirements generation"
        )
        return state.model_copy(
            update={
                "product_requirements": "No consolidated report available to generate product requirements."
            }
        )

    # Define system prompt for product requirements generation
    system_prompt = """You are a senior product manager that excels at creating detailed product requirements
based on code analysis reports. Your task is to create a comprehensive product requirements document
that breaks down functionality by feature and provides detailed user stories."""

    # Define user prompt with consolidated report as context
    user_prompt = f"""ANALYSIS PHASE:

Read each of the following report, analyse them.

CONSOLIDATED REPORT:
{state.consolidated_report}

IMPLEMENTATION PHASE:

Create a detailed product requirements document that breaks down the functionality by feature.  The end result should be a list of features, with both frontend and backend user stories detailed for the given feature. You will have to interweave the relevant API endpoints with the frontend features to create a fully realized feature.  The stories should be discrete and detailed.  There may be multiple stories per feature.  The end result should be a hybrid of very good user stories, with the details found in a PRD.  Please number the features and the stories so they can be easily referred to later.

Each story format should be in the following format:
- Story title
- Designate each story as a frontend or backend API story (it should be one or the other, not both)
- Story written in As a, I want, so that story format
- Design / UX consideration (if applicable)
- Testable acceptance criteria in Given, When, Then BDD format
- Detailed Architecture Design Notes
- Include any other detail or relevant notes that would help an AI-powered coding tool understand and correctly implement the features.
- Include any information about stories that are dependencies, such as backend stories that are needed to complete a frontend story, for example.
- Include any information about related stories for context.

You should also give any overarching context in the feature description.

At the top of the document include the detail of the data model for reference, including any erd diagrams.

Do NOT include any summary, timelines, or non-functional requirements, unless they are relevant to the specific feature implementations.
Do NOT add any functionality that isn't in the above requirements, only add the functionality already defined.

Include a short 'Context' part at the top of the document that details the purpose and background information that is relevant to the project overall.
"""

    # Generate the product requirements
    logger.info("Generating product requirements")
    product_requirements = generate_report(system_prompt, user_prompt)

    # Add a header to the product requirements
    formatted_product_requirements = (
        f"# Product Requirements Document\n\n{product_requirements}"
    )

    logger.info("Product requirements generated")

    # Update the state with the product requirements
    return state.model_copy(
        update={"product_requirements": formatted_product_requirements}
    )
