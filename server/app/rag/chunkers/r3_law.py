"""법령 청킹 모듈 (R3 RAG)

법령 조문을 설정에 따라 청크로 분할합니다.
"""

from langchain_core.documents import Document

from app.rag.chunkers.base import BaseChunker
from app.rag.chunkers.utils import (
    merge_short_chunks,
    para_symbol_to_index,
    split_by_tokens,
)
from app.rag.config import ChunkUnit, MultiGranularity, PrefixType

# =============================================================================
# 법령 전용 유틸리티
# =============================================================================


def format_subparagraphs(subparas: list) -> str:
    """호/목 내용을 텍스트로 포맷팅

    Args:
        subparas: 호 리스트 (API 응답 형식)

    Returns:
        포맷팅된 텍스트
    """
    lines = []
    if not subparas:
        return ""
    if isinstance(subparas, dict):
        subparas = [subparas]

    for subpara in subparas:
        if isinstance(subpara, dict):
            sub_no = subpara.get("호번호", "")
            sub_content = subpara.get("호내용", "")
            if sub_content:
                lines.append(f"  {sub_no}. {sub_content}")
            items = subpara.get("목", [])
            if items:
                if isinstance(items, dict):
                    items = [items]
                for item in items:
                    if isinstance(item, dict):
                        item_no = item.get("목번호", "")
                        item_content = item.get("목내용", "")
                        if item_content:
                            lines.append(f"    {item_no}. {item_content}")
    return "\n".join(lines)


def build_prefix(
    prefix_type: PrefixType,
    law_name: str,
    article_no: str,
    article_title: str = "",
    para_no: str = "",
    subpara_no: str = "",
) -> str:
    """설정에 따른 prefix 생성

    Args:
        prefix_type: prefix 유형
        law_name: 법령명
        article_no: 조 번호
        article_title: 조 제목
        para_no: 항 번호
        subpara_no: 호 번호

    Returns:
        prefix 문자열
    """
    if prefix_type == PrefixType.NONE:
        return ""

    article_ref = f"제{article_no}조"
    if article_title:
        article_ref += f"({article_title})"
    if para_no:
        article_ref += f" {para_no}"
    if subpara_no:
        article_ref += f" 제{subpara_no}호"

    if prefix_type == PrefixType.ARTICLE_ONLY:
        return f"[{article_ref}] "
    elif prefix_type == PrefixType.LAW_AND_ARTICLE:
        return f"[{law_name}] {article_ref}\n"
    return ""


def build_citation(
    law_name: str,
    article_no: str,
    para_no: str = "",
    subpara_no: str = "",
) -> str:
    """인용 형식 생성

    Args:
        law_name: 법령명
        article_no: 조 번호
        para_no: 항 번호
        subpara_no: 호 번호

    Returns:
        인용 문자열 (예: "의료법 제34조 제1항 제2호")
    """
    citation = f"{law_name} 제{article_no}조"
    if para_no:
        citation += f" {para_no}"
    if subpara_no:
        citation += f" 제{subpara_no}호"
    return citation


# =============================================================================
# LawChunker 클래스
# =============================================================================


