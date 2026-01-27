/**
 * 전화번호 포맷팅 (숫자만 입력해도 000-0000-0000 형식으로 변환)
 */
export function formatPhoneNumber(value: string): string {
    // 숫자만 추출
    const numbers = value.replace(/\D/g, '')

    // 최대 11자리까지만
    const limited = numbers.slice(0, 11)

    // 길이에 따라 포맷팅
    if (limited.length <= 3) {
        return limited
    } else if (limited.length <= 7) {
        return `${limited.slice(0, 3)}-${limited.slice(3)}`
    } else {
        return `${limited.slice(0, 3)}-${limited.slice(3, 7)}-${limited.slice(7)}`
    }
}

/**
 * 입력값에 숫자 외 문자가 포함되어 있는지 확인
 */
export function hasNonDigit(value: string): boolean {
    return /\D/.test(value)
}
