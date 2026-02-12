"""법령 데이터 수집 및 Vector DB 저장 스크립트 (설정 기반 청킹 & 임베딩)

대상 법령:
- 의료법
- 전자금융거래법
- 데이터기본법 (데이터 산업진흥 및 이용촉진에 관한 기본법)
- 신용정보법 (신용정보의 이용 및 보호에 관한 법률)
- 개인정보보호법 (개인정보 보호법)
- 전기통신사업법
- ICT특별법 (정보통신 진흥 및 융합 활성화 등에 관한 특별법)
- 산업융합 촉진법
- 금융혁신지원 특별법
- 지역특구법 (규제자유특구 및 지역특화발전특구에 관한 규제특례법)
- 행정규제기본법

실행:
    cd server

    # 기본 실행 (C0 청킹, .env 임베딩 모델)
    uv run python scripts/collect_laws.py

    # 청킹 설정 변경 (C*)
    uv run python scripts/collect_laws.py --config C3 --reset

    # 임베딩 설정 변경 (E*) - 청킹은 C0 기본값 사용
    uv run python scripts/collect_laws.py --config E1 --reset

    # 청킹 + 임베딩 조합 (C* E*)
    uv run python scripts/collect_laws.py --config C3 E1 --reset

    # 사용 가능한 설정 목록 확인
    uv run python scripts/collect_laws.py --list-configs

    # 청크 JSON 내보내기 (평가용)
    uv run python scripts/collect_laws.py --config C1 --export-chunks
"""

import asyncio
import json
import re
import sys
from enum import Enum
from pathlib import Path

import tiktoken
import yaml
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from pydantic import BaseModel, Field, model_validator

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.constants import COLLECTION_LAWS
from app.db.export import save_chunks_json
from app.services.law_api import law_api_client

# =============================================================================
# 임베딩 설정 스키마
# =============================================================================


class EmbeddingConfig(BaseModel):
    """임베딩 모델 설정"""

    name: str = Field(description="설정 이름 (예: E0, E1)")
    description: str = Field(default="", description="설정 설명")
    model: str = Field(description="임베딩 모델 이름")
    provider: str = Field(default="openai", description="제공자 (openai, upstage, local)")
    dimension: int = Field(description="임베딩 벡터 차원")
    max_tokens: int = Field(default=8192, description="최대 입력 토큰 수")
    cost_per_1m_tokens: float = Field(default=0.0, description="100만 토큰당 비용 (USD)")


# =============================================================================
# 청킹 설정 스키마
# =============================================================================


class ChunkUnit(str, Enum):
    """청킹 기본 단위"""

    ARTICLE = "article"  # 조
    PARAGRAPH = "paragraph"  # 항


class MultiGranularity(str, Enum):
    """멀티 그래뉼러리티 단위"""

    ARTICLE = "article"  # 조
    PARAGRAPH = "paragraph"  # 항
    SUBPARAGRAPH = "subparagraph"  # 호


class PrefixType(str, Enum):
    """prefix 유형"""

    NONE = "none"  # 없음
    ARTICLE_ONLY = "article_only"  # 조항호만 (예: 제34조 제1항)
    LAW_AND_ARTICLE = "law_and_article"  # 법령명+조항호 (예: [의료법] 제34조 제1항)


class ChunkingConfig(BaseModel):
    """청킹 전략 설정"""

    name: str = Field(description="설정 이름 (예: C0, C1)")
    description: str = Field(default="", description="설정 설명")

    chunk_unit: ChunkUnit = Field(
        default=ChunkUnit.PARAGRAPH,
        description="기본 청킹 단위 (article: 조, paragraph: 항)",
    )
    multi_granularity: list[MultiGranularity] = Field(
        default_factory=list,
        description="동시 인덱싱할 단위들 (빈 리스트면 단일 단위만)",
    )
    prefix: PrefixType = Field(
        default=PrefixType.NONE,
        description="chunk 앞에 붙일 구조 정보",
    )
    top_k: int = Field(default=5, description="검색 시 반환할 chunk 수")
    hybrid: bool = Field(
        default=False,
        description="토큰 기준 추가 분할/병합 활성화",
    )
    min_tokens: int | None = Field(
        default=None,
        description="chunk 최소 토큰 수 (hybrid=True일 때)",
    )
    max_tokens: int | None = Field(
        default=None,
        description="chunk 최대 토큰 수 (hybrid=True일 때)",
    )
    overlap: int = Field(
        default=0,
        description="인접 chunk 간 겹치는 토큰 수",
    )

    @model_validator(mode="after")
    def validate_overlap(self) -> "ChunkingConfig":
        """overlap이 max_tokens보다 작은지 검증"""
        if self.overlap < 0:
            raise ValueError(f"overlap은 0 이상이어야 합니다: {self.overlap}")
        if self.max_tokens is not None and self.overlap >= self.max_tokens:
            raise ValueError(f"overlap({self.overlap})은 max_tokens({self.max_tokens})보다 작아야 합니다")
        return self


