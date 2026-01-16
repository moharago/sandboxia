from pydantic import BaseModel, Field


class AgentQuery(BaseModel):
    query: str = Field(..., min_length=1)


class AgentResponse(BaseModel):
    answer: str
