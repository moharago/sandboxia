"""청킹 공통 유틸리티

토큰 계산, 텍스트 분할/병합 등 청킹에 필요한 공통 함수들.
"""

import re

import tiktoken

# tiktoken 인코더 (토큰 수 계산용)
_encoder = tiktoken.encoding_for_model("gpt-4o")


def count_tokens(text: str) -> int:
    """텍스트의 토큰 수 계산

    Args:
        text: 토큰 수를 계산할 텍스트

    Returns:
        토큰 수
    """
    return len(_encoder.encode(text))


def split_by_tokens(text: str, max_tokens: int, overlap: int = 0) -> list[str]:
    """텍스트를 토큰 기준으로 분할

    Args:
        text: 분할할 텍스트
        max_tokens: 청크당 최대 토큰 수
        overlap: 인접 청크 간 겹치는 토큰 수

    Returns:
        분할된 텍스트 리스트

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
    """짧은 청크들을 병합

    Args:
        chunks: 청크 리스트
        min_tokens: 최소 토큰 수

    Returns:
        병합된 청크 리스트
    """
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


def para_symbol_to_index(para_no: str) -> int:
    """항 기호(①②③...)를 숫자 인덱스로 변환

    Args:
        para_no: 항 번호 문자열 (예: "①", "제1항")

    Returns:
        숫자 인덱스 (1부터 시작), 변환 실패 시 0
    """
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
