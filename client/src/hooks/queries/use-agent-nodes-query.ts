/**
 * Agent Nodes Query Hook
 *
 * 에이전트의 노드 목록을 조회하는 훅
 *
 * @example
 * ```tsx
 * const { data: nodes, isLoading } = useAgentNodesQuery("eligibility_evaluator")
 *
 * // 노드 목록 렌더링
 * {nodes?.nodes.map(node => (
 *   <div key={node.id}>
 *     {completedNodes.includes(node.id) ? "✓" : "○"} {node.label}
 *   </div>
 * ))}
 * ```
 */

import { useAuthStore } from "@/stores/auth-store"
import type { AgentNodesResponse, AgentType } from "@/types/api/agent-progress"
import { useQuery } from "@tanstack/react-query"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? ""

/** 에이전트 노드 목록 조회 */
async function fetchAgentNodes(agentType: AgentType): Promise<AgentNodesResponse> {
    const token = await useAuthStore.getState().getAccessToken()

    if (!token) {
        throw new Error("로그인이 필요합니다.")
    }

    const response = await fetch(
        `${API_BASE}/api/v1/agents/progress/nodes/${agentType}`,
        {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
            },
        }
    )

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Unknown error" }))
        throw new Error(errorData.detail || `Request failed: ${response.status}`)
    }

    return response.json()
}

/** 쿼리 키 */
export const agentNodesKeys = {
    all: ["agent-nodes"] as const,
    byType: (agentType: AgentType) => [...agentNodesKeys.all, agentType] as const,
}

/**
 * 에이전트 노드 목록 조회 훅
 */
export function useAgentNodesQuery(agentType: AgentType) {
    return useQuery({
        queryKey: agentNodesKeys.byType(agentType),
        queryFn: () => fetchAgentNodes(agentType),
        staleTime: Infinity, // 노드 목록은 정적이므로 항상 fresh
        gcTime: Infinity,
    })
}
