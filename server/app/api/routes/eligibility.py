"""Eligibility Evaluator API 라우터

Step 2: 대상성 판단 엔드포인트
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.eligibility_evaluator.graph import run_eligibility_evaluation
from app.agents.eligibility_evaluator.schemas import (
    EligibilityRequest,
    EligibilityResponse,
)
from app.api.deps import get_auth_user
from app.core.config import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


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
    project_result = (
        supabase.table("projects")
        .select("id, canonical, user_id")
        .eq("id", project_id)
        .maybe_single()
        .execute()
    )

    # maybe_single(): 결과 없으면 data=None, 결과 있으면 data=dict
    project = project_result.data if project_result else None
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
        print(f"[Eligibility] 대상성 판단 시작 - project_id: {project_id}")
        result = await run_eligibility_evaluation(
            project_id=project_id,
            canonical=canonical,
        )
        print(f"[Eligibility] 대상성 판단 완료 - label: {result.eligibility_label.value}\n ---------------------------")
    except Exception as e:
        logger.error(f"[Eligibility] 대상성 판단 실행 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"대상성 판단 중 오류가 발생했습니다: {str(e)}",
        )

    # 5. 결과를 DB에 저장 (upsert: project_id UNIQUE 제약조건)
    try:
        eligibility_data = {
            "project_id": project_id,
            "eligibility_label": result.eligibility_label.value,
            "final_eligibility_label": None,  # 재분석 시 사용자 선택 초기화
            "confidence_score": result.confidence_score,
            "result_summary": result.result_summary,
            "direct_launch_risks": [r.model_dump() for r in result.direct_launch_risks],
            "evidence_data": result.evidence_data.model_dump(),
            "model_name": result.model_name,
        }

        # upsert: project_id가 있으면 UPDATE, 없으면 INSERT
        supabase.table("eligibility_results").upsert(
            eligibility_data,
            on_conflict="project_id"
        ).execute()

        # projects.current_step 업데이트 (Step 2 완료 → Step 3으로 이동)
        supabase.table("projects").update({"current_step": 3}).eq(
            "id", project_id
        ).execute()

    except Exception as e:
        logger.error(f"결과 저장 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"결과 저장 중 오류가 발생했습니다: {str(e)}",
        )

    return result
