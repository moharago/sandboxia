from fastapi import APIRouter

from app.api.schemas.sample import AgentQuery, AgentResponse
from app.services.sample import run_langgraph_agent


router = APIRouter(prefix="/sample", tags=["sample"])


@router.post("/query", response_model=AgentResponse)
def query_agent(payload: AgentQuery):
    answer = run_langgraph_agent(payload.query)
    return AgentResponse(answer=answer)
