"""Application Drafter Agent 상태 정의"""

from typing import TypedDict


class ApplicationDrafterState(TypedDict, total=False):
    """Application Drafter Agent 상태

    입력:
        project_id: 프로젝트 UUID
        canonical: 프로젝트의 canonical 구조화 데이터
        track: 선택된 트랙 ("demo" | "temp_permit" | "quick_check")

    중간 결과:
        form_schema: 트랙별 폼 스키마 (서버에서 로드)
        application_requirements: R1 신청 요건/작성 가이드
        review_criteria: R1 심사 기준
        similar_cases: R2 유사 승인 사례

    최종 출력:
        application_draft: AI가 값을 채운 폼 데이터 (form_schema와 구조 동일)
    """

    # 입력
    project_id: str
    canonical: dict
    track: str

    # 중간 결과
    form_schema: dict  # 트랙별 폼 스키마 (서버에서 로드)
    application_requirements: list[dict]  # R1: 신청 요건/작성 가이드
    review_criteria: list[dict]  # R1: 심사 기준
    similar_cases: list[dict]  # R2: 유사 승인 사례
    domain_laws: list[dict]  # R3: 도메인별 규제/법령

    # 최종 출력
    application_draft: dict  # form_schema와 동일 구조, canonical 기반으로 값 생성
