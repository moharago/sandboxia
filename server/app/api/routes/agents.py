"""AI Agent API 라우터

6개 에이전트에 대한 API 엔드포인트:
1. Service Structurer - /agents/structure ✅
2. Eligibility Evaluator - /agents/eligibility ✅
3. Track Recommender - /agents/track ✅
4. Application Drafter - /agents/draft (TODO)
5. Strategy Advisor - /agents/strategy (TODO)
6. Risk Checker - /agents/risk (TODO)
"""

import logging
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.agents.track_recommender import run_track_recommender
from app.api.schemas.agents import StructureResponse
from app.services.structure_service import StructureService, StructureServiceError
from app.services.track_service import (
    get_eligibility_result,
    get_project_canonical,
    save_track_result,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


# ===============================
# Service Structurer 엔드포인트
# ===============================


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


# ===============================
# Track Recommender 엔드포인트
# ===============================


class TrackRecommendRequest(BaseModel):
    """트랙 추천 요청"""

    project_id: str


class TrackRecommendResponse(BaseModel):
    """트랙 추천 응답"""

    project_id: str
    recommended_track: str
    confidence_score: float
    result_summary: str
    track_comparison: dict


@router.post(
    "/track",
    response_model=TrackRecommendResponse,
    status_code=status.HTTP_200_OK,
    summary="트랙 추천",
    description="""
프로젝트의 서비스 정보를 분석하여 적합한 규제 샌드박스 트랙을 추천합니다.

## 입력
- project_id: 프로젝트 UUID (Step 1 완료 필수)

## 출력
- recommended_track: AI 추천 트랙 (demo/temp_permit/quick_check)
- confidence_score: 신뢰도 점수 (0-100)
- result_summary: AI 분석 요약
- track_comparison: 트랙별 비교 데이터 (JSONB)
    """,
)
async def recommend_track(request: TrackRecommendRequest) -> TrackRecommendResponse:
    """트랙 추천 API

    1. DB에서 canonical 데이터 조회
    2. Track Recommender Agent 실행
    3. 결과를 track_results 테이블에 저장
    4. 응답 반환
    """
    project_id = request.project_id

    # 1. canonical 데이터 조회
    canonical = get_project_canonical(project_id)
    if not canonical:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"프로젝트를 찾을 수 없거나 canonical 데이터가 없습니다: {project_id}",
        )

    # 2. eligibility_result 조회 (선택)
    eligibility_result = get_eligibility_result(project_id)

    # 3. Track Recommender Agent 실행
    try:
        result = await run_track_recommender(
            project_id=project_id,
            canonical=canonical,
            eligibility_result=eligibility_result,
        )
    except Exception:
        correlation_id = str(uuid.uuid4())
        logger.exception(
            "Track Recommender 실행 중 오류 [correlation_id=%s]", correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"트랙 추천 중 내부 서버 오류가 발생했습니다. (오류 ID: {correlation_id})",
        )

    # 4. 결과 저장
    try:
        save_track_result(
            project_id=project_id,
            recommended_track=result["recommended_track"],
            confidence_score=result["confidence_score"],
            result_summary=result["result_summary"],
            track_comparison=result["track_comparison"],
        )
    except Exception as e:
        logger.warning("track_results 저장 실패: %s", str(e))
        # 저장 실패해도 응답은 반환

    return TrackRecommendResponse(
        project_id=project_id,
        recommended_track=result["recommended_track"],
        confidence_score=result["confidence_score"],
        result_summary=result["result_summary"],
        track_comparison=result["track_comparison"],
    )
