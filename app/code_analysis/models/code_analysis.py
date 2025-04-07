"""
Models for code analysis functionality.
"""

from pydantic import BaseModel, Field, HttpUrl


class CodeAnalysisState(BaseModel):
    """State for the parent code analysis graph."""

    repo_url: str = Field(..., description="The URL of the repository to analyze")


class CodeAnalysisRequest(BaseModel):
    """Request model for triggering code analysis."""

    repo_url: HttpUrl = Field(..., description="The URL of the repository to analyze")


class CodeAnalysisResponse(BaseModel):
    """Response model for code analysis trigger."""

    thread_id: str = Field(
        ..., description="The unique identifier for the analysis thread"
    )
