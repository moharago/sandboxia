"""HWP 파일 파싱 서비스

HWP 5.0 포맷 파싱을 위한 서비스.
olefile을 사용하여 OLE Compound Document 구조를 분석합니다.

HWP 5.0 파일 구조:
- FileHeader: 파일 시그니처 및 버전 정보
- DocInfo: 문서 정보 (글꼴, 스타일 등)
- BodyText/Section*: 본문 텍스트 (압축됨)
- PrvText: 미리보기 텍스트 (UTF-16LE)
- BinData: 임베디드 바이너리 데이터

지원하는 문서 유형:
1. 상담신청 (counseling): 1개 파일 - "(양식)_"로 시작
2. 신속확인 (fastcheck): 2개 파일 - "01-"로 시작
3. 임시허가 (temporary): 4개 파일 - "02-"로 시작
4. 실증특례 (demonstration): 4개 파일 - "03-"로 시작
"""

import re
import struct
import unicodedata
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import olefile

from app.services.parsers.hwp_patterns import (
    LAW_LIST_PATTERNS,
    TECHNOLOGY_LIST_PATTERNS,
    DocumentCategory,
    DocumentSubtype,
    get_patterns_for_subtype,
)

# HWP 레코드 태그 상수
HWPTAG_BEGIN = 0x010
HWPTAG_PARA_TEXT = HWPTAG_BEGIN + 51  # 0x43 (67)


@dataclass
class HWPSection:
    """HWP 섹션 정보"""

    index: int
    title: str = ""
    content: str = ""
    tables: list[list[list[str]]] = field(default_factory=list)


@dataclass
class HWPDocument:
    """파싱된 HWP 문서"""

    file_path: str
    file_name: str
    version: str = ""
    is_compressed: bool = False
    is_encrypted: bool = False
    raw_text: str = ""
    sections: list[HWPSection] = field(default_factory=list)
    extracted_fields: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    parse_success: bool = False
    error_message: str = ""
    document_category: DocumentCategory = DocumentCategory.UNKNOWN
    document_subtype: DocumentSubtype = DocumentSubtype.UNKNOWN


