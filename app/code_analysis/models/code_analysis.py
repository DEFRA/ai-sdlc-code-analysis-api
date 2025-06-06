"""
Models for code analysis functionality.
"""

from pydantic import BaseModel, Field, HttpUrl

from app.code_analysis.models.code_analysis_chunk import CodeAnalysisChunk
from app.code_analysis.models.code_chunk import CodeChunk
from app.code_analysis.models.report_section import ReportSection


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
    analyzed_code_chunks: list[CodeAnalysisChunk] = Field(
        ..., description="The chunks of code analyzed from the repository"
    )
    report_sections: ReportSection = Field(
        default_factory=ReportSection,
        description="Structured report sections with different aspects of code analysis",
    )
    consolidated_report: str = Field(
        "", description="The final report as a single string"
    )
    product_requirements: str = Field(
        "", description="Product requirements generated from the consolidated report"
    )


class CodeAnalysisRequest(BaseModel):
    """Request model for triggering code analysis."""

    repo_url: HttpUrl = Field(..., description="The URL of the repository to analyze")


class CodeAnalysisResponse(BaseModel):
    """Response model for code analysis trigger."""

    thread_id: str = Field(
        ..., description="The unique identifier for the analysis thread"
    )
