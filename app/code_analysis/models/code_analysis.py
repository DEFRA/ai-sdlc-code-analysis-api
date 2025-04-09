"""
Models for code analysis functionality.
"""

from pydantic import BaseModel, Field, HttpUrl


class CodeChunk(BaseModel):
    """A chunk of code from the repository."""

    chunk_id: str = Field(..., description="The unique identifier")
    description: str = Field(..., description="A description of the chunk")
    files: list[str] = Field(..., description="The files within the chunk")
    content: str = Field(..., description="The code and content within the chunk")


class CodeAnalysis(BaseModel):
    """Code analysis data model for API responses."""

    repo_url: str = Field(..., description="The URL of the repository to analyze")
    file_structure: str = Field(..., description="The file structure of the repository")
    languages_used: list[str] = Field(
        ..., description="The languages used in the repository"
    )
    ingested_repo_chunks: list[CodeChunk] = Field(
        ..., description="The chunks of code ingested from the repository"
    )


class CodeAnalysisRequest(BaseModel):
    """Request model for triggering code analysis."""

    repo_url: HttpUrl = Field(..., description="The URL of the repository to analyze")


class CodeAnalysisResponse(BaseModel):
    """Response model for code analysis trigger."""

    thread_id: str = Field(
        ..., description="The unique identifier for the analysis thread"
    )
