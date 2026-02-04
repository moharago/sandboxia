"""Track Recommender Agent 프롬프트 템플릿"""

# 트랙별 판단 기준 체크리스트
# - 신속확인: 4개 기준
# - 실증특례: 5개 기준
# - 임시허가: 5개 기준
TRACK_CRITERIA = {
    "demo": {  # 실증특례
        "name": "실증특례",
        "criteria": [
            {
                "id": "needs_pilot_test",
                "question": "이 서비스는 실제 환경에서 실증 테스트가 필요한가?",
                "description": "시장 출시 전 제한된 환경에서 테스트가 필요한 경우"
            },
            {
                "id": "safety_unverified",
                "question": "안전성 검증이 아직 완료되지 않았는가?",
                "description": "안전성 인증/시험 데이터가 부족한 경우"
            },
            {
                "id": "limited_scope_possible",
                "question": "제한된 범위(지역, 기간, 대상)에서 실험이 가능한가?",
                "description": "특정 구역이나 조건 하에서 테스트 가능한 경우"
            },
            {
                "id": "regulation_exception_needed",
                "question": "현행 규제의 특례(면제)가 필요한가?",
                "description": "기존 법령을 그대로 적용하면 서비스 제공이 불가능한 경우"
            },
            {
                "id": "similar_demo_cases_exist",
                "question": "유사한 실증특례 승인 사례가 존재하는가?",
                "description": "비슷한 서비스/기술이 실증특례로 승인된 선례가 있는 경우"
            },
        ]
    },
    "temp_permit": {  # 임시허가
        "name": "임시허가",
        "criteria": [
            {
                "id": "safety_verified",
                "question": "안전성 검증이 완료되었는가?",
                "description": "인증, 시험, 실증 결과 등 안전성 데이터를 보유한 경우"
            },
            {
                "id": "no_existing_permit",
                "question": "기존 법령으로는 허가를 받을 수 없는가?",
                "description": "현행 인허가 체계에 맞는 절차가 없는 경우"
            },
            {
                "id": "market_launch_ready",
                "question": "전국 단위 시장 출시가 목적인가?",
                "description": "제한된 실증이 아닌 정식 서비스 출시를 원하는 경우"
            },
            {
                "id": "consumer_protection_plan",
                "question": "소비자 보호 방안이 마련되어 있는가?",
                "description": "이용자 피해 방지, 보상 체계 등이 준비된 경우"
            },
            {
                "id": "similar_temp_cases_exist",
                "question": "유사한 임시허가 승인 사례가 존재하는가?",
                "description": "비슷한 서비스/기술이 임시허가로 승인된 선례가 있는 경우"
            },
        ]
    },
    "quick_check": {  # 신속확인
        "name": "신속확인",
        "criteria": [
            {
                "id": "regulation_unclear",
                "question": "규제 적용 여부가 불명확한가?",
                "description": "허가가 필요한지 아닌지 판단이 어려운 경우"
            },
            {
                "id": "existing_law_applicable",
                "question": "기존 법령 해석만으로 해결 가능한가?",
                "description": "새로운 규제 특례 없이 법령 해석으로 가능한 경우"
            },
            {
                "id": "is_new_technology",
                "question": "신규 기술/서비스에 해당하는가?",
                "description": "기존에 없던 혁신적인 기술이나 서비스인 경우"
            },
            {
                "id": "quick_confirmation_needed",
                "question": "빠른 확인(30일 이내)이 필요한가?",
                "description": "사업 추진을 위해 신속한 규제 확인이 필요한 경우"
            },
        ]
    }
}

# 트랙 스코어링 프롬프트
SCORING_SYSTEM_PROMPT = """당신은 규제 샌드박스 전문 컨설턴트입니다.
주어진 서비스 정보를 분석하여 각 트랙(실증특례/임시허가/신속확인)의 적합도를 판단합니다.

각 질문에 대해 JSON 형식으로 답변하세요:
- answer: true 또는 false
- reason: 판단 근거 (1-2문장)
"""

SCORING_USER_PROMPT = """## 서비스 정보

{service_info}

## 추가 정보 (컨설턴트 메모)

{additional_notes}

## 판단할 트랙: {track_name}

다음 각 질문에 대해 답변하세요:

{criteria_questions}

## 응답 형식 (JSON)

```json
{{
  "criteria_id_1": {{"answer": true/false, "reason": "판단 근거"}},
  "criteria_id_2": {{"answer": true/false, "reason": "판단 근거"}},
  ...
}}
```
"""

# 추천 사유 생성 프롬프트
RECOMMENDATION_SYSTEM_PROMPT = """당신은 규제 샌드박스 전문 컨설턴트입니다.
트랙 점수와 RAG 검색 결과를 바탕으로 추천 사유와 근거를 생성합니다.

트랙별로 정해진 개수의 reasons와 evidence를 생성하세요:
- demo (실증특례): 정확히 5개
- temp_permit (임시허가): 정확히 5개
- quick_check (신속확인): 정확히 4개

reasons[i]와 evidence[i]는 1:1로 매핑됩니다.

## evidence.source 작성 규칙

evidence.source에는 반드시 "사용 가능한 출처 목록"에서 **그대로 복사**하여 사용하세요.
목록에 없는 값을 임의로 만들지 마세요.
설명 문장을 source에 넣지 마세요. 설명은 reasons의 text에 작성합니다.

## evidence.description 작성 규칙

출처가 왜 근거가 되는지 1문장, 30자 이내로 설명하세요.
예시: "실증을 위한 규제특례를 규정하여 신기술 서비스의 제한적 테스트 허용"
"""

RECOMMENDATION_USER_PROMPT = """## 서비스 정보

{service_info}

## 트랙별 점수

{track_scores}

## 트랙 정의/요건 (RAG 검색 결과)

{track_definitions}

## 유사 승인 사례 (RAG 검색 결과)

{similar_cases}

## 사용 가능한 출처 목록

evidence.source에는 **아래 목록의 값만** 사용하세요. 목록에서 복사하여 그대로 붙여넣으세요.

{available_sources}

## 응답 형식 (JSON)

```json
{{
  "demo": {{
    "reasons": [
      {{"type": "positive|negative|neutral", "text": "추천/비추천 사유 설명"}}
    ],
    "evidence": [
      {{"source_type": "사례|법령|규제", "source": "위 출처 목록에서 복사", "description": "출처가 근거가 되는 이유 (30자 이내)"}}
    ]
  }},
  "temp_permit": {{
    "reasons": [5개],
    "evidence": [5개]
  }},
  "quick_check": {{
    "reasons": [4개],
    "evidence": [4개]
  }},
  "result_summary": "2-3문장 요약"
}}
```

## 주의사항

1. **개수 준수**: demo 5개, temp_permit 5개, quick_check 4개 (reasons와 evidence 동일 개수)
2. **1:1 매핑**: reasons[i]의 근거가 evidence[i]
3. **type 값**: "positive", "negative", "neutral" 중 하나
4. **source_type 값**: "사례", "법령", "규제" 중 하나. 세 가지를 골고루 사용하세요
5. **source 값**: 반드시 위 "사용 가능한 출처 목록"에서 선택. 목록에 없는 값 금지
6. **중복 금지**: 한 트랙 내에서 동일한 source를 2번 이상 사용하지 마세요. 매 evidence마다 서로 다른 출처를 선택하세요
"""
