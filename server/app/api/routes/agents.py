"""AI Agent API 라우터

6개 에이전트에 대한 API 엔드포인트:
1. Service Structurer - /agents/structure ✅
2. Eligibility Evaluator - /agents/eligibility ✅
3. Track Recommender - /agents/track ✅
4. Application Drafter - /agents/draft ✅
5. Strategy Advisor - /agents/strategy (TODO)
6. Risk Checker - /agents/risk (TODO)
"""

import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.agents.eligibility_evaluator.schemas import (
    ApprovalCase,
    EligibilityRequest,
    EligibilityResponse,
    Regulation,
)
from app.agents.track_recommender import run_track_recommender
from app.api.deps import AuthUser, get_auth_user
from app.api.schemas.agents import StructureResponse
from app.services.draft_service import (
    DraftServiceError,
    run_draft,
    save_draft_result,
    update_draft_card,
)
from app.services.eligibility_service import (
    EligibilityServiceError,
    run_eligibility,
    save_eligibility_result,
    update_final_eligibility_label,
    update_project_after_eligibility,
)
from app.services.project_service import get_authorized_project
from app.services.structure_service import StructureService, StructureServiceError
from app.services.track_service import (
    get_track_result,
    save_track_result,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


# ===============================
# Service Structurer 엔드포인트
# ===============================


@router.post("/structure", response_model=StructureResponse, summary="서비스 구조화")
async def structure_service(
    session_id: str = Form(..., description="프로젝트 ID"),
    requested_track: str = Form(..., description="트랙 (counseling/quick_check/temp_permit/demo)"),
    consultant_input: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    auth_user: AuthUser = Depends(get_auth_user),
) -> StructureResponse:
    """HWP 파일과 컨설턴트 입력을 분석하여 Canonical Structure 생성"""
    # 프로젝트 조회 + 권한 확인
    get_authorized_project(session_id, auth_user)

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
    auth_user: AuthUser = Depends(get_auth_user),
) -> EligibilityResponse:
    """대상성 판단 실행

    프로젝트의 canonical 데이터를 분석하여
    규제 샌드박스 신청 필요 여부를 판단합니다.
    """
    project_id = request.project_id

    # 1. 프로젝트 조회 + 권한 확인
    project = get_authorized_project(project_id, auth_user)

    # 2. canonical 데이터 확인
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
    auth_user: AuthUser = Depends(get_auth_user),
) -> dict:
    """사용자의 최종 선택 저장"""
    # 프로젝트 조회 + 권한 확인
    get_authorized_project(project_id, auth_user)

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
    similar_cases: dict = Field(default_factory=dict)  # {track_key: [case_dict, ...]}
    domain_constraints: dict = Field(default_factory=dict)  # R3 도메인 법령 RAG 결과
    # ReferencePanel 데이터 (Eligibility Evaluator와 동일 형식)
    approval_cases: list[ApprovalCase] = Field(default_factory=list)
    regulations: list[Regulation] = Field(default_factory=list)


