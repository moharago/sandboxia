/** 오늘 날짜를 "YYYY-MM-DD" 형식으로 반환 */
export function getTodayIso(): string {
    const today = new Date()
    const year = today.getFullYear()
    const month = String(today.getMonth() + 1).padStart(2, "0")
    const day = String(today.getDate()).padStart(2, "0")
    return `${year}-${month}-${day}`
}

/** 날짜 문자열 → "YYYY-MM-DD" 변환 (OCR 오류 패턴 포함) */
export function formatDateIso(raw: string): string {
    if (!raw) return ""

    const trimmed = raw.trim()

    // 이미 ISO 형식이면 그대로 반환: "2023-06-29"
    if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) return trimmed

    // 점+공백 구분 (끝에 점 포함): "2026. 02. 06." 또는 "2026. 2. 6."
    const dotSpaced = trimmed.match(/^(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?$/)
    if (dotSpaced) return `${dotSpaced[1]}-${dotSpaced[2].padStart(2, "0")}-${dotSpaced[3].padStart(2, "0")}`

    // ISO 형식 또는 점 구분 (공백 없음): "2023-06-29" 또는 "2023.06.29"
    const iso = trimmed.match(/^(\d{4})[-.]\s*(\d{1,2})[-.]\s*(\d{1,2})$/)
    if (iso) return `${iso[1]}-${iso[2].padStart(2, "0")}-${iso[3].padStart(2, "0")}`

    // 정상: "2023년 6월 29일"
    const normal = raw.match(/(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일/)
    if (normal) return `${normal[1]}-${normal[2].padStart(2, "0")}-${normal[3].padStart(2, "0")}`

    // 부분 누락: "2024년 1월 23" (일 빠짐)
    const noDay = raw.match(/(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})$/)
    if (noDay) return `${noDay[1]}-${noDay[2].padStart(2, "0")}-${noDay[3].padStart(2, "0")}`

    // 부분 누락: "2025 8월 27일" (년 빠짐)
    const noYearSuffix = raw.match(/(\d{4})\s+(\d{1,2})\s*월\s*(\d{1,2})\s*일/)
    if (noYearSuffix) return `${noYearSuffix[1]}-${noYearSuffix[2].padStart(2, "0")}-${noYearSuffix[3].padStart(2, "0")}`

    // OCR 오류: "20244 10" → 파싱 불가, 표시하지 않음
    return ""
}
