"""문서 다운로드 API

신청서 초안을 DOCX/PDF로 다운로드합니다.
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import supabase
from app.services.document_generator import generate_docx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# 트랙 코드 → 템플릿 폴더명 매핑
TRACK_MAP = {
    "quick_check": "fastcheck",
    "temp_permit": "temporary",
    "demo": "demonstration",
}

# 폼 ID → 파일 이름 매핑 (formData.json과 동기화)
FORM_NAME_MAP = {
    "fastcheck-1": "신속처리_신청서",
    "fastcheck-2": "기술서비스_설명서",
    "temporary-1": "임시허가_신청서",
    "temporary-2": "사업계획서",
    "temporary-3": "신청사유",
    "temporary-4": "안전성_검증자료_및_이용자_보호방안",
    "demonstration-1": "실증특례_신청서",
    "demonstration-2": "실증계획서",
    "demonstration-3": "신청사유",
    "demonstration-4": "이용자보호방안",
}


def _get_document_data(project_id: str, form_id: str):
    """문서 생성에 필요한 데이터 추출 (공통)"""
    result = supabase.table("projects").select("*").eq("id", project_id).single().execute()
    project = result.data

    if not project:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")

    application_draft = project.get("application_draft", {})
    if not application_draft:
        raise HTTPException(status_code=400, detail="생성된 초안이 없습니다.")

    form_values = application_draft.get("form_values", {})
    form_data = form_values.get(form_id, {})
    if not form_data:
        raise HTTPException(status_code=400, detail=f"{form_id}에 해당하는 초안 데이터가 없습니다.")

    form_content = form_data.get("data", form_data)
    track = TRACK_MAP.get(project.get("track", "quick_check"), "fastcheck")

    # 회사명 추출 (모든 폼에서 검색)
    company_name = ""
    for fv in form_values.values():
        if not isinstance(fv, dict):
            continue
        data = fv.get("data", fv)
        company_name = (
            data.get("applicant", {}).get("companyName")
            or data.get("applicantOrganizations", [{}])[0].get("organizationName")
            or data.get("organizationProfile", {}).get("organizationName")
        )
        if company_name:
            break

    return track, form_content, company_name


@router.get("/{project_id}/{form_id}/docx")
async def download_docx(project_id: str, form_id: str):
    """신청서 DOCX 다운로드"""
    track, form_content, company_name = _get_document_data(project_id, form_id)

    try:
        buffer = generate_docx(track, form_id, form_content)

        form_name = FORM_NAME_MAP.get(form_id, form_id)
        filename = f"{form_name}({company_name}).docx" if company_name else f"{form_name}.docx"

        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("문서 생성 실패: %s", e)
        raise HTTPException(status_code=500, detail="문서 생성에 실패했습니다.")


@router.get("/{project_id}/{form_id}/pdf")
async def download_pdf(project_id: str, form_id: str):
    """신청서 PDF 다운로드"""
    track, form_content, company_name = _get_document_data(project_id, form_id)

    try:
        docx_buffer = generate_docx(track, form_id, form_content)

        with tempfile.TemporaryDirectory() as tmp_dir:
            docx_path = Path(tmp_dir) / "temp.docx"
            pdf_path = Path(tmp_dir) / "temp.pdf"

            with open(docx_path, "wb") as f:
                f.write(docx_buffer.read())

            subprocess.run([
                "soffice", "--headless", "--convert-to", "pdf",
                "--outdir", tmp_dir, str(docx_path)
            ], check=True)

            with open(pdf_path, "rb") as f:
                pdf_content = f.read()

        form_name = FORM_NAME_MAP.get(form_id, form_id)
        filename = f"{form_name}({company_name}).pdf" if company_name else f"{form_name}.pdf"

        return StreamingResponse(
            iter([pdf_content]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
        )

    except subprocess.CalledProcessError as e:
        logger.error("PDF 변환 실패: %s", e)
        raise HTTPException(status_code=500, detail="PDF 변환에 실패했습니다.")
    except Exception as e:
        logger.error("문서 생성 실패: %s", e)
        raise HTTPException(status_code=500, detail="문서 생성에 실패했습니다.")