@router.get(
    "/track/{project_id}",
    response_model=TrackRecommendResponse | None,
    summary="트랙 추천 결과 조회 (캐시)",
    description="이미 분석된 트랙 추천 결과가 있으면 반환합니다. 없으면 null을 반환합니다.",
)
async def get_track_recommendation(
    project_id: str,
    auth_user: AuthUser = Depends(get_auth_user),
) -> TrackRecommendResponse | None:
    """캐시된 트랙 추천 결과 조회"""
    # 프로젝트 조회 + 권한 확인
    get_authorized_project(project_id, auth_user)

    result = get_track_result(project_id)

    if not result:
        return None

    return TrackRecommendResponse(
        project_id=result["project_id"],
        recommended_track=result["recommended_track"],
        confidence_score=result["confidence_score"],
        result_summary=result["result_summary"],
        track_comparison=result["track_comparison"],
        similar_cases=result.get("similar_cases", {}),
        domain_constraints=result.get("domain_constraints", {}),
        approval_cases=result.get("approval_cases", []),
        regulations=result.get("regulations", []),
    )


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
async def recommend_track(
    request: TrackRecommendRequest,
    auth_user: AuthUser = Depends(get_auth_user),
) -> TrackRecommendResponse:
    """트랙 추천 API

    1. DB에서 canonical 데이터 조회
    2. Track Recommender Agent 실행
    3. 결과를 track_results 테이블에 저장
    4. 응답 반환
    """
    project_id = request.project_id

    # 1. 프로젝트 조회 + 권한 확인
    project = get_authorized_project(project_id, auth_user)

    # 2. canonical 데이터 확인
    canonical = project.get("canonical")
    if not canonical:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="프로젝트에 서비스 정보(canonical)가 없습니다. Step 1을 먼저 완료하세요.",
        )

    # 2. Track Recommender Agent 실행
    try:
        result = await run_track_recommender(
            project_id=project_id,
            canonical=canonical,
        )
    except Exception:
        correlation_id = str(uuid.uuid4())
        logger.exception("Track Recommender 실행 중 오류 [correlation_id=%s]", correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"트랙 추천 중 내부 서버 오류가 발생했습니다. (오류 ID: {correlation_id})",
        )

    # 3. 결과 저장
    similar_cases = result.get("similar_cases", {})
    domain_constraints = result.get("domain_constraints", {})
    approval_cases = result.get("approval_cases", [])
    regulations = result.get("regulations", [])
    try:
        save_track_result(
            project_id=project_id,
            recommended_track=result["recommended_track"],
            confidence_score=result["confidence_score"],
            result_summary=result["result_summary"],
            track_comparison=result["track_comparison"],
            similar_cases=similar_cases,
            domain_constraints=domain_constraints,
            approval_cases=[c.model_dump() for c in approval_cases],
            regulations=[r.model_dump() for r in regulations],
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
        similar_cases=similar_cases,
        domain_constraints=domain_constraints,
        approval_cases=approval_cases,
        regulations=regulations,
    )


# ===============================
# Application Drafter 엔드포인트
# ===============================


class DraftGenerateRequest(BaseModel):
    """신청서 초안 생성 요청"""

    project_id: str


class DraftGenerateResponse(BaseModel):
    """신청서 초안 생성 응답"""

    project_id: str
    track: str
    application_draft: dict
    model_name: str
    similar_cases: list[ApprovalCase] = Field(default_factory=list)
    domain_laws: list[Regulation] = Field(default_factory=list)


