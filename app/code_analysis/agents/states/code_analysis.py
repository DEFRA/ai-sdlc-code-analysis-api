"""
State definitions for code analysis agents.
"""

from typing import Annotated

from pydantic import BaseModel, Field

from app.code_analysis.models.code_analysis import CodeChunk
from app.code_analysis.models.code_analysis_chunk import CodeAnalysisChunk
from app.code_analysis.models.report_section import ReportSection


def unique_code_chunks_reducer(
    existing: list[CodeAnalysisChunk], new: list[CodeAnalysisChunk]
) -> list[CodeAnalysisChunk]:
    """
    Custom reducer for analyzed_code_chunks that prevents duplicates.
    Uses a combination of business_logic and data_model as a rough fingerprint to identify duplicates.
    """
    # Create a set of "fingerprints" for existing chunks to detect duplicates
    existing_fingerprints = {
        (chunk.business_logic, chunk.data_model) for chunk in existing
    }

    # Only add chunks that don't match existing fingerprints
    unique_new = [
        chunk
        for chunk in new
        if (chunk.business_logic, chunk.data_model) not in existing_fingerprints
    ]

    return existing + unique_new


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
    analyzed_code_chunks: Annotated[
        list[CodeAnalysisChunk], unique_code_chunks_reducer
    ] = Field([], description="The analyzed code chunks")
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
