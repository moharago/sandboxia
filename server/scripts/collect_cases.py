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
    """Google Drive에서 데이터 다운로드

    Returns:
        True if download and copy succeeded, False otherwise
    """
    if not R2_DATA_ID:
        print("R2_DATA_ID 환경변수가 설정되지 않았습니다.")
        print("수동으로 data/r2/ 폴더에 파일을 복사하세요:")
        print("  - cases_structured.json")
        print("  - vector_db/ (폴더)")
        return False

    folder_url = f"{GOOGLE_DRIVE_URL}{R2_DATA_ID}"
    print("Google Drive에서 R2 데이터 다운로드 중...")
    print(f"  Folder ID: {R2_DATA_ID}")

    # 임시 디렉토리에 다운로드
    tmp_dir = tempfile.mkdtemp()
    try:
        # gdown.download_folder 반환값 확인
        result = gdown.download_folder(folder_url, output=tmp_dir, quiet=False)

        if result is None:
            print("\n✗ 다운로드 실패: gdown이 None을 반환했습니다.")
            return False

        # 필수 파일 존재 확인
        tmp_path = Path(tmp_dir)
        json_file = None
        vector_db_dir = None

        for item in tmp_path.iterdir():
            if item.name == "cases_structured.json":
                json_file = item
            elif item.name == "vector_db" and item.is_dir():
                vector_db_dir = item

        if not json_file:
            print("\n✗ 다운로드 실패: cases_structured.json 파일을 찾을 수 없습니다.")
            return False

        if not vector_db_dir:
            print("\n✗ 다운로드 실패: vector_db/ 폴더를 찾을 수 없습니다.")
            return False

        # 다운로드된 파일 확인
        downloaded_files = list(tmp_path.rglob("*"))
        print(f"\n다운로드된 파일: {len(downloaded_files)}개")

        # 데이터 디렉토리 생성
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # 파일 복사
        try:
            for item in tmp_path.iterdir():
                dest = DATA_DIR / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                    print(f"  ✓ 폴더 복사: {item.name}")
                else:
                    shutil.copy2(item, dest)
                    print(f"  ✓ 파일 복사: {item.name}")
        except (shutil.Error, OSError, IOError) as e:
            print(f"\n✗ 파일 복사 실패: {e}")
            return False

        return True

    except Exception as e:
        print(f"\n✗ 다운로드 중 오류 발생: {e}")
        return False

    finally:
        # 임시 디렉토리 삭제
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass  # 임시 디렉토리 삭제 실패는 무시


def verify_data():
    """데이터 파일 검증

    Returns:
        True if all data files are valid, False otherwise
    """
    print("\n" + "=" * 60)
    print("데이터 검증")
    print("=" * 60)

    json_path = DATA_DIR / "cases_structured.json"
    vector_db_path = DATA_DIR / "vector_db"

    errors = []

    # JSON 파일 확인
    if json_path.exists():
        try:
            import json
            with open(json_path, "r", encoding="utf-8") as f:
                cases = json.load(f)
            if not isinstance(cases, list) or len(cases) == 0:
                errors.append("✗ cases_structured.json: 유효한 케이스 데이터 없음")
            else:
                print(f"✓ cases_structured.json: {len(cases)}개 케이스")
        except (json.JSONDecodeError, IOError) as e:
            errors.append(f"✗ cases_structured.json 로드 실패: {e}")
    else:
        errors.append("✗ cases_structured.json 없음")

    # Vector DB 확인
    if vector_db_path.exists():
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(vector_db_path))
            collection = client.get_collection(name="sandbox_cases")
            count = collection.count()
            if count == 0:
                errors.append("✗ vector_db: 문서가 없습니다")
            else:
                print(f"✓ vector_db: {count}개 문서")
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
        try:
            response = input("다시 다운로드하시겠습니까? (y/N): ").strip().lower()
        except EOFError:
            response = "n"  # 비대화형 환경에서는 기본값 사용

        if response != "y":
            is_valid = verify_data()
            if is_valid:
                print("\n기존 데이터가 유효합니다.")
            else:
                print("\n⚠️ 기존 데이터에 문제가 있습니다. 다시 다운로드하세요.")
            return

    # 다운로드
    download_success = download_from_drive()

    if not download_success:
        print("\n" + "=" * 60)
        print("✗ 다운로드 실패!")
        print("=" * 60)
        return

    # 검증
    verify_success = verify_data()

    if verify_success:
        print("\n" + "=" * 60)
        print("✓ 다운로드 완료!")
        print(f"저장 위치: {DATA_DIR}")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("⚠️ 다운로드는 완료되었으나 검증에 실패했습니다.")
        print("파일을 확인하세요.")
        print("=" * 60)


if __name__ == "__main__":
    main()