# 설정 파일 경로
CHUNKING_PRESETS_FILE = Path(__file__).parent.parent / "eval" / "r3" / "configs" / "chunking.yaml"
EMBEDDING_PRESETS_FILE = Path(__file__).parent.parent / "eval" / "r3" / "configs" / "embedding.yaml"


def _load_chunking_presets() -> dict:
    """chunking.yaml에서 모든 청킹 설정 로드"""
    if not CHUNKING_PRESETS_FILE.exists():
        return {}
    with open(CHUNKING_PRESETS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_embedding_presets() -> dict:
    """embedding.yaml에서 모든 임베딩 설정 로드"""
    if not EMBEDDING_PRESETS_FILE.exists():
        return {}
    with open(EMBEDDING_PRESETS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_chunking_config(config_name: str) -> ChunkingConfig:
    """청킹 설정 로드"""
    presets = _load_chunking_presets()
    if config_name not in presets:
        available = list(presets.keys())
        raise FileNotFoundError(f"청킹 설정 '{config_name}'을 찾을 수 없습니다. 사용 가능: {available}")
    return ChunkingConfig(**presets[config_name])


def load_embedding_config(config_name: str) -> EmbeddingConfig:
    """임베딩 설정 로드"""
    presets = _load_embedding_presets()
    if config_name not in presets:
        available = list(presets.keys())
        raise FileNotFoundError(f"임베딩 설정 '{config_name}'을 찾을 수 없습니다. 사용 가능: {available}")
    return EmbeddingConfig(**presets[config_name])


def load_config(config_name: str) -> ChunkingConfig | EmbeddingConfig:
    """설정 이름에 따라 청킹(C*) 또는 임베딩(E*) 설정 로드"""
    if config_name.startswith("E"):
        return load_embedding_config(config_name)
    return load_chunking_config(config_name)


def list_configs() -> dict[str, list[str]]:
    """사용 가능한 설정 목록 반환"""
    chunking_presets = _load_chunking_presets()
    embedding_presets = _load_embedding_presets()
    return {
        "chunking": sorted(chunking_presets.keys()),
        "embedding": sorted(embedding_presets.keys()),
    }


# =============================================================================
# 청킹 유틸리티 함수
# =============================================================================

# tiktoken 인코더 (토큰 수 계산용)
_encoder = tiktoken.encoding_for_model("gpt-4o")


def count_tokens(text: str) -> int:
    """텍스트의 토큰 수 계산"""
    return len(_encoder.encode(text))


def para_symbol_to_index(para_no: str) -> int:
    """항 기호(①②③...)를 숫자 인덱스로 변환"""
    if not para_no:
        return 0

    symbols = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
    normalized = para_no.strip().rstrip("항., ")

    if normalized in symbols:
        return symbols.index(normalized) + 1
    if normalized and normalized[0] in symbols:
        return symbols.index(normalized[0]) + 1
    try:
        match = re.match(r"(\d+)", normalized)
        if match:
            return int(match.group(1))
    except ValueError:
        pass
    return 0


def format_subparagraphs(subparas: list) -> str:
    """호/목 내용을 텍스트로 포맷팅"""
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
    """설정에 따른 prefix 생성"""
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
    """인용 형식 생성 (예: 의료법 제34조 제1항 제2호)"""
    citation = f"{law_name} 제{article_no}조"
    if para_no:
        citation += f" {para_no}"
    if subpara_no:
        citation += f" 제{subpara_no}호"
    return citation


def split_by_tokens(text: str, max_tokens: int, overlap: int = 0) -> list[str]:
    """텍스트를 토큰 기준으로 분할

    Args:
        text: 분할할 텍스트
        max_tokens: 청크당 최대 토큰 수
        overlap: 인접 청크 간 겹치는 토큰 수

    Raises:
        ValueError: overlap >= max_tokens이거나 음수인 경우
    """
    if overlap < 0:
        raise ValueError(f"overlap은 0 이상이어야 합니다: {overlap}")
    if overlap >= max_tokens:
        raise ValueError(f"overlap({overlap})은 max_tokens({max_tokens})보다 작아야 합니다")

    tokens = _encoder.encode(text)
    if len(tokens) <= max_tokens:
        return [text]

    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(_encoder.decode(chunk_tokens))
        start = end - overlap if overlap > 0 else end
    return chunks


def merge_short_chunks(chunks: list[str], min_tokens: int) -> list[str]:
    """짧은 청크들을 병합"""
    if not chunks:
        return chunks

    merged = []
    current = chunks[0]

    for chunk in chunks[1:]:
        if count_tokens(current) < min_tokens:
            current = current + "\n" + chunk
        else:
            merged.append(current)
            current = chunk

    merged.append(current)
    return merged


# =============================================================================
# LawChunker 클래스
# =============================================================================


class LawChunker:
    """설정 기반 법령 청킹 클래스"""

    def __init__(self, config: ChunkingConfig):
        self.config = config

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
        """조문을 설정에 따라 청킹"""
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


# =============================================================================
# 수집 대상 법령
# =============================================================================

TARGET_LAWS = [
    ("의료법", "healthcare"),
    ("전자금융거래법", "finance"),
    ("데이터 산업진흥 및 이용촉진에 관한 기본법", "data"),
    ("신용정보의 이용 및 보호에 관한 법률", "finance"),
    ("개인정보 보호법", "privacy"),
    ("전기통신사업법", "telecom"),
    ("정보통신 진흥 및 융합 활성화 등에 관한 특별법", "telecom"),
    ("산업융합 촉진법", "regulation"),
    ("금융혁신지원 특별법", "regulation"),
    ("규제자유특구 및 지역특화발전특구에 관한 규제특례법", "regulation"),
    ("행정규제기본법", "regulation"),
]

DOMAIN_LABELS = {
    "healthcare": "의료/헬스케어",
    "finance": "금융",
    "data": "데이터",
    "privacy": "개인정보",
    "telecom": "통신/ICT",
    "regulation": "규제/제도",
}


# =============================================================================
# 메인 수집 함수
# =============================================================================


async def collect_and_store_laws(
    config: ChunkingConfig,
    export_chunks: bool = False,
    collection_suffix: str = "",
    reset: bool = False,
    embedding_config: EmbeddingConfig | None = None,
):
    """법령 데이터 수집 및 Vector DB 저장 (설정 기반 청킹)

    Args:
        config: 청킹 설정
        export_chunks: 청크 JSON 내보내기 여부
        collection_suffix: 컬렉션 이름에 붙일 접미사
        reset: 기존 컬렉션 삭제 후 새로 생성 여부
        embedding_config: 임베딩 설정 (None이면 .env의 LLM_EMBEDDING_MODEL 사용)
    """

    print("=" * 60)
    print("법령 데이터 수집 시작")
    print(f"청킹 설정: {config.name} - {config.description}")
    print("=" * 60)

    print("\n[청킹 설정]")
    print(f"  - 청킹 단위: {config.chunk_unit.value}")
    print(f"  - 멀티 그래뉼러리티: {[g.value for g in config.multi_granularity] or '없음'}")
    print(f"  - prefix: {config.prefix.value}")
    print(f"  - hybrid: {config.hybrid}")
    if config.hybrid:
        print(f"  - min/max tokens: {config.min_tokens} / {config.max_tokens}")
    print(f"  - overlap: {config.overlap}")
    print(f"  - top_k: {config.top_k}")

    # 임베딩 모델 결정
    if embedding_config:
        embedding_model = embedding_config.model
        print(f"\n[임베딩 설정] {embedding_config.name} - {embedding_config.description}")
        print(f"  - 모델: {embedding_config.model}")
        print(f"  - 제공자: {embedding_config.provider}")
        print(f"  - 차원: {embedding_config.dimension}")

        if embedding_config.provider == "local":
            print("  ⚠️  로컬 모델은 아직 지원되지 않습니다. OpenAI API를 사용합니다.")
            embedding_model = settings.LLM_EMBEDDING_MODEL
    else:
        embedding_model = settings.LLM_EMBEDDING_MODEL
        print(f"\n[임베딩 설정] .env 기본값 사용: {embedding_model}")

    chunker = LawChunker(config)

    embeddings = OpenAIEmbeddings(
        model=embedding_model,
        api_key=settings.OPENAI_API_KEY,  # type: ignore[arg-type]
    )

    persist_dir = Path(settings.CHROMA_PERSIST_DIR)
    persist_dir.mkdir(parents=True, exist_ok=True)

    collection_name = COLLECTION_LAWS + collection_suffix

    # 기존 컬렉션 삭제 (reset 옵션)
    if reset:
        import chromadb

        print(f"\n[컬렉션 초기화] '{collection_name}' 삭제 중...")
        client = chromadb.PersistentClient(path=str(persist_dir))
        try:
            client.delete_collection(name=collection_name)
            print("  ✓ 기존 컬렉션 삭제 완료")
        except ValueError:
            print("  - 기존 컬렉션 없음 (새로 생성)")

    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )

    documents = []
    document_ids = []
    seen_ids: set[str] = set()
    collected_laws = []

    for law_name, domain in TARGET_LAWS:
        print(f"\n[{law_name}] 검색 중...")

        law_summary = await law_api_client.search_law_by_name(law_name)
        if not law_summary:
            print(f"  ⚠️  '{law_name}' 법령을 찾을 수 없습니다.")
            continue

        print(f"  [OK] 발견: {law_summary.name} (MST: {law_summary.mst})")
        print(f"    - 소관부처: {law_summary.ministry}")
        print(f"    - 시행일자: {law_summary.enforcement_date}")

        law_detail = await law_api_client.get_law_detail(law_summary.mst)
        if not law_detail:
            print("  ⚠️  본문 조회 실패")
            continue

        print(f"  [OK] 조문 수: {len(law_detail.articles)}개")

        law_doc_count = 0
        for article in law_detail.articles:
            article_docs, article_ids = chunker.create_chunks(
                article=article,
                law_name=law_detail.name,
                domain=domain,
                domain_label=DOMAIN_LABELS.get(domain, domain),
                ministry=law_detail.ministry,
                enforcement_date=law_detail.enforcement_date,
                mst=law_summary.mst,
            )
            documents.extend(article_docs)
            document_ids.extend(article_ids)
            law_doc_count += len(article_docs)

        print(f"  [OK] 생성된 청크: {law_doc_count}개")

        collected_laws.append(
            {
                "name": law_detail.name,
                "mst": law_summary.mst,
                "domain": domain,
                "article_count": len(law_detail.articles),
                "chunk_count": law_doc_count,
            }
        )

    if not documents:
        print("\n⚠️  수집된 문서가 없습니다.")
        return

    # 중복 ID 해결
    unique_ids = []
    duplicate_count = 0
    for doc_id in document_ids:
        if doc_id in seen_ids:
            duplicate_count += 1
            suffix = 1
            new_id = f"{doc_id}_{suffix}"
            while new_id in seen_ids:
                suffix += 1
                new_id = f"{doc_id}_{suffix}"
            doc_id = new_id
        seen_ids.add(doc_id)
        unique_ids.append(doc_id)

    if duplicate_count > 0:
        print(f"\n⚠️  중복 ID {duplicate_count}개 발견 → suffix 추가로 해결")

    print(f"\n{'=' * 60}")
    print(f"총 {len(documents)}개 문서 생성 완료")
    print("Vector DB에 저장 중...")

    # 배치 크기 제한 (ChromaDB max batch size: 5461)
    batch_size = 5000
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i : i + batch_size]
        batch_ids = unique_ids[i : i + batch_size]
        vectorstore.add_documents(batch_docs, ids=batch_ids)
        print(f"  - 배치 {i // batch_size + 1}: {len(batch_docs)}개 저장 완료")

    print("[OK] Vector DB 저장 완료!")
    print(f"  - 컬렉션: {collection_name}")

    if export_chunks:
        chunks_dir = Path(__file__).parent.parent / "data" / "r3_data"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        chunks_json_path = chunks_dir / f"chunks_{config.name}.json"
        saved_count = save_chunks_json(documents, unique_ids, chunks_json_path)
        print(f"[OK] 청크 JSON 저장 완료: {chunks_json_path} ({saved_count}개)")

    result_file = persist_dir / "r3_collection_info.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "config": {
                    "name": config.name,
                    "description": config.description,
                    "chunk_unit": config.chunk_unit.value,
                    "multi_granularity": [g.value for g in config.multi_granularity],
                    "prefix": config.prefix.value,
                    "hybrid": config.hybrid,
                    "min_tokens": config.min_tokens,
                    "max_tokens": config.max_tokens,
                    "overlap": config.overlap,
                    "top_k": config.top_k,
                },
                "total_documents": len(documents),
                "laws": collected_laws,
                "domains": list(DOMAIN_LABELS.keys()),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n수집 정보 저장: {result_file}")
    print("\n" + "=" * 60)
    print("수집 완료 요약:")
    print("=" * 60)
    for law in collected_laws:
        print(f"  - {law['name']}: {law['article_count']}개 조문 → {law['chunk_count']}개 청크 ({law['domain']})")
    print(f"\n총 청크 수: {len(documents)}개")
    print(f"저장 위치: {persist_dir}")


