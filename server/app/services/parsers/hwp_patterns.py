"""HWP 문서 유형별 필드 추출 패턴

11가지 HWP 문서 유형에 대한 필드 추출 패턴을 정의합니다.

문서 유형:
1. 상담신청 (counseling): 1개 - (양식)_로 시작
2. 신속확인 (fastcheck): 2개 - 01-로 시작
3. 임시허가 (temporary): 4개 - 02-로 시작
4. 실증특례 (demonstration): 4개 - 03-로 시작
"""

from enum import Enum


class DocumentCategory(str, Enum):
    """문서 카테고리 (신청 유형)"""

    COUNSELING = "counseling"  # 상담신청
    FASTCHECK = "fastcheck"  # 신속확인
    TEMPORARY = "temporary"  # 임시허가
    DEMONSTRATION = "demonstration"  # 실증특례
    UNKNOWN = "unknown"


class DocumentSubtype(str, Enum):
    """문서 서브타입 (카테고리 내 문서 종류)"""

    # 상담신청
    COUNSELING_APPLICATION = "counseling-1"  # 사전상담 신청서

    # 신속확인
    FASTCHECK_APPLICATION = "fastcheck-1"  # 신속확인 신청서
    FASTCHECK_DESCRIPTION = "fastcheck-2"  # 기술·서비스 설명서

    # 임시허가
    TEMPORARY_APPLICATION = "temporary-1"  # 임시허가 신청서
    TEMPORARY_BUSINESS_PLAN = "temporary-2"  # 사업계획서
    TEMPORARY_JUSTIFICATION = "temporary-3"  # 신청사유 소명서
    TEMPORARY_SAFETY = "temporary-4"  # 안전성검증자료 및 이용자보호방안

    # 실증특례
    DEMONSTRATION_APPLICATION = "demonstration-1"  # 규제특례 신청서
    DEMONSTRATION_PLAN = "demonstration-2"  # 실증계획서
    DEMONSTRATION_JUSTIFICATION = "demonstration-3"  # 신청사유 소명서
    DEMONSTRATION_PROTECTION = "demonstration-4"  # 이용자보호방안

    UNKNOWN = "unknown"


# ============================================================
# 공통 필드 패턴 (모든 문서에서 사용)
# ============================================================
COMMON_FIELD_PATTERNS: dict[str, list[str]] = {
    # 회사/신청인 정보
    "company_name": [
        r"회사명[(\s]*성명[)\s]*[:\s]*(.+?)(?:\n|사업자|$)",
        r"회사명[(\s]*소속[)\s]*[:\s]*(.+?)(?:\n|사업자|$)",
        r"회사명[:\s]*(.+?)(?:\n|사업자|$)",
        r"상\s*호[:\s]*(.+?)(?:\n|$)",
        r"기관명[:\s]*(.+?)(?:\n|유형|$)",
        r"기관[·\s]*단체명[:\s]*(.+?)(?:\n|$)",
    ],
    "representative": [
        r"대표자[명\s]*[:\s]*(.+?)(?:\n|전화|$)",
        r"대\s*표\s*자[:\s]*(.+?)(?:\n|전화|$)",
    ],
    "business_number": [
        r"사업자[(\s]*법인[)\s]*등록번호[:\s]*([\d\-]+)",
        r"사업자등록번호[:\s]*([\d\-]+)",
        r"법인등록번호[:\s]*([\d\-]+)",
    ],
    "address": [
        r"주\s*소[:\s]*(.+?)(?:\n|대표자|$)",
        r"사업장\s*주소[:\s]*(.+?)(?:\n|대표자|$)",
    ],
    "phone": [
        r"전화번호[:\s]*([\d\-]+)",
        r"연락처[:\s]*([\d\-]+)",
        r"전\s*화[:\s]*([\d\-]+)",
    ],
    "email": [
        r"전자우편[:\s]*([\w\.\-]+@[\w\.\-]+)",
        r"이메일[:\s]*([\w\.\-]+@[\w\.\-]+)",
        r"E-?mail[:\s]*([\w\.\-]+@[\w\.\-]+)",
    ],
    # 서비스 정보
    "service_name": [
        r"기술\s*서비스\s*제목[:\s]*(.+?)(?:\n|$)",
        r"명\s*칭[:\s]*(.+?)(?:\n|유\s*형|$)",
        r"기술[·\s]*서비스\s*명칭[:\s]*(.+?)(?:\n|유\s*형|$)",
        r"서비스[명\s]*[:\s]*(.+?)(?:\n|유\s*형|$)",
    ],
    "service_type": [
        # 괄호 안에 체크 표시(√, ✓, ✔, O, ●, ■, v, V)가 있는 항목 찾기 - 캡처 그룹으로 타입 반환
        r"(기술인\s*경우)\s*\(\s*[√✓✔OoVv●■]\s*\)",  # 기술인 경우 ( √ ) → "기술인 경우"
        r"(서비스인\s*경우)\s*\(\s*[√✓✔OoVv●■]\s*\)",  # 서비스인 경우 ( √ ) → "서비스인 경우"
        r"(기술과\s*서비스가\s*융합된\s*경우)\s*\(\s*[√✓✔OoVv●■]\s*\)",  # 융합된 경우 ( √ ) → "기술과 서비스가 융합된 경우"
        # 기존 패턴 (fallback)
        r"유\s*형[:\s]*(기술인\s*경우|서비스인\s*경우|기술과\s*서비스가\s*융합된\s*경우)",
        r"유\s*형[:\s]*(.+?)(?:\n|주요|$)",
    ],
    "service_description": [
        r"기술\s*서비스\s*내용[:\s]*(.+?)(?:\n기술|2\.|$)",
        r"주요\s*내용[:\s]*(.+?)(?:\n\n|소관|$)",
        r"서비스\s*설명[:\s]*(.+?)(?:\n\n|소관|$)",
        r"기술[·\s]*서비스에\s*대한\s*설명[:\s]*(.+?)(?:\n\n|소관|$)",
    ],
}


