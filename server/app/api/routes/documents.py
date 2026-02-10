"""문서 다운로드 API

신청서 초안을 DOCX/PDF로 다운로드합니다.
"""

import logging
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import supabase
from app.services.document_generator import generate_docx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# 트랙 코드 → 트랙 이름 매핑
TRACK_MAP = {
    "quick_check": "fastcheck",
    "temp_permit": "temporary",
    "demo": "demonstration",
}

# 폼 ID → 파일 이름 매핑
FORM_NAME_MAP = {
    "fastcheck-1": "신속확인_신청서",
    "fastcheck-2": "기술서비스_설명서",
    "temporary-1": "임시허가_신청서",
    "temporary-2": "사업계획서",
    "temporary-3": "소명서",
    "temporary-4": "안전성검증자료",
    "demonstration-1": "실증특례_신청서",
    "demonstration-2": "사업계획서",
    "demonstration-3": "소명서",
    "demonstration-4": "안전성검증자료",
}


@router.get("/{project_id}/{form_id}/docx")
async def download_docx(project_id: str, form_id: str):
    """신청서 DOCX 다운로드

    Args:
        project_id: 프로젝트 ID
        form_id: 폼 ID (fastcheck-1, temporary-1 등)
    """
    # 프로젝트 조회
    result = supabase.table("projects").select("*").eq("id", project_id).single().execute()
    project = result.data

    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")

    # application_draft에서 form_values 가져오기
    application_draft = project.get("application_draft", {})
    if not application_draft:
        raise HTTPException(status_code=400, detail="생성된 초안이 없습니다. Step 4를 먼저 완료하세요.")

    form_values = application_draft.get("form_values", {})
    if not form_values:
        raise HTTPException(status_code=400, detail="생성된 초안이 없습니다. Step 4를 먼저 완료하세요.")

    # form_id에 해당하는 데이터 추출
    form_data = form_values.get(form_id, {})
    if not form_data:
        raise HTTPException(status_code=400, detail=f"{form_id}에 해당하는 초안 데이터가 없습니다.")

    # data 섹션 추출 (폼 스키마 구조: {formId: ..., data: {...}})
    form_content = form_data.get("data", form_data)

    # 트랙 결정
    track_code = project.get("track", "quick_check")
    track = TRACK_MAP.get(track_code, "fastcheck")

    try:
        # DOCX 생성
        buffer = generate_docx(track, form_id, form_content)

        # 파일명 설정
        company_name = form_content.get("applicant", {}).get("companyName", "")
        form_name = FORM_NAME_MAP.get(form_id, form_id)
        filename = f"{form_name}_{company_name}.docx" if company_name else f"{form_name}.docx"

        # RFC 5987 인코딩 (한글 파일명 지원)
        encoded_filename = quote(filename)

        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("문서 생성 실패: %s", e)
        raise HTTPException(status_code=500, detail="문서 생성에 실패했습니다.")
