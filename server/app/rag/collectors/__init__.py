"""데이터 수집 모듈

외부 소스에서 데이터를 수집하고 Vector DB에 저장하는 로직을 담당합니다.
"""

from app.rag.collectors.r3_law import (
    DOMAIN_LABELS,
    TARGET_LAWS,
    collect_and_store_laws,
)

__all__ = [
    "collect_and_store_laws",
    "TARGET_LAWS",
    "DOMAIN_LABELS",
]