# ============================================================
# 상담신청(counseling-1) 전용 패턴
# ============================================================
COUNSELING_PATTERNS: dict[str, list[str]] = {
    "position": [
        r"직\s*위[:\s]*(.+?)(?:\n|성명|$)",
    ],
    "name": [
        r"성\s*명[:\s]*(.+?)(?:\n|사업장|$)",
    ],
    "consultation_date": [
        r"상담\s*희망\s*일자[:\s]*(.+?)(?:\n|$)",
    ],
    "consultation_content": [
        r"ICT\s*규제\s*샌드박스\s*상담내용[^:]*[:\s]*(.+?)(?:\n\n|$)",
        r"상담내용[^:]*[:\s]*(.+?)(?:\n\n|$)",
        r"규제사안\s*및\s*문의사항[:\s]*(.+?)(?:\n\n|$)",
    ],
}


# ============================================================
# 신속확인 신청서(fastcheck-1) 전용 패턴
# ============================================================
FASTCHECK_APPLICATION_PATTERNS: dict[str, list[str]] = {
    "receipt_number": [
        r"접수번호[:\s]*(.+?)(?:\n|접수일시|$)",
    ],
    "receipt_date": [
        r"접수일시[:\s]*(.+?)(?:\n|$)",
    ],
    "expected_agency": [
        r"(?:예상되는\s*)?소관\s*(?:중앙)?행정기관(?:\s*또는\s*지방자치단체)?[:\s]*(.+?)(?:\n|예상|$)",
        r"소관부처[:\s]*(.+?)(?:\n|$)",
    ],
    "expected_permit": [
        r"예상되는\s*허가등[:\s]*(.+?)(?:\n|$)",
    ],
    "application_date": [
        r"신청일자[:\s]*(\d{4}\s*년?\s*\d{1,2}\s*월?\s*\d{1,2}\s*일?)",
        r"신청일자[:\s]*(.+?)(?:\n|신청인|$)",
    ],
    "applicant_signature": [
        r"신청인\s*성명[^:]*[:\s]*(.+?)(?:\n|$)",
    ],
}


