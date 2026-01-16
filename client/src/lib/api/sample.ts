import type { AgentQuery, AgentResponse, ApiErrorResponse } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    "message" in value &&
    typeof (value as ApiErrorResponse).message === "string"
  );
}

function isAgentResponse(value: unknown): value is AgentResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    "answer" in value &&
    typeof (value as AgentResponse).answer === "string"
  );
}

export async function fetchSample(
  query: AgentQuery["query"]
): Promise<AgentResponse> {
  const url = new URL("/sample/query", API_BASE);

  const res = await fetch(url.toString(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });

  const data: AgentResponse | ApiErrorResponse = await res.json();

  if (!res.ok) {
    const message = isApiErrorResponse(data)
      ? data.message
      : `Request failed: ${res.status}`;
    throw new Error(message);
  }

  if (!isAgentResponse(data)) {
    throw new Error("Unexpected response format.");
  }

  return data;
}
