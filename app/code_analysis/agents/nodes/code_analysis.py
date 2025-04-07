"""
Node definitions for code analysis LangGraph.
"""

from logging import getLogger

from app.code_analysis.agents.states.code_analysis import CodeAnalysisState

logger = getLogger(__name__)


async def initialize_state(state: CodeAnalysisState) -> CodeAnalysisState:
    """Initialize the code analysis state."""
    logger.info("Initializing code analysis state for repository: %s", state.repo_url)
    return state
