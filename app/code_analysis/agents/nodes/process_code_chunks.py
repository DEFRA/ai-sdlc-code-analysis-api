from logging import getLogger

from app.code_analysis.agents.code_chunk_analysis import code_chunk_analysis
from app.code_analysis.agents.states.code_analysis import CodeAnalysisState
from app.code_analysis.agents.states.code_chuck_analysis import CodeChunkAnalysisState

logger = getLogger(__name__)


def process_code_chunks(state: CodeAnalysisState) -> CodeAnalysisState:
    """Process code chunks sequentially using the code_chunk_analysis subgraph."""

    # If there are no chunks, return state unchanged
    if not state.ingested_repo_chunks:
        return state

    # Process each chunk sequentially
    results = []
    for chunk in state.ingested_repo_chunks:
        # Execute the subgraph with the chunk
        subgraph_output = code_chunk_analysis.invoke(
            CodeChunkAnalysisState(code_chunk=chunk)
        )

        # Extract and store the result
        results.append(subgraph_output["analyzed_code_chunk"])

    logger.info(
        "Analyzed %d out of %d chunks", len(results), len(state.ingested_repo_chunks)
    )
    # Return updated state
    return state.model_copy(update={"analyzed_code_chunks": results})
