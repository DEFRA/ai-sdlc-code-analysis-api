from typing import Optional

from pydantic import BaseModel, Field

from app.code_analysis.models.code_analysis_chunk import CodeAnalysisChunk
from app.code_analysis.models.code_chunk import CodeChunk


class CodeChunkAnalysisState(BaseModel):
    """State for the code chunk analysis subgraph."""

    code_chunk: CodeChunk = Field(..., description="The code chunk to be analyzed")
    analyzed_code_chunk: Optional[CodeAnalysisChunk] = Field(
        None, description="Analysis results for the code chunk"
    )