# =============================================================================
# CLI 엔트리포인트
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="법령 데이터 수집 및 Vector DB 저장",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 기본 실행 (C0 청킹, .env 임베딩 모델)
  uv run python scripts/collect_laws.py

  # 청킹 설정 변경
  uv run python scripts/collect_laws.py --config C3 --reset

  # 임베딩 설정 변경 (청킹은 C0 기본값 사용)
  uv run python scripts/collect_laws.py --config E1 --reset

  # 청킹 + 임베딩 조합
  uv run python scripts/collect_laws.py --config C3 E1 --reset

  # 사용 가능한 설정 목록 확인
  uv run python scripts/collect_laws.py --list-configs
        """,
    )
    parser.add_argument(
        "--config",
        type=str,
        nargs="+",
        default=["C0"],
        help="설정 이름. C*: 청킹, E*: 임베딩. 조합 가능 (예: C3 E1)",
    )
    parser.add_argument(
        "--list-configs",
        action="store_true",
        help="사용 가능한 설정 목록 출력",
    )
    parser.add_argument(
        "--export-chunks",
        action="store_true",
        help="청크 JSON도 함께 저장 (평가셋 작성용)",
    )
    parser.add_argument(
        "--collection-suffix",
        type=str,
        default="",
        help="컬렉션 이름에 붙일 접미사 (예: _C1)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="기존 컬렉션 삭제 후 새로 생성 (프리셋 변경 시 권장)",
    )
    args = parser.parse_args()

    if args.list_configs:
        all_configs = list_configs()
        print("사용 가능한 청킹 설정 (C*):")
        for config_name in all_configs["chunking"]:
            try:
                cfg = load_chunking_config(config_name)
                print(f"  - {config_name}: {cfg.description}")
            except Exception as e:
                print(f"  - {config_name}: (로드 실패: {e})")

        print("\n사용 가능한 임베딩 설정 (E*):")
        for config_name in all_configs["embedding"]:
            try:
                cfg = load_embedding_config(config_name)
                print(f"  - {config_name}: {cfg.description} ({cfg.model})")
            except Exception as e:
                print(f"  - {config_name}: (로드 실패: {e})")
        sys.exit(0)

    # 설정 파싱: C*는 청킹, E*는 임베딩
    chunking_config = None
    embedding_config = None

    for cfg_name in args.config:
        cfg_name = cfg_name.upper()  # 대소문자 무시
        if cfg_name.startswith("E"):
            try:
                embedding_config = load_embedding_config(cfg_name)
            except FileNotFoundError as e:
                print(f"오류: {e}")
                all_configs = list_configs()
                print(f"사용 가능한 임베딩 설정: {all_configs['embedding']}")
                sys.exit(1)
        elif cfg_name.startswith("C"):
            try:
                chunking_config = load_chunking_config(cfg_name)
            except FileNotFoundError as e:
                print(f"오류: {e}")
                all_configs = list_configs()
                print(f"사용 가능한 청킹 설정: {all_configs['chunking']}")
                sys.exit(1)
        else:
            print(f"오류: 알 수 없는 설정 '{cfg_name}'. C* 또는 E*로 시작해야 합니다.")
            sys.exit(1)

    # 청킹 설정 기본값
    if chunking_config is None:
        chunking_config = load_chunking_config("C0")

    asyncio.run(
        collect_and_store_laws(
            config=chunking_config,
            export_chunks=args.export_chunks,
            collection_suffix=args.collection_suffix,
            reset=args.reset,
            embedding_config=embedding_config,
        )
    )