# ============================================================
# 신속확인 첨부서류(fastcheck-2) 전용 패턴
# ============================================================
FASTCHECK_DESCRIPTION_PATTERNS: dict[str, list[str]] = {
    "technology_service_details": [
        r"1\.\s*기술[·\s]*서비스\s*세부내용[:\s]*(.+?)(?:2\.|$)",
        r"기술[·\s]*서비스\s*세부내용[:\s]*(.+?)(?:\n\n|2\.|$)",
    ],
    "legal_issues": [
        r"2\.\s*법[·\s]*제도\s*이슈\s*사항[:\s]*(.+?)(?:3\.|$)",
        r"법[·\s]*제도\s*이슈\s*사항[:\s]*(.+?)(?:\n\n|3\.|$)",
    ],
    "additional_questions": [
        r"3\.\s*기타\s*질의\s*사항[:\s]*(.+?)(?:\n\n|$)",
        r"기타\s*질의\s*사항[:\s]*(.+?)(?:\n\n|$)",
    ],
    # 기술 정보 (설명서용)
    "core_technology": [
        r"주요\s*기술\s*요소[:\s]*(.+?)(?:\n\n|2\.|$)",
        r"핵심\s*기술[:\s]*(.+?)(?:\n\n|$)",
        r"기술\s*요소[:\s]*(.+?)(?:\n\n|$)",
    ],
    "regulatory_issues": [
        r"법령\s*해석\s*관련\s*이슈[:\s]*(.+?)(?:\n\n|②|$)",
        r"예상되는\s*허가등[:\s]*(.+?)(?:\n\n|$)",
        r"규제\s*사안[:\s]*(.+?)(?:\n\n|$)",
        r"법[·\s]*제도\s*이슈\s*사항[:\s]*(.+?)(?:\n\n|$)",
    ],
    "related_laws": [
        r"관련\s*법령\s*체계[^:]*[:\s]*(.+?)(?:\n\n|①|$)",
        r"관련\s*법령[:\s]*(.+?)(?:\n\n|$)",
    ],
}


# ============================================================
# 임시허가/실증특례 신청서 공통 패턴
# ============================================================
APPLICATION_COMMON_PATTERNS: dict[str, list[str]] = {
    "receipt_number": [
        r"접수번호[:\s]*(.+?)(?:\n|접수일시|$)",
    ],
    "receipt_date": [
        r"접수일시[:\s]*(.+?)(?:\n|$)",
    ],
    "expected_agency": [
        r"(?:예상되는\s*)?소관\s*(?:중앙)?행정기관(?:\s*또는\s*지방자치단체)?[:\s]*(.+?)(?:\n|예상|$)",
        r"소관부처[:\s]*(.+?)(?:\n|$)",
    ],
    "expected_permit": [
        r"예상되는\s*허가등[:\s]*(.+?)(?:\n|$)",
        r"예상되는\s*허가[:\s]*(.+?)(?:\n|$)",
    ],
    "application_date": [
        r"신청일자[:\s]*(\d{4}\s*년?\s*\d{1,2}\s*월?\s*\d{1,2}\s*일?)",
        r"신청일자[:\s]*(.+?)(?:\n|신청인|$)",
    ],
    "applicant_signature": [
        r"신청인\s*성명[^:]*[:\s]*(.+?)(?:\n|$)",
    ],
}


# ============================================================
# 임시허가 신청서(temporary-1) 전용 패턴
# (체크박스 추출은 TEMPORARY_REASON_CHECKBOX_PATTERNS 사용)
# ============================================================
TEMPORARY_APPLICATION_PATTERNS: dict[str, list[str]] = {}


