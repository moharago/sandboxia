/** 날짜 문자열 → "YYYY-MM-DD" 변환 (OCR 오류 패턴 포함) */
export function formatDateIso(raw: string): string {
    if (!raw) return ""

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
