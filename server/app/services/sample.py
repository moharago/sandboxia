from langchain_core.messages import AIMessage, HumanMessage

from app.agents.sample_supervisor.graph import get_graph


def run_langgraph_agent(user_input: str) -> str:
    app = get_graph()
    inputs = {
        "messages": [HumanMessage(content=user_input)],
        "next": "",
        "iteration_count": 0,
    }
    config = {"recursion_limit": 15}
    final_state = app.invoke(inputs, config)
    for message in reversed(final_state["messages"]):
        if isinstance(message, AIMessage) and message.content:
            return message.content
    return "응답을 생성하지 못했습니다."