# ============================================================
# 사업계획서/실증계획서 공통 패턴
# ============================================================
PLAN_COMMON_PATTERNS: dict[str, list[str]] = {
    "project_name": [
        r"사업명[:\s]*(.+?)(?:\n|기간|$)",
        r"실증사업명[:\s]*(.+?)(?:\n|기간|$)",
    ],
    "period_start": [
        r"기간[^:]*[:\s]*(\d{4}\s*[년.]\s*\d{1,2}\s*[월.])",
        r"시작[:\s]*(\d{4}\s*[년.]\s*\d{1,2}\s*[월.]\s*\d{1,2})",
    ],
    "period_end": [
        r"[~∼]\s*(\d{4}\s*[년.]\s*\d{1,2}\s*[월.]\s*\d{1,2})",
        r"종료[:\s]*(\d{4}\s*[년.]\s*\d{1,2}\s*[월.]\s*\d{1,2})",
    ],
    "period_months": [
        r"(\d+)\s*개월",
    ],
    "submission_date": [
        r"제출일자[:\s]*(\d{4}\s*년?\s*\d{1,2}\s*월?\s*\d{1,2}\s*일?)",
    ],
    "detailed_description": [
        r"가\.\s*기술[·\s]*서비스\s*세부\s*내용[:\s]*(.+?)(?:나\.|$)",
        r"기술[·\s]*서비스\s*세부\s*내용[:\s]*(.+?)(?:\n\n|나\.|$)",
    ],
    "market_status": [
        r"나\.\s*기술[·\s]*서비스\s*관련\s*시장\s*현황\s*및\s*전망[:\s]*(.+?)(?:2\.|$)",
        r"시장\s*현황\s*및\s*전망[:\s]*(.+?)(?:\n\n|2\.|$)",
    ],
    "regulation_details": [
        r"가\.\s*규제\s*내용[:\s]*(.+?)(?:나\.|$)",
        r"규제\s*내용[:\s]*(.+?)(?:\n\n|나\.|$)",
    ],
    "necessity_and_request": [
        r"나\.\s*(?:임시허가|규제특례)(?:의)?\s*필요성\s*및\s*내용[:\s]*(.+?)(?:3\.|$)",
    ],
    "objectives_and_scope": [
        r"가\.\s*(?:사업|실증)\s*목표\s*및\s*범위[:\s]*(.+?)(?:나\.|$)",
    ],
    "business_content": [
        r"나\.\s*사업\s*내용[:\s]*(.+?)(?:다\.|$)",
    ],
    "execution_method": [
        r"나\.\s*단계별\s*추진\s*방법[^:]*[:\s]*(.+?)(?:다\.|$)",
    ],
    "schedule": [
        r"다\.\s*(?:사업|실증)\s*기간\s*및\s*일정\s*계획[:\s]*(.+?)(?:4\.|$)",
    ],
    "operation_plan": [
        r"4\.\s*(?:사업|실증)\s*운영\s*계획[:\s]*(.+?)(?:5\.|$)",
    ],
    "expected_quantitative": [
        r"가\.\s*정량적\s*기대효과[:\s]*([\s\S]+?)(?=나\.\s*정성적|$)",
        r"정량적\s*기대효과[:\s]*([\s\S]+?)(?=정성적\s*기대효과|$)",
    ],
    "expected_qualitative": [
        r"나\.\s*정성적\s*기대효과[:\s]*([\s\S]+?)(?=6\.\s*사업|$)",
        r"정성적\s*기대효과[:\s]*([\s\S]+?)(?=사업\s*확대|$)",
    ],
    "expansion_plan": [
        r"6\.\s*(?:사업\s*확대[·\s]*확산|실증\s*이후)\s*계획[:\s]*(.+?)(?:7\.|$)",
        r"가\.\s*확산\s*계획[:\s]*(.+?)(?:나\.|7\.|$)",
    ],
    "restoration_plan": [
        r"나\.\s*실증\s*후\s*복구\s*계획[:\s]*(.+?)(?:7\.|$)",
    ],
    "organization_structure": [
        r"가\.\s*추진\s*체계[:\s]*(.+?)(?:나\.|$)",
    ],
    "budget": [
        r"나\.\s*추진\s*예산[:\s]*(.+?)(?:붙임|$)",
    ],
    # 붙임 1. 신청기관 현황자료
    "establishment_date": [
        r"설립일[:\s]*(.+?)(?:\n|대표자|$)",
    ],
    "main_business": [
        r"주요\s*사업[:\s]*(.+?)(?:\n\n|주요\s*인허가|$)",
    ],
    "licenses_and_permits": [
        r"주요\s*인허가\s*사항[:\s]*(.+?)(?:\n\n|보유기술|$)",
    ],
    "technologies_and_patents": [
        r"보유기술\s*및\s*특허[:\s]*(.+?)(?:\n\n|재무|$)",
    ],
}


# ============================================================
# 소명서 공통 패턴 (temporary-3, demonstration-3)
# ============================================================
JUSTIFICATION_PATTERNS: dict[str, list[str]] = {
    "eligibility_reason_1": [
        r"허가등의\s*근거가\s*되는\s*법령에\s*해당\s*신규[^.]+없는\s*경우",
        r"법령에\s*따른\s*기준[·\s]*규격[·\s]*요건\s*등이\s*없는\s*경우",
        r"다른\s*법령의\s*규정에\s*의하여\s*허가\s*등을\s*신청하는\s*것이\s*불가능한\s*경우",
    ],
    "eligibility_reason_2": [
        r"기준[·\s]*규격[·\s]*요건\s*등을\s*적용하는\s*것이\s*불명확하거나\s*불합리한\s*경우",
    ],
    "justification": [
        r"2\.\s*해당여부에\s*대한\s*근거[:\s]*(.+?)(?:\n\n|$)",
        r"해당여부에\s*대한\s*근거[:\s]*(.+?)(?:\n\n|$)",
    ],
}


