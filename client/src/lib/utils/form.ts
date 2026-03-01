/**
 * Step 4 (신청서 초안) 폼 관련 유틸리티 함수
 */

// ============================================
// 체크박스 관련 유틸리티
// ============================================

/**
 * 값이 "체크됨" 상태인지 확인
 * - "true", "V", "√" → true
 * - 그 외 → false
 */
export function isCheckedValue(value: string | undefined): boolean {
    if (!value) return false
    return value === "true" || value === "V" || value === "√"
}

/**
 * boolean을 폼 저장용 문자열로 변환
 * @param checked 체크 상태
 * @param useFalseString true면 "false" 반환, false면 "" 반환 (기본)
 */
export function toBooleanString(checked: boolean, useFalseString = false): string {
    if (checked) return "true"
    return useFalseString ? "false" : ""
}

/**
 * 콤마 구분 문자열을 배열로 파싱
 * - "a,b,c" → ["a", "b", "c"]
 * - "" 또는 undefined → []
 */
export function parseCheckboxArray(value: string | undefined): string[] {
    if (!value) return []
    return value.split(",").filter(Boolean)
}

/**
 * 체크박스 배열 업데이트 후 콤마 구분 문자열 반환
 * @param currentValue 현재 값 (콤마 구분 문자열)
 * @param optionValue 토글할 옵션 값
 * @param checked 체크 여부
 */
export function updateCheckboxArray(
    currentValue: string | undefined,
    optionValue: string,
    checked: boolean
): string {
    const current = parseCheckboxArray(currentValue)
    if (checked) {
        if (!current.includes(optionValue)) {
            current.push(optionValue)
        }
    } else {
        const index = current.indexOf(optionValue)
        if (index > -1) {
            current.splice(index, 1)
        }
    }
    return current.join(",")
}

// ============================================
// 숫자 포맷 관련 유틸리티
// ============================================

/**
 * 숫자에 천 단위 구분자(,) 추가
 * - 퍼센트(%)가 포함된 경우 그대로 반환
 * - 소수점 지원
 */
export function formatNumber(value: string | number | null | undefined): string {
    if (value === null || value === undefined || value === "") return ""

    const strValue = String(value)

    // 퍼센트가 포함된 경우 그대로
    if (strValue.includes("%")) return strValue

    // 숫자와 소수점, 마이너스만 추출
    const numericValue = strValue.replace(/[^0-9.-]/g, "")
    if (!numericValue) return strValue

    // 소수점 처리
    const parts = numericValue.split(".")
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",")
    return parts.join(".")
}

/**
 * 포맷팅된 숫자에서 콤마 제거
 * - 퍼센트(%)가 포함된 경우 그대로 반환
 */
export function parseNumber(formattedValue: string): string {
    if (!formattedValue) return ""
    if (formattedValue.includes("%")) return formattedValue
    return formattedValue.replace(/,/g, "")
}

// js-cache-function-results: RegExp 패턴 캐싱으로 반복 생성 방지
const arrayCountPatternCache = new Map<string, RegExp>()

/**
 * flat key 패턴에서 배열 행 수를 계산
 * 예: "applicantOrganizations.0.name", "applicantOrganizations.1.name" → 2
 */
export function getArrayCount(values: Record<string, string>, prefix: string): number {
    let maxIndex = -1

    // js-cache-function-results: 캐시된 RegExp 사용
    let pattern = arrayCountPatternCache.get(prefix)
    if (!pattern) {
        pattern = new RegExp(`^${prefix}\\.(\\d+)\\.`)
        arrayCountPatternCache.set(prefix, pattern)
    }

    for (const key of Object.keys(values)) {
        const match = key.match(pattern)
        if (match) {
            const index = parseInt(match[1], 10)
            if (index > maxIndex) {
                maxIndex = index
            }
        }
    }
    return maxIndex + 1
}
