"""법령 데이터 수집 CLI

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

import argparse
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag import list_configs, load_chunking_config, load_embedding_config
from app.rag.collectors import collect_and_store_laws


def main():
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


if __name__ == "__main__":
    main()
