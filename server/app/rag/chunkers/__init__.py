"""청킹 모듈

문서를 벡터 검색에 적합한 청크로 분할하는 로직을 담당합니다.
"""

from app.rag.chunkers.r3_law import LawChunker

__all__ = [
    "LawChunker",
]
