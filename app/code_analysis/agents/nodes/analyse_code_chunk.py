from logging import getLogger

from app.code_analysis.agents.states.code_chuck_analysis import CodeChunkAnalysisState
from app.code_analysis.models.code_analysis_chunk import CodeAnalysisChunk

logger = getLogger(__name__)


def analyse_code_chunk(state: CodeChunkAnalysisState) -> CodeChunkAnalysisState:
    """A mock node that analyses a given code chunk."""

    analyzed_code_chunk = CodeAnalysisChunk(
        summary=f"This is a summary of - {state.code_chunk.chunk_id}",
        data_model=f"This is the data model for - {state.code_chunk.chunk_id}",
        interfaces=f"This is the interfaces for - {state.code_chunk.chunk_id}",
        business_logic=f"This is the business logic for - {state.code_chunk.chunk_id}",
        dependencies=f"This is the dependencies for - {state.code_chunk.chunk_id}",
        configuration=f"This is the configuration for - {state.code_chunk.chunk_id}",
        infrastructure=f"This is the infrastructure for - {state.code_chunk.chunk_id}",
        non_functional=f"This is the non-functional for - {state.code_chunk.chunk_id}",
    )

    logger.info("Analyzed code chunk %s", state.code_chunk.chunk_id)

    return {
        "analyzed_code_chunk": analyzed_code_chunk,
    }
