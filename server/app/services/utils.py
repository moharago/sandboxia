"""서비스 공용 유틸리티"""


def unflatten(data: dict) -> dict:
    """flat 키를 nested 구조로 변환

    예:
    - {"applicant.email": "x"} → {"applicant": {"email": "x"}}
    - {"keyPersonnel.0.name": "a", "keyPersonnel.1.name": "b"}
      → {"keyPersonnel": [{"name": "a"}, {"name": "b"}]}

    숫자 키는 배열 인덱스로 처리합니다.
    """
    result = {}
    for key, value in data.items():
        parts = key.split(".")
        current = result
        for i, part in enumerate(parts[:-1]):
            next_part = parts[i + 1] if i + 1 < len(parts) else None

            # 현재 파트가 숫자면 배열 인덱스
            if part.isdigit():
                idx = int(part)
                # 부모가 리스트인지 확인
                if not isinstance(current, list):
                    # 이 경우는 발생하지 않아야 함 (이전 단계에서 리스트로 설정됨)
                    continue
                # 리스트 길이 확장
                while len(current) <= idx:
                    current.append({})
                current = current[idx]
            else:
                # 다음 파트가 숫자면 현재 파트는 배열
                if next_part and next_part.isdigit():
                    if part not in current:
                        current[part] = []
                    current = current[part]
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

        # 마지막 파트 설정
        last_part = parts[-1]
        if last_part.isdigit():
            idx = int(last_part)
            if isinstance(current, list):
                while len(current) <= idx:
                    current.append(None)
                current[idx] = value
        else:
            if isinstance(current, dict):
                current[last_part] = value

    return result


def is_flat_structure(data: dict) -> bool:
    """flat 구조인지 확인 (키에 . 포함)"""
    return any("." in key for key in data.keys())
