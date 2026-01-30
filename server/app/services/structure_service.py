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
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.agents.service_structurer import run_service_structurer
from app.api.schemas.agents import CanonicalStructure, ParsedDocument, StructureResponse
from app.services.parsers import DocumentSubtype

logger = logging.getLogger(__name__)

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


class StructureServiceError(Exception):
    """서비스 구조화 오류"""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class StructureService:
    """서비스 구조화 비즈니스 로직"""

    @staticmethod
    def validate_track(requested_track: str) -> list[DocumentSubtype]:
        """트랙 유효성 검사"""
        if requested_track not in TRACK_SUBTYPE_MAP:
            raise StructureServiceError(
                f"유효하지 않은 트랙: {requested_track}",
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
    def validate_file_count(files: list[UploadFile], expected_subtypes: list[DocumentSubtype], track: str) -> None:
        """파일 수 검증"""
        if len(files) > len(expected_subtypes):
            raise StructureServiceError(
                f"{track} 트랙은 최대 {len(expected_subtypes)}개 파일 지원",
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
    ) -> tuple[list[str], list[str], list[ParsedDocument]]:
        """업로드된 파일 저장"""
        file_paths: list[str] = []
        file_subtypes: list[str] = []
        parsed_docs: list[ParsedDocument] = []

        for idx, upload_file in enumerate(files):
            if not upload_file.filename:
                continue

            filename = cls.sanitize_filename(upload_file.filename)
            temp_path = Path(temp_dir) / f"{idx}_{filename}"

            content = await upload_file.read()
            with open(temp_path, "wb") as f:
                f.write(content)

            subtype = expected_subtypes[idx] if idx < len(expected_subtypes) else None
            subtype_str = subtype.value if subtype else "unknown"

            file_paths.append(str(temp_path))
            file_subtypes.append(subtype_str)
            parsed_docs.append(
                ParsedDocument(
                    file_index=idx,
                    original_filename=filename,
                    assigned_subtype=subtype_str,
                )
            )

        return file_paths, file_subtypes, parsed_docs

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
                parsed_docs[idx].parse_success = parse_result.get("parse_success", False)
                parsed_docs[idx].error_message = parse_result.get("error_message")

    @classmethod
    async def run(
        cls,
        session_id: str,
        requested_track: str,
        consultant_input: str,
        files: list[UploadFile],
    ) -> StructureResponse:
        """서비스 구조화 실행"""
        # 검증
        expected_subtypes = cls.validate_track(requested_track)
        consultant_data = cls.parse_consultant_input(consultant_input)
        cls.validate_file_count(files, expected_subtypes, requested_track)

        temp_dir = tempfile.mkdtemp()

        try:
            # 파일 저장
            file_paths, file_subtypes, parsed_docs = await cls.save_uploaded_files(
                files, expected_subtypes, temp_dir
            )

            # Agent 실행
            logger.info(f"Service Structurer: session={session_id}, track={requested_track}")

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
            print(json.dumps(result.get("canonical_structure"), indent=2, ensure_ascii=False))
            print("=" * 50)

            # 파싱 결과 업데이트
            cls.update_parsed_docs_with_results(
                parsed_docs, result.get("hwp_parse_results", [])
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