# ============================================================
# 안전성/이용자보호 공통 패턴 (temporary-4, demonstration-4)
# ============================================================
SAFETY_PROTECTION_PATTERNS: dict[str, list[str]] = {
    "safety_verification": [
        r"1\.\s*안전성\s*검증\s*자료[:\s]*(.+?)(?:2\.|$)",
        r"안전성\s*검증\s*자료[:\s]*(.+?)(?:\n\n|2\.|$)",
    ],
    "user_protection_plan": [
        r"(?:1\.|2\.)\s*이용자\s*보호\s*(?:및\s*)?대응\s*(?:계획)?[:\s]*(.+?)(?:2\.|3\.|$)",
    ],
    "risk_and_response": [
        r"(?:2\.|3\.)\s*(?:임시허가|규제특례)에\s*따른\s*위험\s*및\s*대응\s*방안[:\s]*(.+?)(?:3\.|4\.|$)",
    ],
    "stakeholder_conflict": [
        r"(?:3\.|4\.)\s*기존\s*시장\s*및\s*이용자\s*등의\s*이해관계\s*충돌[^:]*[:\s]*(.+?)(?:\n\n|$)",
    ],
}


# ============================================================
# 실증특례 신청서(demonstration-1) 전용 패턴
# (체크박스 추출은 DEMONSTRATION_REASON_CHECKBOX_PATTERNS 사용)
# ============================================================
DEMONSTRATION_APPLICATION_PATTERNS: dict[str, list[str]] = {}


# ============================================================
# 체크박스 추출 패턴 (HWP 문서에서 체크 상태 판별)
# ============================================================

# 실증특례 신청 사유 체크박스 패턴 (demonstration-1)
# 사유1: 다른 법령의 규정에 의하여 허가 등을 신청하는 것이 불가능한 경우 (법 제38조의2제1항제1호)
# 사유2: 기준·규격·요건 등을 적용하는 것이 불명확하거나 불합리한 경우 (법 제38조의2제1항제2호)
#
# HWP 형식 예시:
# TABLE 형식 (해당여부 컬럼에 O 표시):
#   | 사유 | 해당여부 |
#   | 불가능한 경우(제1호) | O |
#   | 불합리한 경우(제2호) | O |
#
# 기존 형식 (대괄호/괄호 체크):
#   1. 불가능한 경우(제1호)  [√]
#   2. 불합리한 경우(제2호)  [ ]
DEMONSTRATION_REASON_CHECKBOX_PATTERNS: dict[str, dict[str, str]] = {
    # reason1: 허가 등을 신청하는 것이 불가능한 경우 (제1호)
    "impossibleToApplyPermit": {
        # TABLE 형식: 텍스트 뒤에 O 또는 ○ 또는 ● 마크 (해당여부 컬럼)
        "table_checked": r"(?:제38조의2제1항제1호|제1호\)|불가능한\s*경우)[^\n]*?[\t\s]{2,}[OoㅇⓞО○●■☑✓✔√](?:\s|$|\n|[\t])",
        "table_unchecked": r"(?:제38조의2제1항제1호|제1호\)|불가능한\s*경우)[^\n]*?[\t\s]{2,}(?:$|\n)",
        # 기존 형식: 텍스트 뒤에 [√] 또는 (√) 형태의 체크 표시
        # [^\n]*? - 줄바꿈 제외 모든 문자, non-greedy (법령 괄호 포함 가능)
        "after_text_checked": r"(?:제38조의2제1항제1호|제1호\)|불가능한\s*경우)[^\n]*?[\[\(]\s*[√✓✔vVOo●■]\s*[\]\)]",
        "after_text_unchecked": r"(?:제38조의2제1항제1호|제1호\)|불가능한\s*경우)[^\n]*?[\[\(]\s*[\]\)]",
        # 텍스트 앞에 체크 표시
        "before_text_checked": r"[√✓✔☑■●vVOo]\s*[^\n]{0,30}?(?:제38조의2제1항제1호|제1호|불가능한\s*경우)",
        "before_text_unchecked": r"[☐□]\s*[^\n]{0,30}?(?:제38조의2제1항제1호|제1호|불가능한\s*경우)",
    },
    # reason2: 기준·규격·요건 등을 적용하는 것이 불명확하거나 불합리한 경우 (제2호)
    "unclearOrUnreasonableCriteria": {
        # TABLE 형식: 텍스트 뒤에 O 또는 ○ 또는 ● 마크
        "table_checked": r"(?:제38조의2제1항제2호|제2호\)|불합리한\s*경우)[^\n]*?[\t\s]{2,}[OoㅇⓞО○●■☑✓✔√](?:\s|$|\n|[\t])",
        "table_unchecked": r"(?:제38조의2제1항제2호|제2호\)|불합리한\s*경우)[^\n]*?[\t\s]{2,}(?:$|\n)",
        # 기존 형식: 텍스트 뒤에 [√] 또는 (√) 형태의 체크 표시
        "after_text_checked": r"(?:제38조의2제1항제2호|제2호\)|불합리한\s*경우)[^\n]*?[\[\(]\s*[√✓✔vVOo●■]\s*[\]\)]",
        "after_text_unchecked": r"(?:제38조의2제1항제2호|제2호\)|불합리한\s*경우)[^\n]*?[\[\(]\s*[\]\)]",
        # 텍스트 앞에 체크 표시
        "before_text_checked": r"[√✓✔☑■●vVOo]\s*[^\n]{0,30}?(?:제38조의2제1항제2호|제2호|불합리한\s*경우)",
        "before_text_unchecked": r"[☐□]\s*[^\n]{0,30}?(?:제38조의2제1항제2호|제2호|불합리한\s*경우)",
    },
}

