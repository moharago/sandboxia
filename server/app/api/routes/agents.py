"""AI Agent API 라우터

6개 에이전트에 대한 API 엔드포인트:
1. Service Structurer - /agents/structure
2. Eligibility Evaluator - /agents/eligibility (TODO)
3. Track Recommender - /agents/track (TODO)
4. Application Drafter - /agents/draft (TODO)
5. Strategy Advisor - /agents/strategy (TODO)
6. Risk Checker - /agents/risk (TODO)
"""

import json
import tempfile
import unicodedata
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.services.parsers import (
    DocumentSubtype,
    parse_hwp_files,
)

router = APIRouter(prefix="/agents", tags=["agents"])


# ===============================
# HWP 파싱 엔드포인트 (에이전트 미연결)
# ===============================

# 트랙별 서브타입 매핑
TRACK_SUBTYPE_MAP: dict[str, list[DocumentSubtype]] = {
    "counseling": [DocumentSubtype.COUNSELING_APPLICATION],
    "fastcheck": [
        DocumentSubtype.FASTCHECK_APPLICATION,
        DocumentSubtype.FASTCHECK_DESCRIPTION,
    ],
    "temporary": [
        DocumentSubtype.TEMPORARY_APPLICATION,
        DocumentSubtype.TEMPORARY_BUSINESS_PLAN,
        DocumentSubtype.TEMPORARY_JUSTIFICATION,
        DocumentSubtype.TEMPORARY_SAFETY,
    ],
    "demonstration": [
        DocumentSubtype.DEMONSTRATION_APPLICATION,
        DocumentSubtype.DEMONSTRATION_PLAN,
        DocumentSubtype.DEMONSTRATION_JUSTIFICATION,
        DocumentSubtype.DEMONSTRATION_PROTECTION,
    ],
}


@router.post(
    "/structure",
    status_code=status.HTTP_200_OK,
    summary="서비스 정보 파싱 (HWP)",
    description="""
클라이언트에서 업로드한 HWP 파일을 파싱하여 JSON 구조로 반환합니다.

## 입력 (FormData)
- session_id: 세션 ID
- requested_track: 신청 유형 (counseling, fastcheck, temporary, demonstration)
- consultant_input: 컨설턴트 입력 정보 (JSON 문자열)
- files: 업로드된 HWP 파일들 (순서대로 서브타입 할당)

## 출력
- session_id: 세션 ID
- requested_track: 신청 유형
- consultant_input: 파싱된 컨설턴트 입력
- parsed_documents: HWP 파일 파싱 결과
    """,
)
async def parse_service_files(
    session_id: str = Form(...),
    requested_track: str = Form(...),
    consultant_input: str = Form(...),
    files: list[UploadFile] = File(...),
) -> dict:
    """서비스 정보 HWP 파일 파싱

    클라이언트에서 업로드한 HWP 파일을 파싱하여
    JSON 구조로 변환합니다.
    에이전트 로직은 아직 연결하지 않습니다.
    """
    # 트랙 유효성 검사
    if requested_track not in TRACK_SUBTYPE_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 트랙: {requested_track}. "
            f"가능한 값: {list(TRACK_SUBTYPE_MAP.keys())}",
        )

    # 컨설턴트 입력 JSON 파싱
    try:
        consultant_data = json.loads(consultant_input)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"consultant_input JSON 파싱 오류: {str(e)}",
        )

    # 트랙별 예상 파일 수 확인
    expected_subtypes = TRACK_SUBTYPE_MAP[requested_track]
    if len(files) > len(expected_subtypes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{requested_track} 트랙은 최대 {len(expected_subtypes)}개의 "
            f"파일을 지원합니다. 업로드된 파일 수: {len(files)}",
        )

    # 임시 디렉토리에 파일 저장 및 파싱
    parsed_results = []
    temp_dir = tempfile.mkdtemp()

    try:
        file_paths = []

        for idx, upload_file in enumerate(files):
            if not upload_file.filename:
                continue

            # 파일명 정규화 (macOS NFD → NFC)
            normalized_filename = unicodedata.normalize("NFC", upload_file.filename)

            # 임시 파일로 저장
            temp_path = Path(temp_dir) / f"{idx}_{normalized_filename}"
            content = await upload_file.read()

            with open(temp_path, "wb") as f:
                f.write(content)

            # 서브타입 할당 (업로드 순서 기반)
            subtype = expected_subtypes[idx] if idx < len(expected_subtypes) else None

            file_paths.append(
                {
                    "path": str(temp_path),
                    "original_filename": normalized_filename,
                    "assigned_subtype": subtype.value if subtype else None,
                }
            )

        # HWP 파일 파싱 (클라이언트에서 지정한 subtype 전달)
        hwp_paths = [f["path"] for f in file_paths]
        subtypes = [f["assigned_subtype"] for f in file_paths]
        parsed_docs = parse_hwp_files(hwp_paths, subtypes)

        # 파싱 결과 정리
        for idx, (file_info, doc) in enumerate(zip(file_paths, parsed_docs)):
            doc_result = {
                "file_index": idx,
                "original_filename": file_info["original_filename"],
                "assigned_subtype": file_info["assigned_subtype"],
                "detected_type": (
                    doc.document_category.value if doc.document_category else None
                ),
                "detected_subtype": (
                    doc.document_subtype.value if doc.document_subtype else None
                ),
                "sections": [],
                "fields": doc.extracted_fields,
                "metadata": doc.metadata,
            }

            # 섹션 정보 추가
            for section in doc.sections:
                doc_result["sections"].append(
                    {
                        "title": section.title,
                        "content_preview": (
                            section.content[:200] + "..."
                            if len(section.content) > 200
                            else section.content
                        ),
                    }
                )

            parsed_results.append(doc_result)

        # 결과 출력 (디버깅용)
        result = {
            "session_id": session_id,
            "requested_track": requested_track,
            "consultant_input": consultant_data,
            "parsed_documents": parsed_results,
        }

        print("\n" + "=" * 60)
        print("HWP 파싱 결과")
        print("=" * 60)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("=" * 60 + "\n")

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"HWP 파싱 중 오류 발생: {str(e)}",
        )
    finally:
        # 임시 파일 정리
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)
