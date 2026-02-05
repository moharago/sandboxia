"""트랙별 폼 스키마 로더

트랙에 따라 적절한 폼 스키마를 로드합니다.
"""

import json
import logging
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

TrackType = Literal["demo", "temp_permit", "quick_check", "counseling"]

# 트랙 → 폼 스키마 파일 매핑
TRACK_TO_SCHEMA_FILE: dict[TrackType, str] = {
    "demo": "demonstration.json",
    "temp_permit": "temporary.json",
    "quick_check": "fastcheck.json",
    "counseling": "counseling.json",
}

# 폼 스키마 디렉토리 경로
FORM_SCHEMA_DIR = Path(__file__).parent.parent.parent / "data" / "form"


def load_form_schema(track: str) -> dict:
    """트랙에 해당하는 폼 스키마 로드

    Args:
        track: 트랙 타입 ("demo" | "temp_permit" | "quick_check" | "counseling")

    Returns:
        폼 스키마 딕셔너리 (formId별 data 구조)

    Raises:
        FileNotFoundError: 스키마 파일이 없는 경우
        ValueError: 지원하지 않는 트랙인 경우
    """
    if track not in TRACK_TO_SCHEMA_FILE:
        raise ValueError(f"지원하지 않는 트랙입니다: {track}")

    schema_file = FORM_SCHEMA_DIR / TRACK_TO_SCHEMA_FILE[track]

    if not schema_file.exists():
        raise FileNotFoundError(f"폼 스키마 파일을 찾을 수 없습니다: {schema_file}")

    with open(schema_file, "r", encoding="utf-8") as f:
        schema = json.load(f)

    logger.debug("폼 스키마 로드 완료: %s (%d개 폼)", track, len(schema))
    return schema


def get_empty_form_structure(track: str) -> dict:
    """트랙의 빈 폼 구조 반환

    폼 스키마에서 키 구조만 추출하여 반환합니다.
    모든 값은 null 상태로 유지됩니다.

    Args:
        track: 트랙 타입

    Returns:
        빈 폼 구조 딕셔너리
    """
    return load_form_schema(track)
