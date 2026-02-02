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

각 트랙에 대해 3-5개의 reasons와 대응하는 evidence를 생성하세요.
reasons[i]와 evidence[i]는 1:1로 매핑됩니다.
"""

RECOMMENDATION_USER_PROMPT = """## 서비스 정보

{service_info}

## 트랙별 점수

{track_scores}

## 트랙 정의/요건 (RAG 검색 결과)

{track_definitions}

## 유사 승인 사례 (RAG 검색 결과)

{similar_cases}

## 응답 형식 (JSON)

각 트랙(demo, temp_permit, quick_check)에 대해 다음 형식으로 응답하세요:

```json
{{
  "demo": {{
    "reasons": [
      {{"type": "positive", "text": "긍정적 이유..."}},
      {{"type": "negative", "text": "부정적 이유..."}},
      {{"type": "neutral", "text": "중립적 참고사항..."}}
    ],
    "evidence": [
      {{"source_type": "사례", "source": "실증특례 제2023-ICT융합-0147호"}},
      {{"source_type": "법령", "source": "「정보통신융합법」 제38조의2"}},
      {{"source_type": "규제", "source": "ICT 규제샌드박스 운영지침 제5조"}}
    ]
  }},
  "temp_permit": {{ ... }},
  "quick_check": {{ ... }},
  "result_summary": "서비스 특성과 규제 현황을 분석한 결과, ... (2-3문장 요약)"
}}
```

주의사항:
- reasons의 개수와 evidence의 개수는 반드시 동일해야 합니다
- reasons[i]의 근거가 evidence[i]입니다
- type은 "positive", "negative", "neutral" 중 하나입니다
- source_type은 "법령", "사례", "규제" 중 하나입니다
"""
