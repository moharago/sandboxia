import { useQuery } from "@tanstack/react-query"
import { sampleApi } from "@/lib/api/sample"
import type { AgentResponse } from "@/types/api"

export const sampleKeys = {
    all: ["sample"] as const,
    queries: () => [...sampleKeys.all, "query"] as const,
    query: (query: string) => [...sampleKeys.queries(), query] as const,
}

export function useSampleQuery(query: string) {
    return useQuery<AgentResponse, Error>({
        queryKey: sampleKeys.query(query),
        queryFn: () => sampleApi.query(query),
        enabled: Boolean(query),
        staleTime: 30 * 1000,
    })
}
