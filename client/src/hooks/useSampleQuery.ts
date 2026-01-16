import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import { fetchSample } from "@/lib/api/sample";
import type { AgentResponse } from "@/types/api";

export default function useSampleQuery(
  query: string
): UseQueryResult<AgentResponse, Error> {
  return useQuery<AgentResponse, Error>({
    queryKey: ["sample", query],
    queryFn: () => fetchSample(query),
    enabled: Boolean(query),
  });
}