# 임시허가 신청 사유 체크박스 패턴 (temporary-1)
# 사유1: 허가등의 근거가 되는 법령에 해당 신규 기술·서비스에 맞는 기준·규격·요건 등이 없는 경우 (법 제37조제1항제1호)
# 사유2: 법령에 따른 기준·규격·요건 등을 적용하는 것이 불명확하거나 불합리한 경우 (법 제37조제1항제2호)
#
# HWP 형식 예시:
# TABLE 형식 (해당여부 컬럼에 O 표시):
#   | 사유 | 해당여부 |
#   | 요건 등이 없는 경우(제1호) | O |
#   | 불합리한 경우(제2호) | O |
#
# 기존 형식 (대괄호/괄호 체크):
#   1. 요건 등이 없는 경우(제1호)  [√]
#   2. 불합리한 경우(제2호)  [ ]
TEMPORARY_REASON_CHECKBOX_PATTERNS: dict[str, dict[str, str]] = {
    # reason1: 기준·규격·요건 등이 없는 경우 (제1호)
    # 키 이름: noApplicableStandards (application_drafter와 일치)
    "noApplicableStandards": {
        # TABLE 형식: 텍스트 뒤에 O 또는 ○ 또는 ● 마크 (해당여부 컬럼)
        "table_checked": r"(?:제37조제1항제1호|제1호\)|요건\s*등이\s*없는\s*경우)[^\n]*?[\t\s]{2,}[OoㅇⓞО○●■☑✓✔√](?:\s|$|\n|[\t])",
        "table_unchecked": r"(?:제37조제1항제1호|제1호\)|요건\s*등이\s*없는\s*경우)[^\n]*?[\t\s]{2,}(?:$|\n)",
        # 기존 형식: 텍스트 뒤에 [√] 또는 (√) 형태의 체크 표시
        # [^\n]*? - 줄바꿈 제외 모든 문자, non-greedy (법령 괄호 포함 가능)
        "after_text_checked": r"(?:제37조제1항제1호|제1호\)|요건\s*등이\s*없는\s*경우)[^\n]*?[\[\(]\s*[√✓✔vVOo●■]\s*[\]\)]",
        "after_text_unchecked": r"(?:제37조제1항제1호|제1호\)|요건\s*등이\s*없는\s*경우)[^\n]*?[\[\(]\s*[\]\)]",
        # 텍스트 앞에 체크 표시
        "before_text_checked": r"[√✓✔☑■●vVOo]\s*[^\n]{0,30}?(?:제37조제1항제1호|제1호|요건\s*등이\s*없는\s*경우)",
        "before_text_unchecked": r"[☐□]\s*[^\n]{0,30}?(?:제37조제1항제1호|제1호|요건\s*등이\s*없는\s*경우)",
    },
    # reason2: 기준·규격·요건 등을 적용하는 것이 불명확하거나 불합리한 경우 (제2호)
    # 키 이름: unclearOrUnreasonableStandards (application_drafter와 일치)
    "unclearOrUnreasonableStandards": {
        # TABLE 형식: 텍스트 뒤에 O 또는 ○ 또는 ● 마크
        "table_checked": r"(?:제37조제1항제2호|제2호\)|불합리한\s*경우)[^\n]*?[\t\s]{2,}[OoㅇⓞО○●■☑✓✔√](?:\s|$|\n|[\t])",
        "table_unchecked": r"(?:제37조제1항제2호|제2호\)|불합리한\s*경우)[^\n]*?[\t\s]{2,}(?:$|\n)",
        # 기존 형식: 텍스트 뒤에 [√] 또는 (√) 형태의 체크 표시
        "after_text_checked": r"(?:제37조제1항제2호|제2호\)|불합리한\s*경우)[^\n]*?[\[\(]\s*[√✓✔vVOo●■]\s*[\]\)]",
        "after_text_unchecked": r"(?:제37조제1항제2호|제2호\)|불합리한\s*경우)[^\n]*?[\[\(]\s*[\]\)]",
        # 텍스트 앞에 체크 표시
        "before_text_checked": r"[√✓✔☑■●vVOo]\s*[^\n]{0,30}?(?:제37조제1항제2호|제2호|불합리한\s*경우)",
        "before_text_unchecked": r"[☐□]\s*[^\n]{0,30}?(?:제37조제1항제2호|제2호|불합리한\s*경우)",
    },
}


