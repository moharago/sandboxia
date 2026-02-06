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


def _get_all_keys(obj: dict | list, prefix: str = "") -> set[str]:
    """딕셔너리/리스트에서 모든 키 경로 추출 (재귀)"""
    keys = set()

    if isinstance(obj, dict):
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.add(full_key)
            if isinstance(value, (dict, list)):
                keys.update(_get_all_keys(value, full_key))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, (dict, list)):
                keys.update(_get_all_keys(item, prefix))

    return keys


def validate_schema_keys(generated: dict, schema: dict) -> dict:
    """LLM 생성 결과가 스키마 구조와 일치하는지 검증

    Args:
        generated: LLM이 생성한 폼 데이터
        schema: 원본 폼 스키마

    Returns:
        검증 결과 딕셔너리:
        - valid: bool - 검증 통과 여부
        - unknown_keys: list - 스키마에 없는 키들
        - missing_keys: list - 생성 결과에 없는 키들

    Raises:
        ValueError: 스키마에 없는 키가 발견된 경우
    """
    schema_keys = _get_all_keys(schema)
    generated_keys = _get_all_keys(generated)

    # 스키마에 없는 키 (LLM이 만들어낸 잘못된 경로)
    unknown_keys = generated_keys - schema_keys

    # 생성 결과에 없는 키 (누락된 필드 - 경고용)
    missing_keys = schema_keys - generated_keys

    result = {
        "valid": len(unknown_keys) == 0,
        "unknown_keys": list(unknown_keys),
        "missing_keys": list(missing_keys),
    }

    if unknown_keys:
        logger.error(
            "스키마에 없는 키 발견: %s",
            ", ".join(sorted(unknown_keys)[:10])  # 최대 10개만 로깅
        )

    if missing_keys:
        logger.warning(
            "누락된 키 (정상일 수 있음): %d개",
            len(missing_keys)
        )

    return result
