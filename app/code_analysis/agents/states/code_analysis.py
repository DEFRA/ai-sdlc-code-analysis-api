"""
State definitions for code analysis agents.
"""

from pydantic import BaseModel, Field

from app.code_analysis.models.code_analysis import CodeChunk


class CodeAnalysisState(BaseModel):
    """State for the parent code analysis graph."""

    repo_url: str = Field(..., description="The URL of the repository to analyze")
    file_structure: str = Field(..., description="The file structure of the repository")
    languages_used: list[str] = Field(
        ..., description="The languages used in the repository"
    )
    ingested_repo_chunks: list[CodeChunk] = Field(
        ..., description="The chunks of code ingested from the repository"
    )
