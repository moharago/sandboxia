/**
 * Agent Progress API Types
 *
 * SSE 스트리밍을 통한 에이전트 진행 상태 타입 정의
 */

/** 에이전트 타입 */
export type AgentType =
    | "service_structurer"
    | "eligibility_evaluator"
    | "track_recommender"
    | "application_drafter"

/** SSE 이벤트 타입 */
export type AgentEventType =
    | "agent_start"
    | "node_start"
    | "node_end"
    | "agent_end"
    | "error"

/** 노드 정보 */
export interface NodeInfo {
    id: string
    label: string
    description: string
}

/** 에이전트 노드 목록 응답 */
export interface AgentNodesResponse {
    agent_type: AgentType
    nodes: NodeInfo[]
    total_steps: number
}

/** SSE 진행 이벤트 */
export interface AgentProgressEvent {
    event_type: AgentEventType
    agent_type: AgentType
    node_id?: string
    node_label?: string
    progress: number
    message?: string
    completed_nodes: string[]
}

/** SSE 연결 상태 */
export type SSEConnectionStatus =
    | "idle"
    | "connecting"
    | "connected"
    | "completed"
    | "error"

/** SSE 훅 반환 타입 */
export interface UseAgentProgressReturn {
    /** 현재 연결 상태 */
    status: SSEConnectionStatus
    /** 현재 진행률 (0-100) */
    progress: number
    /** 현재 진행 중인 노드 ID */
    currentNodeId: string | null
    /** 완료된 노드 ID 목록 */
    completedNodes: string[]
    /** 현재 메시지 */
    message: string | null
    /** 에러 메시지 */
    error: string | null
    /** 스트리밍 시작 */
    start: () => void
    /** 스트리밍 중단 */
    abort: () => void
}
