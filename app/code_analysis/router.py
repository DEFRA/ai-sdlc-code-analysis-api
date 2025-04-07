from logging import getLogger

from fastapi import APIRouter, HTTPException, status

from app.code_analysis.models import (
    CodeAnalysisRequest,
    CodeAnalysisResponse,
    CodeAnalysisState,
)
from app.code_analysis.service import get_code_analysis_state, trigger_code_analysis

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


@router.get("/{thread_id}", response_model=CodeAnalysisState)
async def get_code_analysis(thread_id: str) -> CodeAnalysisState:
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
