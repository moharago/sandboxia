/**
 * Step 4 (신청서 초안) 폼 관련 유틸리티 함수
 */

/**
 * 다양한 날짜 형식을 ISO 형식(YYYY-MM-DD)으로 변환
 * - 한국어 형식: "2026년 2월 2일", "2026년 2 월 2일"
 * - 점 형식: "2026. 02. 13.", "2026.02.13"
 * - ISO 형식: 그대로 반환
 */
export function convertToISODate(value: string): string {
    if (!value) return ""

    // 이미 ISO 형식이면 그대로
    if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return value

    // 한국어 형식 (2026년 2월 2일 또는 2026년 2 월 2일)
    const koreanMatch = value.match(/(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일?/)
    if (koreanMatch) {
        const [, year, month, day] = koreanMatch
        return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`
    }

    // 점 형식 (2026. 02. 13. 또는 2026.02.13)
    const dotMatch = value.replace(/\s/g, "").match(/(\d{4})\.(\d{1,2})\.(\d{1,2})\.?/)
    if (dotMatch) {
        const [, year, month, day] = dotMatch
        return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`
    }

    return value
}

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

/**
 * flat key 패턴에서 배열 행 수를 계산
 * 예: "applicantOrganizations.0.name", "applicantOrganizations.1.name" → 2
 */
export function getArrayCount(values: Record<string, string>, prefix: string): number {
    let maxIndex = -1
    const pattern = new RegExp(`^${prefix}\\.(\\d+)\\.`)
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