class HWPParser:
    """HWP 파일 파서

    olefile을 사용하여 HWP 5.0 포맷 파일을 파싱합니다.
    11가지 문서 유형을 지원합니다.
    """

    def __init__(
        self,
        file_path: str | Path,
        document_subtype: DocumentSubtype = DocumentSubtype.UNKNOWN,
    ):
        """HWP 파서 초기화

        Args:
            file_path: HWP 파일 경로
            document_subtype: 문서 서브타입 (클라이언트에서 지정)
        """
        self.file_path = Path(file_path)
        self.ole = None

        # subtype에서 category 추출
        category = self._get_category_from_subtype(document_subtype)

        self.document = HWPDocument(
            file_path=str(self.file_path),
            file_name=self.file_path.name,
            document_category=category,
            document_subtype=document_subtype,
        )

    def _get_category_from_subtype(
        self, subtype: DocumentSubtype
    ) -> DocumentCategory:
        """서브타입에서 카테고리 추출"""
        subtype_value = subtype.value
        if subtype_value.startswith("counseling"):
            return DocumentCategory.COUNSELING
        elif subtype_value.startswith("fastcheck"):
            return DocumentCategory.FASTCHECK
        elif subtype_value.startswith("temporary"):
            return DocumentCategory.TEMPORARY
        elif subtype_value.startswith("demonstration"):
            return DocumentCategory.DEMONSTRATION
        return DocumentCategory.UNKNOWN

    def parse(self) -> HWPDocument:
        """HWP 파일 파싱 실행

        Returns:
            HWPDocument: 파싱된 문서 정보
        """
        try:
            if not self.file_path.exists():
                self.document.error_message = (
                    f"파일을 찾을 수 없습니다: {self.file_path}"
                )
                return self.document

            # OLE 파일 열기
            self.ole = olefile.OleFileIO(str(self.file_path))

            # 파일 헤더 파싱
            self._parse_file_header()

            # 텍스트 추출 (여러 방법 시도)
            text = self._extract_text()
            self.document.raw_text = text

            # 섹션 분리 및 필드 추출
            self._extract_sections(text)
            self._extract_fields(text)

            self.document.parse_success = True

        except Exception as e:
            self.document.error_message = f"파싱 오류: {str(e)}"
            self.document.parse_success = False

        finally:
            if self.ole:
                self.ole.close()

        return self.document

    def _parse_file_header(self) -> None:
        """FileHeader 스트림 파싱"""
        try:
            if self.ole.exists("FileHeader"):
                header_data = self.ole.openstream("FileHeader").read()

                # 시그니처 확인 (HWP Document File)
                signature = (
                    header_data[:32].decode("utf-16le", errors="ignore").strip("\x00")
                )
                self.document.metadata["signature"] = signature

                # 버전 정보 (offset 32-35)
                if len(header_data) >= 36:
                    version = struct.unpack("<I", header_data[32:36])[0]
                    major = (version >> 24) & 0xFF
                    minor = (version >> 16) & 0xFF
                    build = (version >> 8) & 0xFF
                    revision = version & 0xFF
                    self.document.version = f"{major}.{minor}.{build}.{revision}"

                # 속성 플래그 (offset 36-39)
                if len(header_data) >= 40:
                    flags = struct.unpack("<I", header_data[36:40])[0]
                    self.document.is_compressed = bool(flags & 0x01)
                    self.document.is_encrypted = bool(flags & 0x02)

        except Exception:
            pass

    def _extract_text(self) -> str:
        """텍스트 추출 (여러 방법 시도)

        Returns:
            추출된 텍스트
        """
        text = ""

        # 방법 1: PrvText 스트림 (미리보기 텍스트)
        text = self._extract_from_prvtext()
        if text.strip():
            return text

        # 방법 2: BodyText 섹션 (압축 해제 필요)
        text = self._extract_from_bodytext()
        if text.strip():
            return text

        # 방법 3: 모든 스트림에서 텍스트 추출 시도
        text = self._extract_from_all_streams()

        return text

    def _extract_from_prvtext(self) -> str:
        """PrvText 스트림에서 텍스트 추출

        PrvText는 미리보기용 텍스트로 UTF-16LE 인코딩입니다.
        """
        try:
            if self.ole.exists("PrvText"):
                data = self.ole.openstream("PrvText").read()
                # UTF-16LE 디코딩
                text = data.decode("utf-16le", errors="ignore")
                # NULL 문자 제거
                text = text.replace("\x00", "")
                return text.strip()
        except Exception:
            pass
        return ""

    def _extract_from_bodytext(self) -> str:
        """BodyText 섹션에서 텍스트 추출

        BodyText/Section* 스트림은 압축되어 있을 수 있습니다.
        """
        texts = []

        try:
            # Section 스트림 찾기
            section_streams = [
                entry
                for entry in self.ole.listdir()
                if len(entry) >= 2
                and entry[0] == "BodyText"
                and entry[1].startswith("Section")
            ]

            for stream_path in sorted(section_streams):
                stream_name = "/".join(stream_path)
                try:
                    data = self.ole.openstream(stream_name).read()

                    # 압축 해제 시도
                    if self.document.is_compressed:
                        try:
                            data = zlib.decompress(data, -15)
                        except zlib.error:
                            pass

                    # 레코드 파싱하여 텍스트 추출
                    section_text = self._parse_body_records(data)
                    if section_text:
                        texts.append(section_text)

                except Exception:
                    pass

        except Exception:
            pass

        return "\n\n".join(texts)

    def _parse_body_records(self, data: bytes) -> str:
        """BodyText 레코드 파싱

        HWP 레코드 구조:
        - Header (4 bytes): TagID(10bit) + Level(10bit) + Size(12bit)
        - Data: 가변 길이

        Args:
            data: 섹션 데이터

        Returns:
            추출된 텍스트
        """
        texts = []
        offset = 0

        while offset < len(data) - 4:
            try:
                # 레코드 헤더 읽기 (tag_id: 10bits, level: 10bits, size: 12bits)
                header = struct.unpack("<I", data[offset : offset + 4])[0]
                tag_id = header & 0x3FF
                size = (header >> 20) & 0xFFF

                # 확장 크기 처리
                if size == 0xFFF:
                    if offset + 8 > len(data):
                        break
                    size = struct.unpack("<I", data[offset + 4 : offset + 8])[0]
                    offset += 8
                else:
                    offset += 4

                # 데이터 읽기
                if offset + size > len(data):
                    break

                record_data = data[offset : offset + size]
                offset += size

                # PARA_TEXT 레코드에서 텍스트 추출
                if tag_id == HWPTAG_PARA_TEXT:
                    text = self._extract_para_text(record_data)
                    if text:
                        texts.append(text)

            except Exception:
                break

        return "\n".join(texts)

    def _extract_para_text(self, data: bytes) -> str:
        """PARA_TEXT 레코드에서 텍스트 추출

        Args:
            data: PARA_TEXT 레코드 데이터

        Returns:
            추출된 텍스트
        """
        chars = []
        i = 0

        while i < len(data) - 1:
            # UTF-16LE 문자 읽기 (2바이트)
            char_code = struct.unpack("<H", data[i : i + 2])[0]

            # 제어 문자 처리
            if char_code < 32:
                if char_code == 0:  # NULL
                    i += 2
                    continue
                elif char_code == 10:  # 줄바꿈
                    chars.append("\n")
                    i += 2
                    continue
                elif char_code == 13:  # 캐리지 리턴
                    i += 2
                    continue
                elif char_code in (1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23):
                    # 인라인 컨트롤 (확장 문자)
                    # 구조: [char_code: 2bytes][ext_len: 2bytes][payload: ext_len*2 bytes]
                    if i + 4 <= len(data):
                        ext_len = struct.unpack("<H", data[i + 2 : i + 4])[0]
                        # char_code(2) + ext_len field(2) + payload(ext_len*2)
                        i += 4 + ext_len * 2
                    else:
                        i += 2
                    continue
                else:
                    # 기타 제어 문자
                    i += 2
                    continue

            # 일반 문자
            try:
                chars.append(chr(char_code))
            except ValueError:
                pass

            i += 2

        return "".join(chars).strip()

    def _extract_from_all_streams(self) -> str:
        """모든 스트림에서 텍스트 추출 시도 (폴백)"""
        texts = []

        try:
            for entry in self.ole.listdir():
                stream_name = "/".join(entry)
                try:
                    data = self.ole.openstream(stream_name).read()

                    # UTF-16LE 디코딩 시도
                    try:
                        text = data.decode("utf-16le", errors="ignore")
                        text = text.replace("\x00", "")
                        if text.strip() and len(text) > 10:
                            # 유효한 텍스트인지 확인 (한글/영문 비율)
                            korean_chars = len(re.findall(r"[가-힣]", text))
                            total_chars = len(text)
                            if korean_chars / max(total_chars, 1) > 0.1:
                                texts.append(text.strip())
                    except Exception:
                        pass

                except Exception:
                    pass

        except Exception:
            pass

        return "\n\n".join(texts)

    def _extract_sections(self, text: str) -> None:
        """텍스트에서 섹션 분리

        Args:
            text: 전체 텍스트
        """
        # 줄바꿈으로 섹션 분리
        paragraphs = text.split("\n\n")

        for i, para in enumerate(paragraphs):
            if para.strip():
                section = HWPSection(
                    index=i,
                    content=para.strip(),
                )
                # 첫 줄을 제목으로 사용
                lines = para.strip().split("\n")
                if lines:
                    section.title = lines[0][:50]  # 최대 50자

                self.document.sections.append(section)

    def _extract_fields(self, text: str) -> None:
        """텍스트에서 필드 추출

        문서 타입에 맞는 패턴을 사용하여 필드를 추출합니다.

        Args:
            text: 전체 텍스트
        """
        # 텍스트 전처리: HWP 제어 문자 정리
        cleaned_text = self._clean_hwp_text(text)

        # 문서 타입별 패턴 가져오기
        type_patterns = get_patterns_for_subtype(self.document.document_subtype)

        # 단일 값 필드 추출
        for field_name, patterns in type_patterns.items():
            for pattern in patterns:
                match = re.search(
                    pattern, cleaned_text, re.IGNORECASE | re.MULTILINE | re.DOTALL
                )
                if match:
                    # 그룹이 있는 경우 첫 번째 그룹 사용
                    if match.lastindex and match.lastindex >= 1:
                        value = match.group(1).strip()
                    else:
                        # 그룹이 없는 경우 (체크박스 패턴 등)
                        value = "checked"

                    # 값 정제
                    value = self._clean_field_value(value)
                    if value and len(value) > 1:
                        self.document.extracted_fields[field_name] = value
                        break

        # 기술 요소 리스트 추출 (설명서/계획서 문서에서)
        subtype = self.document.document_subtype
        if subtype in [
            DocumentSubtype.FASTCHECK_DESCRIPTION,
            DocumentSubtype.TEMPORARY_BUSINESS_PLAN,
            DocumentSubtype.DEMONSTRATION_PLAN,
        ]:
            innovation_points = self._extract_technology_list(cleaned_text)
            if innovation_points:
                self.document.extracted_fields["innovation_points"] = innovation_points

        # 관련 법령 리스트 추출
        related_laws = self._extract_law_list(cleaned_text)
        if related_laws:
            self.document.extracted_fields["related_laws"] = related_laws

        # 문서 메타데이터 추가
        self.document.metadata["document_category"] = self.document.document_category.value
        self.document.metadata["document_subtype"] = self.document.document_subtype.value

    def _extract_technology_list(self, text: str) -> list[str]:
        """기술 요소 리스트 추출

        Args:
            text: 정제된 텍스트

        Returns:
            기술 요소 리스트
        """
        tech_items = []

        # 방법 1: 패턴 매칭으로 기술 요소 블록 추출
        for pattern in TECHNOLOGY_LIST_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                block = match.group(1).strip()
                # 줄바꿈으로 분리하여 각 항목 추출
                lines = block.split("\n")
                for line in lines:
                    line = line.strip()
                    # 의미 있는 항목만 추가 (10자 이상)
                    if line and len(line) > 10 and not line.startswith("2."):
                        # 불필요한 접두사 제거
                        line = re.sub(r"^[-·•]\s*", "", line)
                        line = re.sub(r"^\d+[.)]\s*", "", line)
                        if line:
                            tech_items.append(line)
                break

        # 방법 2: "~기술" 또는 "~시스템" 패턴으로 개별 추출
        if not tech_items:
            tech_patterns = [
                r"([가-힣\w\s·]+(?:기술|시스템|장치|분석|처리))",
            ]
            for pattern in tech_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    item = match.strip()
                    # 충분히 긴 항목만 추가
                    if len(item) > 15 and item not in tech_items:
                        tech_items.append(item)
                    if len(tech_items) >= 10:  # 최대 10개
                        break

        # 중복 제거 및 정제
        unique_items = []
        for item in tech_items:
            # "를 위한", "을 위한" 등으로 시작하는 경우 정제
            item = re.sub(r"^[를을]?\s*위한\s*", "", item)
            if item and item not in unique_items:
                unique_items.append(item)

        return unique_items[:10]  # 최대 10개

    def _extract_law_list(self, text: str) -> list[str]:
        """관련 법령 리스트 추출

        Args:
            text: 정제된 텍스트

        Returns:
            법령명 리스트
        """
        laws = []

        for pattern in LAW_LIST_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                law_name = match.strip()
                if law_name and law_name not in laws:
                    laws.append(law_name)

        return laws

    def _clean_hwp_text(self, text: str) -> str:
        """HWP 제어 문자 정리

        Args:
            text: 원본 텍스트

        Returns:
            정리된 텍스트
        """
        # HWP 셀 구분자 정리
        text = re.sub(r"><+", "\n", text)
        text = re.sub(r"<>+", "\n", text)
        text = re.sub(r"[<>]+", " ", text)

        # 여러 공백을 하나로
        text = re.sub(r"[ \t]+", " ", text)

        # 여러 줄바꿈을 최대 2개로
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def _clean_field_value(self, value: str) -> str:
        """필드 값 정리

        Args:
            value: 원본 값

        Returns:
            정리된 값
        """
        # HWP 제어 문자 제거
        value = re.sub(r"[<>]+", " ", value)

        # 괄호 안 설명 제거: (성명), (소속) 등
        value = re.sub(r"^\s*\([^)]*\)\s*", "", value)

        # ※ 이후 설명 제거
        value = re.sub(r"\s*※.*$", "", value)

        # 여러 공백을 하나로
        value = re.sub(r"\s+", " ", value)

        # 앞뒤 공백 제거
        value = value.strip()

        # 끝에 붙은 다음 필드 레이블 제거
        value = re.sub(
            r"\s*(회사명|대표자|주소|전화|이메일|명칭|유형|내용|소관|예상).*$",
            "",
            value,
            flags=re.IGNORECASE,
        )

        return value.strip()


