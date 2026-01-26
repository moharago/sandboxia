"""승인 사례 데이터 다운로드 스크립트

R2. 승인 사례 RAG Tool용 데이터 다운로드

데이터 소스:
- 환경변수 R2_DATA_ID가 설정된 경우: Google Drive에서 다운로드
- 미설정 시: 수동으로 data/r2/ 폴더에 파일 복사 필요

필요 파일:
- cases_structured.json: 사례 상세 데이터
- vector_db/: Chroma Vector DB (한국어 임베딩)

실행:
    cd server
    uv run python scripts/collect_cases.py
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import gdown
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv(Path(__file__).parent.parent / ".env")

# 환경변수 읽기
GOOGLE_DRIVE_URL = os.getenv("GOOGLE_DRIVE_URL", "https://drive.google.com/drive/folders/")
R2_DATA_ID = os.getenv("R2_DATA_ID")

# 데이터 저장 경로
DATA_DIR = Path(__file__).parent.parent / "data" / "r2"


def download_from_drive():
    """Google Drive에서 데이터 다운로드"""
    if not R2_DATA_ID:
        print("R2_DATA_ID 환경변수가 설정되지 않았습니다.")
        print("수동으로 data/r2/ 폴더에 파일을 복사하세요:")
        print("  - cases_structured.json")
        print("  - vector_db/ (폴더)")
        return False

    folder_url = f"{GOOGLE_DRIVE_URL}{R2_DATA_ID}"
    print(f"Google Drive에서 R2 데이터 다운로드 중...")
    print(f"  Folder ID: {R2_DATA_ID}")

    # 임시 디렉토리에 다운로드
    tmp_dir = tempfile.mkdtemp()
    try:
        gdown.download_folder(folder_url, output=tmp_dir, quiet=False)

        # 다운로드된 파일 확인
        downloaded_files = list(Path(tmp_dir).rglob("*"))
        print(f"\n다운로드된 파일: {len(downloaded_files)}개")

        # 데이터 디렉토리 생성
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # 파일 복사
        for item in Path(tmp_dir).iterdir():
            dest = DATA_DIR / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
                print(f"  ✓ 폴더 복사: {item.name}")
            else:
                shutil.copy2(item, dest)
                print(f"  ✓ 파일 복사: {item.name}")

        return True

    finally:
        # 임시 디렉토리 삭제
        shutil.rmtree(tmp_dir)


def verify_data():
    """데이터 파일 검증"""
    print("\n" + "=" * 60)
    print("데이터 검증")
    print("=" * 60)

    json_path = DATA_DIR / "cases_structured.json"
    vector_db_path = DATA_DIR / "vector_db"

    errors = []

    # JSON 파일 확인
    if json_path.exists():
        import json
        with open(json_path, "r", encoding="utf-8") as f:
            cases = json.load(f)
        print(f"✓ cases_structured.json: {len(cases)}개 케이스")
    else:
        errors.append("✗ cases_structured.json 없음")

    # Vector DB 확인
    if vector_db_path.exists():
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(vector_db_path))
            collection = client.get_collection(name="sandbox_cases")
            print(f"✓ vector_db: {collection.count()}개 문서")
        except Exception as e:
            errors.append(f"✗ vector_db 로드 실패: {e}")
    else:
        errors.append("✗ vector_db/ 폴더 없음")

    if errors:
        print("\n오류:")
        for err in errors:
            print(f"  {err}")
        return False

    print("\n✓ 데이터 검증 완료!")
    return True


def main():
    print("=" * 60)
    print("R2 승인 사례 데이터 다운로드")
    print("=" * 60)

    # 이미 데이터가 있는지 확인
    json_exists = (DATA_DIR / "cases_structured.json").exists()
    vector_db_exists = (DATA_DIR / "vector_db").exists()

    if json_exists and vector_db_exists:
        print("\n데이터가 이미 존재합니다.")
        response = input("다시 다운로드하시겠습니까? (y/N): ").strip().lower()
        if response != "y":
            verify_data()
            return

    # 다운로드
    success = download_from_drive()

    if success:
        verify_data()
        print("\n" + "=" * 60)
        print("다운로드 완료!")
        print(f"저장 위치: {DATA_DIR}")
        print("=" * 60)


if __name__ == "__main__":
    main()
