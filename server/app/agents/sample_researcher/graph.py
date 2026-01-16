from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode

from app.agents.sample_researcher.tools import web_search_tool
from app.core.config import settings


llm = ChatOpenAI(
    model="gpt-4.1-nano",
    temperature=0,
    api_key=settings.OPENAI_API_KEY,
)
researcher_llm = llm.bind_tools([web_search_tool])


def researcher_node(state):
    messages = [
        SystemMessage(content="당신은 정보 검색 전문가입니다. 웹 검색으로 정확한 정보를 찾으세요."),
        *state["messages"],
    ]
    response = researcher_llm.invoke(messages)

    if response.tool_calls:
        tool_node = ToolNode([web_search_tool])
        tool_result = tool_node.invoke({"messages": [response]})
        return {"messages": [response] + tool_result["messages"]}
    return {"messages": [response]}