def parse_hwp_file(
    file_path: str | Path,
    document_subtype: DocumentSubtype = DocumentSubtype.UNKNOWN,
) -> HWPDocument:
    """HWP 파일 파싱 헬퍼 함수

    Args:
        file_path: HWP 파일 경로
        document_subtype: 문서 서브타입 (클라이언트에서 지정)

    Returns:
        HWPDocument: 파싱된 문서 정보
    """
    parser = HWPParser(file_path, document_subtype)
    return parser.parse()


def parse_hwp_files(
    file_paths: list[str | Path],
    subtypes: list[str] | None = None,
) -> list[HWPDocument]:
    """여러 HWP 파일 파싱 헬퍼 함수

    Args:
        file_paths: HWP 파일 경로 리스트
        subtypes: 각 파일의 서브타입 리스트 (예: ["temporary-1", "temporary-2", ...])

    Returns:
        HWPDocument 리스트
    """
    results = []
    for idx, fp in enumerate(file_paths):
        # subtype 문자열을 enum으로 변환
        subtype = DocumentSubtype.UNKNOWN
        if subtypes and idx < len(subtypes) and subtypes[idx]:
            try:
                subtype = DocumentSubtype(subtypes[idx])
            except ValueError:
                pass
        results.append(parse_hwp_file(fp, subtype))
    return results