@router.post(
    "/draft",
    response_model=DraftGenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="신청서 초안 생성 (Step 4)",
    description="""
프로젝트의 canonical 데이터와 선택된 트랙을 기반으로 신청서 초안을 생성합니다.

## 입력
- project_id: 프로젝트 UUID (Step 3 완료 필수)

## 처리
1. DB에서 canonical + track 조회
2. 트랙에 맞는 폼 스키마 로드 (서버 내장)
3. R1(신청 요건/심사 기준), R2(유사 사례) RAG 검색
4. canonical 기반으로 LLM이 폼 필드 값 생성

## 출력
- application_draft: AI가 생성한 폼 데이터 (트랙별 폼 스키마 구조)
    """,
)
async def generate_draft(
    request: DraftGenerateRequest,
    auth_user: AuthUser = Depends(get_auth_user),
) -> DraftGenerateResponse:
    """신청서 초안 생성 API

    1. DB에서 프로젝트 데이터 조회
    2. Application Drafter Agent 실행 (트랙별 폼 스키마 자동 로드)
    3. 결과를 projects.application_draft에 저장
    4. 응답 반환
    """
    project_id = request.project_id

    # 1. 프로젝트 조회 + 권한 확인
    project = get_authorized_project(project_id, auth_user)

    canonical = project.get("canonical")
    if not canonical:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="프로젝트에 서비스 정보(canonical)가 없습니다. Step 1을 먼저 완료하세요.",
        )

    track = project.get("track")
    if not track:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="트랙이 선택되지 않았습니다. Step 3을 먼저 완료하세요.",
        )

    # 2. Application Drafter Agent 실행
    try:
        result = await run_draft(project_id, canonical, track)
    except DraftServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception:
        correlation_id = str(uuid.uuid4())
        logger.exception("Application Drafter 실행 중 오류 [correlation_id=%s]", correlation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"신청서 초안 생성 중 내부 서버 오류가 발생했습니다. (오류 ID: {correlation_id})",
        )

    # 3. 결과 저장
    application_draft = result.get("application_draft", {})
    model_name = result.get("model_name", "")

    # 4. RAG 결과를 ReferencePanel 형식으로 변환
    similar_cases: list[ApprovalCase] = []
    for case in result.get("similar_cases", []):
        # title: service_name 우선, 없으면 company_name 사용
        title = case.get("service_name", "") or case.get("company_name", "") or "승인 사례"
        similar_cases.append(ApprovalCase(
            track=case.get("track", ""),
            date=case.get("designation_date", ""),
            similarity=0,
            title=title,
            company=case.get("company_name", ""),
            summary=case.get("service_description", "") or case.get("content", "")[:200],
            source_url=case.get("source_url"),
        ))

    domain_laws: list[Regulation] = []
    for law in result.get("domain_laws", []):
        metadata = law.get("metadata", {})
        # citation 우선 (예: "의료법 제34조 제1항"), 없으면 law_name
        title = metadata.get("citation", "") or metadata.get("law_name", "") or "관련 법령"
        # source_url 직접 사용
        source_url = metadata.get("source_url")
        domain_laws.append(Regulation(
            category=metadata.get("domain_label", "법령"),
            title=title,
            summary=law.get("content", "")[:300],
            source_url=source_url,
        ))

    # 5. 결과 저장 (RAG 결과 포함) - Pydantic 모델을 dict로 변환
    try:
        save_draft_result(
            project_id=project_id,
            application_draft=application_draft,
            model_name=model_name,
            similar_cases=[c.model_dump() for c in similar_cases],
            domain_laws=[l.model_dump() for l in domain_laws],
        )
    except Exception as e:
        logger.warning("application_draft 저장 실패: %s", str(e))

    return DraftGenerateResponse(
        project_id=project_id,
        track=track,
        application_draft=application_draft,
        model_name=model_name,
        similar_cases=similar_cases,
        domain_laws=domain_laws,
    )


class DraftCardUpdateRequest(BaseModel):
    """신청서 카드 부분 업데이트 요청"""

    card_key: str = Field(..., description="업데이트할 카드 키 (예: fastcheck_application)")
    card_data: dict = Field(..., description="카드 데이터 (flat된 필드-값 쌍)")


class DraftCardUpdateResponse(BaseModel):
    """신청서 카드 부분 업데이트 응답"""

    success: bool
    project_id: str
    card_key: str


@router.patch(
    "/draft/{project_id}",
    response_model=DraftCardUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="신청서 카드 부분 저장",
    description="""
특정 카드만 부분 업데이트합니다. 다른 카드 데이터는 유지됩니다.

## 입력
- project_id: 프로젝트 UUID (path parameter)
- card_key: 업데이트할 카드 키
- card_data: 카드의 필드-값 데이터

## 처리
- 기존 application_draft.form_values에서 해당 카드만 업데이트
- 나머지 카드는 그대로 유지 (JSON 병합)
    """,
)
async def update_draft_card_endpoint(
    project_id: str,
    request: DraftCardUpdateRequest,
    auth_user: AuthUser = Depends(get_auth_user),
) -> DraftCardUpdateResponse:
    """신청서 카드 부분 업데이트 API"""
    # 1. 프로젝트 조회 + 권한 확인
    get_authorized_project(project_id, auth_user)

    # 2. 카드 업데이트
    result = update_draft_card(
        project_id=project_id,
        card_key=request.card_key,
        card_data=request.card_data,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="카드 저장에 실패했습니다.",
        )

    return DraftCardUpdateResponse(
        success=True,
        project_id=project_id,
        card_key=request.card_key,
    )
