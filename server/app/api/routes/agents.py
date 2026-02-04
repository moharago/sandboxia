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

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.agents.eligibility_evaluator.schemas import (
    EligibilityRequest,
    EligibilityResponse,
)
from app.agents.track_recommender import run_track_recommender
from app.api.deps import get_auth_user
from app.api.schemas.agents import StructureResponse
from app.services.eligibility_service import (
    EligibilityServiceError,
    get_project_for_eligibility,
    run_eligibility,
    save_eligibility_result,
    update_final_eligibility_label,
    update_project_after_eligibility,
)
from app.services.structure_service import StructureService, StructureServiceError
from app.services.track_service import (
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
# Eligibility Evaluator 엔드포인트
# ===============================


@router.post(
    "/eligibility",
    response_model=EligibilityResponse,
    status_code=status.HTTP_200_OK,
    summary="대상성 판단 (Step 2)",
    description="""
프로젝트의 서비스 정보를 분석하여 규제 샌드박스 신청 필요 여부를 판단합니다.

## 입력
- project_id: 프로젝트 UUID

## 처리
1. DB에서 projects.canonical 조회
2. Rule Screener로 규제 저촉 키워드 탐지
3. R1(규제제도), R2(승인사례), R3(법령) RAG 검색
4. 최종 판정 및 근거 생성

## 출력
- eligibility_label: 판정 결과 (required/not_required/unclear)
- confidence_score: 신뢰도 (0~1)
- result_summary: AI 분석 결과 요약
- evidence_data: 판단 근거 + 승인사례 + 법령 (Step 3,4에서 재사용)
    """,
)
async def evaluate_eligibility(
    request: EligibilityRequest,
    auth_user=Depends(get_auth_user),
) -> EligibilityResponse:
    """대상성 판단 실행

    프로젝트의 canonical 데이터를 분석하여
    규제 샌드박스 신청 필요 여부를 판단합니다.
    """
    project_id = request.project_id

    # 1. DB에서 프로젝트 조회
    project = get_project_for_eligibility(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"프로젝트를 찾을 수 없습니다: {project_id}",
        )

    # 2. 권한 확인 (본인 프로젝트인지)
    if project.get("user_id") != auth_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 프로젝트에 접근할 권한이 없습니다.",
        )

    # 3. canonical 데이터 확인
    canonical = project.get("canonical")
    if not canonical:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="프로젝트에 서비스 정보(canonical)가 없습니다. Step 1을 먼저 완료하세요.",
        )

    # 4. 에이전트 실행
    try:
        result = await run_eligibility(project_id, canonical)
    except EligibilityServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    # 5. 결과를 DB에 저장
    try:
        save_eligibility_result(project_id, result)
        update_project_after_eligibility(project_id)
    except Exception as e:
        logger.error(f"결과 저장 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"결과 저장 중 오류가 발생했습니다: {str(e)}",
        )

    return result


# ===============================
# 사용자 최종 선택 업데이트 엔드포인트
# ===============================


class FinalDecisionRequest(BaseModel):
    """최종 결정 업데이트 요청"""

    final_eligibility_label: Literal["required", "not_required"]


@router.patch(
    "/eligibility/{project_id}/final-decision",
    status_code=status.HTTP_200_OK,
    summary="최종 결정 업데이트",
    description="사용자가 AI 추천과 다른 결정을 선택한 경우 저장합니다.",
)
async def update_final_decision(
    project_id: str,
    request: FinalDecisionRequest,
    auth_user=Depends(get_auth_user),
) -> dict:
    """사용자의 최종 선택 저장"""
    # 권한 확인
    project = get_project_for_eligibility(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"프로젝트를 찾을 수 없습니다: {project_id}",
        )

    if project.get("user_id") != auth_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 프로젝트에 접근할 권한이 없습니다.",
        )

    # 최종 선택 저장
    result = update_final_eligibility_label(project_id, request.final_eligibility_label)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="대상성 판단 결과를 찾을 수 없습니다.",
        )

    return {"success": True, "final_eligibility_label": request.final_eligibility_label}


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

    # 2. Track Recommender Agent 실행
    try:
        result = await run_track_recommender(
            project_id=project_id,
            canonical=canonical,
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

    # 3. 결과 저장
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

