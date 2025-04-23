"""
Unit tests for consolidated_report.py.

These tests verify that the generate_consolidated_report function correctly
combines report sections into a consolidated report.
"""

import pytest

from app.code_analysis.agents.nodes.consolidated_report import (
    generate_consolidated_report,
)
from app.code_analysis.agents.states.code_analysis import CodeAnalysisState
from app.code_analysis.models.report_section import ReportSection


@pytest.fixture
def full_report_sections():
    """Fixture providing ReportSection with all sections populated."""
    return ReportSection(
        data_model="# Data Model Report\n\nThis is the data model report content. \n## Data Model SubHeading\n\nThis is a subheading.",
        interfaces="# Interfaces Report\n\nThis is the interfaces report content. \n## Interfaces SubHeading\n\nThis is a subheading.",
        business_logic="# Business Logic Report\n\nThis is the business logic report content. \n## Business Logic SubHeading\n\nThis is a subheading.",
        dependencies="# Dependencies Report\n\nThis is the dependencies report content. \n## Dependencies SubHeading\n\nThis is a subheading.",
        configuration="# Configuration Report\n\nThis is the configuration report content. \n## Configuration SubHeading\n\nThis is a subheading.",
        infrastructure="# Infrastructure Report\n\nThis is the infrastructure report content. \n## Infrastructure SubHeading\n\nThis is a subheading.",
        non_functional="# Non-Functional Aspects Report\n\nThis is the non-functional report content. \n## Non-Functional SubHeading\n\nThis is a subheading.",
    )


@pytest.fixture
def partial_report_sections():
    """Fixture providing ReportSection with only some sections populated."""
    return ReportSection(
        data_model="# Data Model Report\n\nThis is the data model report content. \n## Data Model SubHeading\n\nThis is a subheading.",
        interfaces=None,
        business_logic="# Business Logic Report\n\nThis is the business logic report content. \n## Business Logic SubHeading\n\nThis is a subheading.",
        dependencies=None,
        configuration=None,
        infrastructure="# Infrastructure Report\n\nThis is the infrastructure report content. \n## Infrastructure SubHeading\n\nThis is a subheading.",
        non_functional=None,
    )


@pytest.fixture
def empty_report_sections():
    """Fixture providing ReportSection with no sections populated."""
    return ReportSection()


@pytest.mark.asyncio
async def test_generate_consolidated_report_with_all_sections(full_report_sections):
    """
    Test consolidation of a state with all report sections populated.

    Given a CodeAnalysisState with all report sections populated
    When generate_consolidated_report is called
    Then it should return a state with a consolidated report containing all sections
    """
    # Given
    initial_state = CodeAnalysisState(
        repo_url="https://github.com/example/repo",
        file_structure="example file structure",
        languages_used=["Python", "JavaScript"],
        ingested_repo_chunks=[],
        analyzed_code_chunks=[],
        report_sections=full_report_sections,
    )

    # When
    result_state = await generate_consolidated_report(initial_state)

    # Then
    assert result_state.consolidated_report is not None
    assert "# Code Analysis Report" in result_state.consolidated_report
    assert (
        "- **Repository URL:** https://github.com/example/repo"
        in result_state.consolidated_report
    )
    assert (
        "- **Languages Used:** Python, JavaScript" in result_state.consolidated_report
    )

    # Verify all report sections are included
    assert "## 1. Data Model Report" in result_state.consolidated_report
    assert "### 1.1. Data Model SubHeading" in result_state.consolidated_report
    assert "## 2. Interfaces Report" in result_state.consolidated_report
    assert "### 2.1. Interfaces SubHeading" in result_state.consolidated_report
    assert "## 3. Business Logic Report" in result_state.consolidated_report
    assert "### 3.1. Business Logic SubHeading" in result_state.consolidated_report
    assert "## 4. Dependencies Report" in result_state.consolidated_report
    assert "### 4.1. Dependencies SubHeading" in result_state.consolidated_report
    assert "## 5. Configuration Report" in result_state.consolidated_report
    assert "### 5.1. Configuration SubHeading" in result_state.consolidated_report
    assert "## 6. Infrastructure Report" in result_state.consolidated_report
    assert "### 6.1. Infrastructure SubHeading" in result_state.consolidated_report
    assert "## 7. Non-Functional Aspects Report" in result_state.consolidated_report
    assert "### 7.1. Non-Functional SubHeading" in result_state.consolidated_report


