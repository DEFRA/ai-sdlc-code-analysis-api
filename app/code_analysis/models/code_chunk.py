"""
Models for code chunk functionality.
"""

from pydantic import BaseModel, Field


class CodeChunk(BaseModel):
    """A chunk of code from the repository."""

    chunk_id: str = Field(..., description="The unique identifier")
    description: str = Field(..., description="A description of the chunk")
    files: list[str] = Field(..., description="The files within the chunk")
    content: str = Field(..., description="The code and content within the chunk")
