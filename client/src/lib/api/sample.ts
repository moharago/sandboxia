import type { AgentQuery, AgentResponse } from "@/types/api";

const API_BASE =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export const sampleApi = {
    query: async (query: AgentQuery["query"]): Promise<AgentResponse> => {
        const response = await fetch(`${API_BASE}/sample/query`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(
                errorData.message || `Request failed: ${response.status}`
            );
        }

        const data = await response.json();

        if (!data.answer || typeof data.answer !== "string") {
            throw new Error("Unexpected response format");
        }

        return data as AgentResponse;
    },
};