@pytest.mark.asyncio
async def test_generate_consolidated_report_with_partial_sections(
    partial_report_sections,
):
    """
    Test consolidation of a state with only some report sections populated.

    Given a CodeAnalysisState with only some report sections populated
    When generate_consolidated_report is called
    Then it should return a state with a consolidated report containing only populated sections
    """
    # Given
    initial_state = CodeAnalysisState(
        repo_url="https://github.com/example/repo",
        file_structure="example file structure",
        languages_used=["Python"],
        ingested_repo_chunks=[],
        analyzed_code_chunks=[],
        report_sections=partial_report_sections,
    )

    # When
    result_state = await generate_consolidated_report(initial_state)

    # Then
    assert result_state.consolidated_report is not None
    assert "# Code Analysis Report" in result_state.consolidated_report

    # Verify populated sections are included with their transformed headings
    assert "## 1. Data Model Report" in result_state.consolidated_report
    assert "## 2. Business Logic Report" in result_state.consolidated_report
    assert "## 3. Infrastructure Report" in result_state.consolidated_report

    # Verify unpopulated sections are not included
    assert "Interfaces Report" not in result_state.consolidated_report
    assert "Dependencies Report" not in result_state.consolidated_report
    assert "Configuration Report" not in result_state.consolidated_report
    assert "Non-Functional Aspects Report" not in result_state.consolidated_report


@pytest.mark.asyncio
async def test_generate_consolidated_report_with_empty_sections(empty_report_sections):
    """
    Test consolidation of a state with no report sections populated.

    Given a CodeAnalysisState with no report sections populated
    When generate_consolidated_report is called
    Then it should return a state with a consolidated report containing only the header
    """
    # Given
    initial_state = CodeAnalysisState(
        repo_url="https://github.com/example/repo",
        file_structure="example file structure",
        languages_used=["Python", "TypeScript", "JavaScript"],
        ingested_repo_chunks=[],
        analyzed_code_chunks=[],
        report_sections=empty_report_sections,
    )

    # When
    result_state = await generate_consolidated_report(initial_state)

    # Then
    assert result_state.consolidated_report is not None
    assert "# Code Analysis Report" in result_state.consolidated_report
    assert (
        "- **Repository URL:** https://github.com/example/repo"
        in result_state.consolidated_report
    )
    assert (
        "- **Languages Used:** Python, TypeScript, JavaScript"
        in result_state.consolidated_report
    )

    # Verify the report only contains the header (no additional content)
    expected_report_lines = [
        "# Code Analysis Report",
        "",
        "## Repository Information",
        "- **Repository URL:** https://github.com/example/repo",
        "- **Languages Used:** Python, TypeScript, JavaScript",
        "",
    ]

    # Join expected lines with newlines to match actual report format
    expected_report = "\n".join(expected_report_lines)
    assert result_state.consolidated_report.strip() == expected_report.strip()


@pytest.mark.asyncio
async def test_generate_consolidated_report_preserves_other_state_fields():
    """
    Test that generate_consolidated_report preserves other fields in the state.

    Given a CodeAnalysisState with various fields populated
    When generate_consolidated_report is called
    Then it should only update the consolidated_report field and preserve all others
    """
    # Given
    report_sections = ReportSection(
        data_model="# Data Model Report\n\nSome data model content.",
    )

    initial_state = CodeAnalysisState(
        repo_url="https://github.com/example/repo",
        file_structure="detailed file structure",
        languages_used=["Python", "SQL"],
        ingested_repo_chunks=[],  # Empty for simplicity
        analyzed_code_chunks=[],  # Empty for simplicity
        report_sections=report_sections,
        consolidated_report="",  # This should be updated
        product_requirements="Pre-existing product requirements",  # This should be preserved
    )

    # When
    result_state = await generate_consolidated_report(initial_state)

    # Then
    # Check the consolidated report was updated
    assert result_state.consolidated_report is not None
    assert "# Code Analysis Report" in result_state.consolidated_report

    # Check that other fields were preserved
    assert result_state.repo_url == initial_state.repo_url
    assert result_state.file_structure == initial_state.file_structure
    assert result_state.languages_used == initial_state.languages_used
    assert result_state.ingested_repo_chunks == initial_state.ingested_repo_chunks
    assert result_state.analyzed_code_chunks == initial_state.analyzed_code_chunks
    assert result_state.product_requirements == initial_state.product_requirements
