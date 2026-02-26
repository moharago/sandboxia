"""서비스 구조화 비즈니스 로직

Service Structurer Agent 실행을 위한 서비스 레이어입니다.
"""

import json
import logging
import os
import re
import shutil
import tempfile
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.agents.service_structurer import run_service_structurer
from app.api.schemas.agents import ParsedDocument, StructureResponse
from app.core.config import supabase
from app.services.parsers import DocumentSubtype

logger = logging.getLogger(__name__)

# Supabase Storage 버킷명
STORAGE_BUCKET = "uploads"

# 트랙별 서브타입 매핑 (counseling/quick_check/temp_permit/demo)
TRACK_SUBTYPE_MAP: dict[str, list[DocumentSubtype]] = {
    "counseling": [DocumentSubtype.COUNSELING_APPLICATION],  # 상담신청
    "quick_check": [  # 신속확인
        DocumentSubtype.FASTCHECK_APPLICATION,
        DocumentSubtype.FASTCHECK_DESCRIPTION,
    ],
    "temp_permit": [  # 임시허가
        DocumentSubtype.TEMPORARY_APPLICATION,
        DocumentSubtype.TEMPORARY_BUSINESS_PLAN,
        DocumentSubtype.TEMPORARY_JUSTIFICATION,
        DocumentSubtype.TEMPORARY_SAFETY,
    ],
    "demo": [  # 실증특례
        DocumentSubtype.DEMONSTRATION_APPLICATION,
        DocumentSubtype.DEMONSTRATION_PLAN,
        DocumentSubtype.DEMONSTRATION_JUSTIFICATION,
        DocumentSubtype.DEMONSTRATION_PROTECTION,
    ],
}

# 트랙 한글명 매핑 (로그/에러 메시지용)
# NOTE: 클라이언트(types/data/project.ts)에도 TRACK_LABELS가 정의되어 있습니다.
# 향후 통합 고려 시 API 응답에 라벨을 포함하거나 공유 설정을 도입할 수 있습니다.
TRACK_LABELS: dict[str, str] = {
    "counseling": "상담신청",
    "quick_check": "신속확인",
    "temp_permit": "임시허가",
    "demo": "실증특례",
}


