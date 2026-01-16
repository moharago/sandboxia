from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode

from app.agents.sample_calculator.tools import calculate_tool, get_current_time_tool
from app.core.config import settings


llm = ChatOpenAI(
    model="gpt-4.1-nano",
    temperature=0,
    api_key=settings.OPENAI_API_KEY,
)
calculator_llm = llm.bind_tools([calculate_tool, get_current_time_tool])


def calculator_node(state):
    messages = [
        SystemMessage(content="당신은 계산 전문가입니다. 정확한 계산 결과를 제공하세요."),
        *state["messages"],
    ]
    response = calculator_llm.invoke(messages)

    if response.tool_calls:
        tool_node = ToolNode([calculate_tool, get_current_time_tool])
        tool_result = tool_node.invoke({"messages": [response]})
        return {"messages": [response] + tool_result["messages"]}
    return {"messages": [response]}