class LawChunker(BaseChunker):
    """설정 기반 법령 청킹 클래스

    법령 조문을 설정(ChunkingConfig)에 따라 청크로 분할합니다.
    조/항/호 단위 청킹, 멀티 그래뉼러리티, prefix, hybrid 분할 등을 지원합니다.
    """

    def create_chunks(
        self,
        article,
        law_name: str,
        domain: str,
        domain_label: str,
        ministry: str,
        enforcement_date: str,
        mst: str,
    ) -> tuple[list[Document], list[str]]:
        """조문을 설정에 따라 청킹

        Args:
            article: 조문 객체 (article_no, title, content, paragraphs 속성)
            law_name: 법령명
            domain: 도메인 코드
            domain_label: 도메인 라벨
            ministry: 소관부처
            enforcement_date: 시행일자
            mst: 법령 MST 코드

        Returns:
            (documents, doc_ids) 튜플
        """
        documents = []
        doc_ids = []

        article_no = article.article_no
        article_title = article.title or ""

        base_metadata = {
            "source_type": "law",
            "law_name": law_name,
            "law_mst": mst,
            "article_no": article_no,
            "article_title": article_title,
            "domain": domain,
            "domain_label": domain_label,
            "ministry": ministry,
            "enforcement_date": enforcement_date,
            "chunking_config": self.config.name,
        }

        granularities = self.config.multi_granularity or []

        # 조 단위 청킹
        if self.config.chunk_unit == ChunkUnit.ARTICLE or MultiGranularity.ARTICLE in granularities:
            docs, ids = self._create_article_chunks(article, law_name, article_no, article_title, base_metadata, mst)
            documents.extend(docs)
            doc_ids.extend(ids)

        # 항 단위 청킹
        if self.config.chunk_unit == ChunkUnit.PARAGRAPH or MultiGranularity.PARAGRAPH in granularities:
            if article.paragraphs:
                docs, ids = self._create_paragraph_chunks(
                    article, law_name, article_no, article_title, base_metadata, mst
                )
                documents.extend(docs)
                doc_ids.extend(ids)
            elif self.config.chunk_unit == ChunkUnit.PARAGRAPH and MultiGranularity.ARTICLE not in granularities:
                # 항이 없는 경우 조 단위로 fallback (단, multi_granularity에 ARTICLE이 없을 때만)
                docs, ids = self._create_article_chunks(
                    article, law_name, article_no, article_title, base_metadata, mst
                )
                documents.extend(docs)
                doc_ids.extend(ids)

        # 호 단위 청킹
        if MultiGranularity.SUBPARAGRAPH in granularities:
            docs, ids = self._create_subparagraph_chunks(
                article, law_name, article_no, article_title, base_metadata, mst
            )
            documents.extend(docs)
            doc_ids.extend(ids)

        return documents, doc_ids

    def _create_article_chunks(
        self, article, law_name, article_no, article_title, base_metadata, mst
    ) -> tuple[list[Document], list[str]]:
        """조 단위 청킹"""
        documents = []
        doc_ids = []
        content_lines = []

        prefix = build_prefix(self.config.prefix, law_name, article_no, article_title)
        if prefix:
            content_lines.append(prefix)

        article_header = f"제{article_no}조"
        if article_title:
            article_header += f"({article_title})"

        if self.config.prefix == PrefixType.NONE:
            content_lines.append(f"[{law_name}] {article_header}")

        if article.content:
            content_lines.append(article.content)

        if article.paragraphs:
            for para in article.paragraphs:
                para_no = para.get("no", "")
                para_content = para.get("content", "")
                if para_content:
                    content_lines.append(f"{para_no} {para_content}")
                subparas_text = format_subparagraphs(para.get("subparagraphs", []))
                if subparas_text:
                    content_lines.append(subparas_text)

        content = "\n".join(content_lines)

        if not content.strip():
            return documents, doc_ids

        if self.config.hybrid and self.config.max_tokens:
            chunks = split_by_tokens(content, self.config.max_tokens, self.config.overlap)
            if self.config.min_tokens:
                chunks = merge_short_chunks(chunks, self.config.min_tokens)
        else:
            chunks = [content]

        for idx, chunk_content in enumerate(chunks):
            metadata = base_metadata.copy()
            metadata["paragraph_no"] = ""
            metadata["chunk_type"] = "article"
            metadata["citation"] = build_citation(law_name, article_no)

            doc = Document(page_content=chunk_content, metadata=metadata)
            doc_id = f"law_{mst}_{article_no}"
            if len(chunks) > 1:
                doc_id += f"_part{idx + 1}"

            documents.append(doc)
            doc_ids.append(doc_id)

        return documents, doc_ids

    def _create_paragraph_chunks(
        self, article, law_name, article_no, article_title, base_metadata, mst
    ) -> tuple[list[Document], list[str]]:
        """항 단위 청킹"""
        documents = []
        doc_ids = []

        for enum_idx, para in enumerate(article.paragraphs, start=1):
            para_no = para.get("no", "")
            para_content = para.get("content", "")

            if not para_content:
                continue

            content_lines = []

            prefix = build_prefix(self.config.prefix, law_name, article_no, article_title, para_no)
            if prefix:
                content_lines.append(prefix)

            if self.config.prefix == PrefixType.NONE:
                article_header = f"제{article_no}조"
                if article_title:
                    article_header += f"({article_title})"
                content_lines.append(f"[{law_name}] {article_header}")

            content_lines.append(f"{para_no} {para_content}")

            subparas_text = format_subparagraphs(para.get("subparagraphs", []))
            if subparas_text:
                content_lines.append(subparas_text)

            content = "\n".join(content_lines)

            if self.config.hybrid and self.config.max_tokens:
                chunks = split_by_tokens(content, self.config.max_tokens, self.config.overlap)
                if self.config.min_tokens:
                    chunks = merge_short_chunks(chunks, self.config.min_tokens)
            else:
                chunks = [content]

            para_idx = para_symbol_to_index(para_no) or enum_idx

            for chunk_idx, chunk_content in enumerate(chunks):
                metadata = base_metadata.copy()
                metadata["paragraph_no"] = para_no
                metadata["chunk_type"] = "paragraph"
                metadata["citation"] = build_citation(law_name, article_no, para_no)

                doc = Document(page_content=chunk_content, metadata=metadata)
                doc_id = f"law_{mst}_{article_no}_{para_idx}"
                if len(chunks) > 1:
                    doc_id += f"_part{chunk_idx + 1}"

                documents.append(doc)
                doc_ids.append(doc_id)

        return documents, doc_ids

    def _create_subparagraph_chunks(
        self, article, law_name, article_no, article_title, base_metadata, mst
    ) -> tuple[list[Document], list[str]]:
        """호 단위 청킹 (멀티 그래뉼러리티용)"""
        documents = []
        doc_ids = []

        if not article.paragraphs:
            return documents, doc_ids

        for enum_idx, para in enumerate(article.paragraphs, start=1):
            para_no = para.get("no", "")
            subparas = para.get("subparagraphs", [])

            if not subparas:
                continue

            if isinstance(subparas, dict):
                subparas = [subparas]

            para_idx = para_symbol_to_index(para_no) or enum_idx

            for subpara in subparas:
                if not isinstance(subpara, dict):
                    continue

                sub_no = subpara.get("호번호", "")
                sub_content = subpara.get("호내용", "")

                if not sub_content:
                    continue

                content_lines = []

                prefix = build_prefix(
                    self.config.prefix,
                    law_name,
                    article_no,
                    article_title,
                    para_no,
                    sub_no,
                )
                if prefix:
                    content_lines.append(prefix)

                if self.config.prefix == PrefixType.NONE:
                    article_header = f"제{article_no}조"
                    if article_title:
                        article_header += f"({article_title})"
                    content_lines.append(f"[{law_name}] {article_header} {para_no}")

                content_lines.append(f"{sub_no}. {sub_content}")

                items = subpara.get("목", [])
                if items:
                    if isinstance(items, dict):
                        items = [items]
                    for item in items:
                        if isinstance(item, dict):
                            item_no = item.get("목번호", "")
                            item_content = item.get("목내용", "")
                            if item_content:
                                content_lines.append(f"  {item_no}. {item_content}")

                content = "\n".join(content_lines)

                metadata = base_metadata.copy()
                metadata["paragraph_no"] = para_no
                metadata["subparagraph_no"] = sub_no
                metadata["chunk_type"] = "subparagraph"
                metadata["citation"] = build_citation(law_name, article_no, para_no, sub_no)

                doc = Document(page_content=content, metadata=metadata)
                doc_id = f"law_{mst}_{article_no}_{para_idx}_{sub_no}"

                documents.append(doc)
                doc_ids.append(doc_id)

        return documents, doc_ids
