"""AI Agent API 라우터

6개 에이전트에 대한 API 엔드포인트:
1. Service Structurer - /agents/structure
2. Eligibility Evaluator - /agents/eligibility (TODO)
3. Track Recommender - /agents/track (TODO)
4. Application Drafter - /agents/draft (TODO)
5. Strategy Advisor - /agents/strategy (TODO)
6. Risk Checker - /agents/risk (TODO)
"""

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.schemas.agents import StructureResponse
from app.services.structure_service import StructureService, StructureServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/structure", response_model=StructureResponse, summary="서비스 구조화")
async def structure_service(
    session_id: str = Form(...),
    requested_track: str = Form(..., description="트랙 (counseling/quick_check/temp_permit/demo)"),
    consultant_input: str = Form(...),
    files: list[UploadFile] = File(default=[]),
) -> StructureResponse:
    """HWP 파일과 컨설턴트 입력을 분석하여 Canonical Structure 생성"""
    try:
        return await StructureService.run(
            session_id=session_id,
            requested_track=requested_track,
            consultant_input=consultant_input,
            files=files,
        )
    except StructureServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Service Structurer 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서비스 구조화 처리 중 오류가 발생했습니다.",
        )