class StructureServiceError(Exception):
    """서비스 구조화 오류"""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class StructureService:
    """서비스 구조화 비즈니스 로직"""

    @staticmethod
    async def delete_existing_files(project_id: str) -> None:
        """기존 프로젝트 파일 삭제 (재분석 시 호출)

        Args:
            project_id: 프로젝트 ID
        """
        # 1. 기존 파일 메타정보 조회
        result = (
            supabase.table("project_files")
            .select("id, storage_path")
            .eq("project_id", project_id)
            .execute()
        )

        if not result.data:
            return

        # 2. Storage에서 파일 삭제
        storage_paths = [f["storage_path"] for f in result.data if f.get("storage_path")]
        if storage_paths:
            try:
                supabase.storage.from_(STORAGE_BUCKET).remove(storage_paths)
            except Exception as e:
                # Storage 삭제 실패해도 메타정보는 삭제 진행 (Storage와 DB는 별개 시스템)
                logger.warning(f"Storage 파일 삭제 실패 (무시): {e}")

        # 3. project_files 테이블에서 메타정보 삭제
        supabase.table("project_files").delete().eq("project_id", project_id).execute()

    @staticmethod
    async def upload_file_to_storage(
        project_id: str,
        file_content: bytes,
        filename: str,
        file_index: int,
    ) -> str:
        """파일을 Supabase Storage에 업로드

        Args:
            project_id: 프로젝트 ID
            file_content: 파일 내용
            filename: 원본 파일명
            file_index: 파일 인덱스

        Returns:
            Storage 내 파일 경로
        """
        # 파일 확장자 추출
        file_ext = Path(filename).suffix.lower() or ".hwp"

        # Storage 경로는 UUID 기반으로 생성 (한글/특수문자 문제 방지)
        # 원본 파일명은 project_files 테이블에 저장
        file_uuid = uuid.uuid4().hex
        storage_path = f"projects/{project_id}/{file_uuid}{file_ext}"

        try:
            supabase.storage.from_(STORAGE_BUCKET).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": "application/octet-stream"},
            )
            return storage_path
        except Exception as e:
            raise StructureServiceError(f"파일 업로드 실패: {str(e)}", status_code=500)

    @staticmethod
    async def save_file_metadata(
        project_id: str,
        filename: str,
        storage_path: str,
        file_type: str,
        extracted_text: str | None = None,
    ) -> dict[str, Any]:
        """project_files 테이블에 파일 메타정보 저장

        Args:
            project_id: 프로젝트 ID
            filename: 원본 파일명
            storage_path: Storage 내 파일 경로
            file_type: 파일 확장자
            extracted_text: 추출된 텍스트 (옵션)

        Returns:
            저장된 레코드
        """
        try:
            result = (
                supabase.table("project_files")
                .insert(
                    {
                        "project_id": project_id,
                        "file_name": filename,
                        "storage_bucket": STORAGE_BUCKET,
                        "storage_path": storage_path,
                        "file_type": file_type,
                        "extracted_text": extracted_text,
                    }
                )
                .execute()
            )
            return result.data[0]
        except Exception as e:
            logger.error(f"파일 메타정보 저장 실패: {e}")
            raise StructureServiceError(
                f"파일 메타정보 저장 실패: {str(e)}", status_code=500
            )

    @staticmethod
    async def update_project_basic_info(
        project_id: str,
        consultant_data: dict[str, Any],
        requested_track: str,
    ) -> None:
        """projects 테이블에 기본 정보 업데이트

        Args:
            project_id: 프로젝트 ID
            consultant_data: 컨설턴트 입력 데이터
            requested_track: 선택한 트랙 (counseling/quick_check/temp_permit/demo)
        """
        try:
            update_data = {
                "updated_at": datetime.now().isoformat(),
            }

            # 컨설턴트 입력에서 기본 정보 추출
            if consultant_data.get("company_name"):
                update_data["company_name"] = consultant_data["company_name"]
            if consultant_data.get("service_name"):
                update_data["service_name"] = consultant_data["service_name"]
            if consultant_data.get("service_description"):
                update_data["service_description"] = consultant_data[
                    "service_description"
                ]
            if consultant_data.get("additional_memo"):
                update_data["additional_notes"] = consultant_data["additional_memo"]

            # 트랙 저장 (counseling/quick_check/temp_permit/demo)
            if requested_track in TRACK_SUBTYPE_MAP:
                update_data["track"] = requested_track

            supabase.table("projects").update(update_data).eq(
                "id", project_id
            ).execute()
            logger.info(f"프로젝트 기본 정보 업데이트 성공: {project_id}")
        except Exception as e:
            logger.error(f"프로젝트 기본 정보 업데이트 실패: {e}")
            raise StructureServiceError(
                f"프로젝트 업데이트 실패: {str(e)}", status_code=500
            )

    @staticmethod
    async def update_project_analysis_results(
        project_id: str,
        application_input: list[dict[str, Any]] | None,
        canonical_structure: dict[str, Any] | None,
    ) -> None:
        """projects 테이블에 분석 결과 업데이트

        Args:
            project_id: 프로젝트 ID
            application_input: 파싱된 원본 JSON (hwp_parse_results)
            canonical_structure: Canonical 구조
        """
        try:
            update_data = {
                "updated_at": datetime.now().isoformat(),
                "current_step": 1,  # 서비스 분석 완료 → Step 1 완료
                "status": 1,  # Step 1~3은 항상 status=1
            }

            if application_input is not None:
                update_data["application_input"] = application_input
            if canonical_structure is not None:
                update_data["canonical"] = canonical_structure

            supabase.table("projects").update(update_data).eq(
                "id", project_id
            ).execute()
            logger.info(f"프로젝트 분석 결과 업데이트 성공: {project_id}")
        except Exception as e:
            logger.error(f"프로젝트 분석 결과 업데이트 실패: {e}")
            raise StructureServiceError(
                f"프로젝트 분석 결과 업데이트 실패: {str(e)}", status_code=500
            )

    @staticmethod
    def validate_track(requested_track: str) -> list[DocumentSubtype]:
        """트랙 유효성 검사

        Args:
            requested_track: 트랙 (counseling/quick_check/temp_permit/demo)
        """
        if requested_track not in TRACK_SUBTYPE_MAP:
            valid_tracks = ", ".join(TRACK_SUBTYPE_MAP.keys())
            raise StructureServiceError(
                f"유효하지 않은 트랙: {requested_track}. 유효한 값: {valid_tracks}",
                status_code=400,
            )
        return TRACK_SUBTYPE_MAP[requested_track]

    @staticmethod
    def parse_consultant_input(consultant_input: str) -> dict[str, Any]:
        """컨설턴트 입력 JSON 파싱"""
        try:
            return json.loads(consultant_input)
        except json.JSONDecodeError as e:
            raise StructureServiceError(
                f"consultant_input JSON 파싱 오류: {str(e)}",
                status_code=400,
            )

    @staticmethod
    def validate_file_count(
        files: list[UploadFile], expected_subtypes: list[DocumentSubtype], track: str
    ) -> None:
        """파일 수 검증"""
        track_label = TRACK_LABELS.get(track, track)
        if len(files) > len(expected_subtypes):
            raise StructureServiceError(
                f"{track_label} 트랙은 최대 {len(expected_subtypes)}개 파일 지원",
                status_code=400,
            )

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """파일명 정규화 및 살균"""
        filename = unicodedata.normalize("NFC", filename)
        filename = os.path.basename(filename)
        filename = re.sub(r"[\x00/\\]", "", filename)
        if not filename or filename.startswith("."):
            filename = f"upload_{uuid.uuid4().hex[:8]}.hwp"
        return filename

    @classmethod
    async def save_uploaded_files(
        cls,
        files: list[UploadFile],
        expected_subtypes: list[DocumentSubtype],
        temp_dir: str,
        project_id: str,
    ) -> tuple[list[str], list[str], list[ParsedDocument], list[bytes]]:
        """업로드된 파일 저장 및 Supabase 업로드

        Args:
            files: 업로드된 파일 목록
            expected_subtypes: 예상 서브타입 목록
            temp_dir: 임시 디렉토리 경로
            project_id: 프로젝트 ID (Supabase 저장용)

        Returns:
            (파일 경로 목록, 서브타입 목록, ParsedDocument 목록, 파일 내용 목록)
        """
        file_paths: list[str] = []
        file_subtypes: list[str] = []
        parsed_docs: list[ParsedDocument] = []
        file_contents: list[bytes] = []

        for idx, upload_file in enumerate(files):
            if not upload_file.filename:
                continue

            filename = cls.sanitize_filename(upload_file.filename)
            temp_path = Path(temp_dir) / f"{idx}_{filename}"

            content = await upload_file.read()
            file_contents.append(content)

            with open(temp_path, "wb") as f:
                f.write(content)

            subtype = expected_subtypes[idx] if idx < len(expected_subtypes) else None
            subtype_str = subtype.value if subtype else "unknown"

            # 파일 확장자 추출
            file_ext = Path(filename).suffix.lstrip(".").lower() or "unknown"

            # Supabase Storage에 업로드
            storage_path = await cls.upload_file_to_storage(
                project_id=project_id,
                file_content=content,
                filename=filename,
                file_index=idx,
            )

            # project_files 테이블에 메타정보 저장
            await cls.save_file_metadata(
                project_id=project_id,
                filename=filename,
                storage_path=storage_path,
                file_type=file_ext,
                extracted_text=None,  # 파싱 후 업데이트
            )

            file_paths.append(str(temp_path))
            file_subtypes.append(subtype_str)
            parsed_docs.append(
                ParsedDocument(
                    file_index=idx,
                    original_filename=filename,
                    assigned_subtype=subtype_str,
                )
            )

        return file_paths, file_subtypes, parsed_docs, file_contents

    @staticmethod
    def update_parsed_docs_with_results(
        parsed_docs: list[ParsedDocument],
        hwp_parse_results: list[dict[str, Any]],
    ) -> None:
        """파싱 결과로 ParsedDocument 업데이트"""
        for idx, parse_result in enumerate(hwp_parse_results):
            if idx < len(parsed_docs):
                parsed_docs[idx].detected_type = parse_result.get("document_type")
                parsed_docs[idx].detected_subtype = parse_result.get("document_subtype")
                parsed_docs[idx].parse_success = parse_result.get(
                    "parse_success", False
                )
                parsed_docs[idx].error_message = parse_result.get("error_message")

    @classmethod
    async def run(
        cls,
        session_id: str,
        requested_track: str,
        consultant_input: str,
        files: list[UploadFile],
    ) -> StructureResponse:
        """서비스 구조화 실행

        Args:
            session_id: 세션 ID (= project_id)
            requested_track: 트랙 (counseling/quick_check/temp_permit/demo)
            consultant_input: 컨설턴트 입력 JSON 문자열
            files: 업로드 파일 목록

        Returns:
            StructureResponse
        """
        # 검증
        expected_subtypes = cls.validate_track(requested_track)
        consultant_data = cls.parse_consultant_input(consultant_input)
        cls.validate_file_count(files, expected_subtypes, requested_track)

        temp_dir = tempfile.mkdtemp()

        try:
            # 1. 컨설턴트 입력으로 기본 정보 업데이트 (회사명, 서비스명, 신청서 양식 유형 등)
            await cls.update_project_basic_info(
                project_id=session_id,
                consultant_data=consultant_data,
                requested_track=requested_track,
            )

            # 2. 기존 파일 삭제 (재분석 시)
            await cls.delete_existing_files(project_id=session_id)

            # 3. 파일 저장 (임시 디렉토리 + Supabase Storage + project_files 테이블)
            file_paths, file_subtypes, parsed_docs, _ = await cls.save_uploaded_files(
                files, expected_subtypes, temp_dir, project_id=session_id
            )

            # 4. Agent 실행
            logger.info(
                f"Service Structurer: session={session_id}, track={requested_track}"
            )

            result = await run_service_structurer(
                session_id=session_id,
                requested_track=requested_track,
                consultant_input=consultant_data,
                file_paths=file_paths,
                file_subtypes=file_subtypes,
            )

            # 디버그: Canonical Structure 출력
            print("=" * 50)
            print("Canonical Structure:")
            print(
                json.dumps(
                    result.get("canonical_structure"), indent=2, ensure_ascii=False
                )
            )
            print("=" * 50)

            # 5. 파싱 결과로 ParsedDocument 업데이트
            cls.update_parsed_docs_with_results(
                parsed_docs, result.get("hwp_parse_results", [])
            )

            # 6. projects 테이블에 분석 결과 저장 (application_input, canonical)
            hwp_parse_results = result.get("hwp_parse_results", [])
            canonical_structure = result.get("canonical_structure")

            await cls.update_project_analysis_results(
                project_id=session_id,
                application_input=hwp_parse_results if hwp_parse_results else None,
                canonical_structure=canonical_structure,
            )

            return StructureResponse(
                session_id=session_id,
                requested_track=requested_track,
                canonical_structure=result.get("canonical_structure"),
                parsed_documents=parsed_docs,
                error=result.get("error"),
                messages=result.get("messages", []),
            )

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
