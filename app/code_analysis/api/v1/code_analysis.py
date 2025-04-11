"""
API routes for code analysis functionality.
"""

from logging import getLogger

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse

from app.code_analysis.models.code_analysis import (
    CodeAnalysis,
    CodeAnalysisRequest,
    CodeAnalysisResponse,
)
from app.code_analysis.services.code_analysis import (
    get_code_analysis_state,
    trigger_code_analysis,
)

router = APIRouter(prefix="/api/v1/code-analysis")
logger = getLogger(__name__)


@router.post(
    "", response_model=CodeAnalysisResponse, status_code=status.HTTP_202_ACCEPTED
)
async def create_code_analysis(request: CodeAnalysisRequest) -> CodeAnalysisResponse:
    """
    Triggers a new code analysis for the given repository URL.
    Returns a thread ID that can be used to check the status.
    """
    logger.info("Received code analysis request for repo %s", request.repo_url)

    try:
        thread_id = await trigger_code_analysis(str(request.repo_url))
        return CodeAnalysisResponse(thread_id=thread_id)
    except Exception as e:
        logger.error("Error triggering code analysis: %s", e)
        detail = f"Failed to trigger code analysis: {str(e)}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        ) from e


@router.get("/{thread_id}", response_model=CodeAnalysis)
async def get_code_analysis(thread_id: str) -> CodeAnalysis:
    """
    Gets the current state of a code analysis by thread ID.
    """
    logger.info("Received state request for thread %s", thread_id)

    try:
        return await get_code_analysis_state(thread_id)
    except ValueError as e:
        logger.error("Thread not found: %s", e)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error("Error getting code analysis state: %s", e)
        detail = f"Failed to get code analysis state: {str(e)}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        ) from e


@router.get("/{thread_id}/consolidated-report", response_class=HTMLResponse)
async def get_consolidated_report(thread_id: str) -> str:
    """
    Gets the consolidated report for a code analysis in a human-readable format.
    Returns an HTML page that renders the markdown report with proper styling.
    """
    logger.info("Received consolidated report request for thread %s", thread_id)

    try:
        # Get the code analysis state
        analysis = await get_code_analysis_state(thread_id)

        return analysis.consolidated_report

    except ValueError as e:
        logger.error("Thread not found: %s", e)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error("Error getting consolidated report: %s", e)
        detail = f"Failed to get consolidated report: {str(e)}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        ) from e


@router.get("/{thread_id}/product-requirements-report", response_class=HTMLResponse)
async def get_product_requirements_report(thread_id: str) -> str:
    """
    Gets the product requirements for a code analysis in a human-readable format.
    Returns the product requirements extracted from the analysis.
    """
    logger.info("Received product requirements report request for thread %s", thread_id)

    try:
        # Get the code analysis state
        analysis = await get_code_analysis_state(thread_id)

        return analysis.product_requirements

    except ValueError as e:
        logger.error("Thread not found: %s", e)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error("Error getting product requirements report: %s", e)
        detail = f"Failed to get product requirements report: {str(e)}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        ) from e
