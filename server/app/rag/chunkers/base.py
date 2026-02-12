"""청킹 베이스 클래스

새로운 도메인(R1, R2 등)의 청킹 로직 추가 시 이 클래스를 상속합니다.
"""

from abc import ABC, abstractmethod

from langchain_core.documents import Document

from app.rag.config import ChunkingConfig


class BaseChunker(ABC):
    """청킹 베이스 클래스"""

    def __init__(self, config: ChunkingConfig):
        self.config = config

    @abstractmethod
    def create_chunks(self, source: any, **kwargs) -> tuple[list[Document], list[str]]:
        """소스 데이터를 청크로 분할

        Args:
            source: 청킹할 소스 데이터
            **kwargs: 추가 메타데이터

        Returns:
            (documents, doc_ids) 튜플
        """
        pass

    @property
    def config_name(self) -> str:
        """설정 이름 반환"""
        return self.config.name