# ============================================================
# 리스트 추출 패턴
# ============================================================

# 기술 요소 리스트 추출 패턴 (줄바꿈으로 구분된 항목들)
TECHNOLOGY_LIST_PATTERNS: list[str] = [
    r"주요\s*기술\s*요소\s*\n(.+?)(?:\n\n|2\.|$)",
    r"기술[·\s]*서비스\s*구현을\s*위해[^\n]*\n(.+?)(?:\n\n|2\.|$)",
]

# 관련 법령 리스트 추출 패턴
LAW_LIST_PATTERNS: list[str] = [
    r"「([^」]+)」",  # 법령명 추출 (「」 안의 내용)
]


# ============================================================
# 문서 타입별 패턴 매핑 함수
# ============================================================
def get_patterns_for_subtype(subtype: DocumentSubtype) -> dict[str, list[str]]:
    """문서 서브타입에 맞는 필드 패턴 반환

    Args:
        subtype: 문서 서브타입

    Returns:
        필드명과 패턴 리스트의 딕셔너리
    """
    # 기본 공통 패턴으로 시작
    patterns = dict(COMMON_FIELD_PATTERNS)

    # 문서 타입별 추가 패턴 병합
    if subtype == DocumentSubtype.COUNSELING_APPLICATION:
        patterns.update(COUNSELING_PATTERNS)

    elif subtype == DocumentSubtype.FASTCHECK_APPLICATION:
        patterns.update(APPLICATION_COMMON_PATTERNS)
        patterns.update(FASTCHECK_APPLICATION_PATTERNS)

    elif subtype == DocumentSubtype.FASTCHECK_DESCRIPTION:
        patterns.update(FASTCHECK_DESCRIPTION_PATTERNS)

    elif subtype == DocumentSubtype.TEMPORARY_APPLICATION:
        patterns.update(APPLICATION_COMMON_PATTERNS)
        patterns.update(TEMPORARY_APPLICATION_PATTERNS)

    elif subtype == DocumentSubtype.TEMPORARY_BUSINESS_PLAN:
        patterns.update(PLAN_COMMON_PATTERNS)

    elif subtype == DocumentSubtype.TEMPORARY_JUSTIFICATION:
        patterns.update(JUSTIFICATION_PATTERNS)

    elif subtype == DocumentSubtype.TEMPORARY_SAFETY:
        patterns.update(SAFETY_PROTECTION_PATTERNS)

    elif subtype == DocumentSubtype.DEMONSTRATION_APPLICATION:
        patterns.update(APPLICATION_COMMON_PATTERNS)
        patterns.update(DEMONSTRATION_APPLICATION_PATTERNS)

    elif subtype == DocumentSubtype.DEMONSTRATION_PLAN:
        patterns.update(PLAN_COMMON_PATTERNS)

    elif subtype == DocumentSubtype.DEMONSTRATION_JUSTIFICATION:
        patterns.update(JUSTIFICATION_PATTERNS)

    elif subtype == DocumentSubtype.DEMONSTRATION_PROTECTION:
        patterns.update(SAFETY_PROTECTION_PATTERNS)

    return patterns
