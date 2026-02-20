/**
 * 공용 Hook 타입 정의
 */

/**
 * Mutation Hook의 공통 옵션 타입
 * @template TData - onSuccess 콜백에 전달되는 응답 데이터 타입
 */
export interface MutationOptions<TData = void> {
    onSuccess?: (data: TData) => void
    onError?: (error: Error) => void
}
