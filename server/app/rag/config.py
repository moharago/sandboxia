"""RAG 설정 스키마 및 로더

청킹 전략(C0~Cn)과 임베딩 모델(E0~En) 설정을 관리합니다.
설정 파일 위치: eval/{rag_type}/configs/
"""

from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

# =============================================================================
# 임베딩 설정 스키마
# =============================================================================


class EmbeddingConfig(BaseModel):
    """임베딩 모델 설정 (Dense Embedding)"""

    name: str = Field(description="설정 이름 (예: E0, E1)")
    description: str = Field(default="", description="설정 설명")
    model: str = Field(description="임베딩 모델 이름")
    provider: str = Field(default="openai", description="제공자 (openai, upstage, local)")
    dimension: int = Field(description="임베딩 벡터 차원")
    max_tokens: int = Field(default=8192, description="최대 입력 토큰 수")
    cost_per_1m_tokens: float = Field(default=0.0, description="100만 토큰당 비용 (USD)")


class HybridConfig(BaseModel):
    """Hybrid Search 설정 (Qdrant 전용)

    Dense + Sparse 검색 결합 설정.
    alpha: Dense 가중치 (1.0=Dense만, 0.0=Sparse만)
    """

    name: str = Field(description="설정 이름 (예: H0, H1)")
    description: str = Field(default="", description="설정 설명")
    sparse_model: str = Field(
        default="naver/splade-cocondenser-ensembledistil",
        description="Sparse 임베딩 모델 (SPLADE, BM25 등)",
    )
    alpha: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Dense 가중치 (0.0~1.0, 0.7=Dense 70%)",
    )
    note: str = Field(default="", description="참고 사항")


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


# =============================================================================
# 설정 파일 경로
# =============================================================================

# 프로젝트 루트 기준 설정 파일 경로
_PROJECT_ROOT = Path(__file__).parent.parent.parent  # server/
_CONFIGS_BASE = _PROJECT_ROOT / "eval"


def _get_config_paths(rag_type: str = "r3") -> tuple[Path, Path, Path]:
    """RAG 타입별 설정 파일 경로 반환"""
    config_dir = _CONFIGS_BASE / rag_type / "configs"
    return (
        config_dir / "chunking.yaml",
        config_dir / "embedding.yaml",
        config_dir / "hybrid.yaml",
    )


# =============================================================================
# 설정 로더
# =============================================================================


def _load_yaml(file_path: Path) -> dict:
    """YAML 파일 로드"""
    if not file_path.exists():
        return {}
    with open(file_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_chunking_presets(rag_type: str = "r3") -> dict:
    """청킹 프리셋 로드"""
    chunking_path, _, _ = _get_config_paths(rag_type)
    return _load_yaml(chunking_path)


def _load_embedding_presets(rag_type: str = "r3") -> dict:
    """임베딩 프리셋 로드"""
    _, embedding_path, _ = _get_config_paths(rag_type)
    return _load_yaml(embedding_path)


def _load_hybrid_presets(rag_type: str = "r3") -> dict:
    """Hybrid Search 프리셋 로드"""
    _, _, hybrid_path = _get_config_paths(rag_type)
    return _load_yaml(hybrid_path)


def load_chunking_config(config_name: str, rag_type: str = "r3") -> ChunkingConfig:
    """청킹 설정 로드

    Args:
        config_name: 설정 이름 (예: C0, C1)
        rag_type: RAG 타입 (r1, r2, r3)

    Returns:
        ChunkingConfig 인스턴스

    Raises:
        FileNotFoundError: 설정을 찾을 수 없을 때
    """
    presets = _load_chunking_presets(rag_type)
    if config_name not in presets:
        available = list(presets.keys())
        raise FileNotFoundError(f"청킹 설정 '{config_name}'을 찾을 수 없습니다. 사용 가능: {available}")
    return ChunkingConfig(**presets[config_name])


def load_embedding_config(config_name: str, rag_type: str = "r3") -> EmbeddingConfig:
    """임베딩 설정 로드

    Args:
        config_name: 설정 이름 (예: E0, E1)
        rag_type: RAG 타입 (r1, r2, r3)

    Returns:
        EmbeddingConfig 인스턴스

    Raises:
        FileNotFoundError: 설정을 찾을 수 없을 때
    """
    presets = _load_embedding_presets(rag_type)
    if config_name not in presets:
        available = list(presets.keys())
        raise FileNotFoundError(f"임베딩 설정 '{config_name}'을 찾을 수 없습니다. 사용 가능: {available}")
    return EmbeddingConfig(**presets[config_name])


def load_hybrid_config(config_name: str, rag_type: str = "r3") -> HybridConfig:
    """Hybrid Search 설정 로드

    Args:
        config_name: 설정 이름 (예: H0, H1)
        rag_type: RAG 타입 (r1, r2, r3)

    Returns:
        HybridConfig 인스턴스

    Raises:
        FileNotFoundError: 설정을 찾을 수 없을 때
    """
    presets = _load_hybrid_presets(rag_type)
    if config_name not in presets:
        available = list(presets.keys())
        raise FileNotFoundError(f"Hybrid 설정 '{config_name}'을 찾을 수 없습니다. 사용 가능: {available}")
    return HybridConfig(**presets[config_name])


def load_config(config_name: str, rag_type: str = "r3") -> ChunkingConfig | EmbeddingConfig | HybridConfig:
    """설정 이름에 따라 청킹(C*), 임베딩(E*), 또는 Hybrid(H*) 설정 로드

    Args:
        config_name: 설정 이름 (C*는 청킹, E*는 임베딩, H*는 Hybrid)
        rag_type: RAG 타입 (r1, r2, r3)

    Returns:
        ChunkingConfig, EmbeddingConfig, 또는 HybridConfig 인스턴스
    """
    upper_name = config_name.upper()
    if upper_name.startswith("E"):
        return load_embedding_config(upper_name, rag_type)
    if upper_name.startswith("H"):
        return load_hybrid_config(upper_name, rag_type)
    return load_chunking_config(upper_name, rag_type)


def list_configs(rag_type: str = "r3") -> dict[str, list[str]]:
    """사용 가능한 설정 목록 반환

    Args:
        rag_type: RAG 타입 (r1, r2, r3)

    Returns:
        {"chunking": [...], "embedding": [...], "hybrid": [...]}
    """
    chunking_presets = _load_chunking_presets(rag_type)
    embedding_presets = _load_embedding_presets(rag_type)
    hybrid_presets = _load_hybrid_presets(rag_type)
    return {
        "chunking": sorted(chunking_presets.keys()),
        "embedding": sorted(embedding_presets.keys()),
        "hybrid": sorted(hybrid_presets.keys()),
    }