def merge_parsed_documents(documents: list[HWPDocument]) -> dict[str, Any]:
    """여러 파싱된 문서를 하나의 구조로 병합

    같은 카테고리의 여러 문서에서 추출한 필드들을 하나로 병합합니다.

    Args:
        documents: 파싱된 HWPDocument 리스트

    Returns:
        병합된 필드 딕셔너리
    """
    merged: dict[str, Any] = {
        "company_info": {},
        "service_info": {},
        "technology_info": {},
        "regulatory_info": {},
        "business_plan": {},
        "safety_and_protection": {},
        "justification": {},
        "metadata": {
            "source_files": [],
            "document_category": None,
            "document_subtypes": [],
        },
    }

    for doc in documents:
        if not doc.parse_success:
            continue

        # 메타데이터 수집
        merged["metadata"]["source_files"].append(doc.file_name)
        merged["metadata"]["document_subtypes"].append(doc.document_subtype.value)

        if merged["metadata"]["document_category"] is None:
            merged["metadata"]["document_category"] = doc.document_category.value

        fields = doc.extracted_fields

        # 회사 정보 매핑
        company_fields = [
            "company_name",
            "representative",
            "business_number",
            "address",
            "phone",
            "email",
            "position",
            "name",
        ]
        for f in company_fields:
            if f in fields and f not in merged["company_info"]:
                merged["company_info"][f] = fields[f]

        # 서비스 정보 매핑
        service_fields = [
            "service_name",
            "service_type",
            "service_description",
            "technology_service_details",
        ]
        for f in service_fields:
            if f in fields and f not in merged["service_info"]:
                merged["service_info"][f] = fields[f]

        # 기술 정보 매핑
        tech_fields = [
            "core_technology",
            "innovation_points",
            "technologies_and_patents",
            "detailed_description",
            "market_status",
        ]
        for f in tech_fields:
            if f in fields and f not in merged["technology_info"]:
                merged["technology_info"][f] = fields[f]

        # 규제 정보 매핑
        regulatory_fields = [
            "regulatory_issues",
            "related_laws",
            "expected_agency",
            "expected_permit",
            "legal_issues",
            "regulation_details",
            "necessity_and_request",
        ]
        for f in regulatory_fields:
            if f in fields and f not in merged["regulatory_info"]:
                merged["regulatory_info"][f] = fields[f]

        # 사업/실증 계획 매핑
        plan_fields = [
            "project_name",
            "period_start",
            "period_end",
            "period_months",
            "objectives_and_scope",
            "business_content",
            "execution_method",
            "schedule",
            "operation_plan",
            "expected_quantitative",
            "expected_qualitative",
            "expansion_plan",
            "restoration_plan",
            "organization_structure",
            "budget",
        ]
        for f in plan_fields:
            if f in fields and f not in merged["business_plan"]:
                merged["business_plan"][f] = fields[f]

        # 안전성 및 이용자 보호 매핑
        safety_fields = [
            "safety_verification",
            "user_protection_plan",
            "risk_and_response",
            "stakeholder_conflict",
            "justification",
            "eligibility_reason_1",
            "eligibility_reason_2",
        ]
        for f in safety_fields:
            if f in fields and f not in merged["safety_and_protection"]:
                merged["safety_and_protection"][f] = fields[f]

    # 빈 딕셔너리 제거
    return {k: v for k, v in merged.items() if v}
