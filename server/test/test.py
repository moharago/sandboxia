from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
import operator
from app.core.config import settings

@tool
def web_search_tool(query: str) -> str:
    """인터넷에서 실시간 정보를 검색합니다."""

    print(f"🔍 웹 검색: {query}")

    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "max_results": 3
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        # 결과를 간단한 텍스트로 변환
        results_text = f"검색 결과 for '{query}':\n\n"
        for i, result in enumerate(data.get("results", [])[:3], 1):
            results_text += f"{i}. {result.get('title')}\n"
            results_text += f"   {result.get('content')[:150]}...\n\n"

        if data.get("answer"):
            results_text += f"요약: {data.get('answer')}\n"

        return results_text

    except Exception as e:
        return f"검색 실패: {str(e)}"


@tool
def calculate_tool(expression: str) -> str:
    """수학 계산을 수행합니다."""

    print(f"🧮 계산 실행: '{expression}'")

    try:
        # 안전한 계산
        allowed_names = {'abs': abs ,'round':round,'pow':pow}
        result = eval(expression,{'__builtins__' :{}},allowed_names)

        return json.dumps({
            "expression": expression,
            "result": result
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": f"계산 실패: {str(e)}"}, ensure_ascii=False)


@tool
def get_current_time_tool() -> str:
    """현재 날짜와 시간을 가져옵니다."""

    print(f"⏰ 현재 시간 조회")

    now = datetime.now()
    return json.dumps({
        'datetime' : now.strftime('%Y-%m-D %H:%M:%S'),
        'date':now.strftime('%Y-%m-%d'),
        'time':now.strftime('%H:%M:%S'),
        'day_of_week':now.strftime('%A')
    }, ensure_ascii=False)

############################

# 도구 리스트
langchain_tools = [web_search_tool, calculate_tool, get_current_time_tool]

# print("✅ LangChain 스타일 도구 정의 완료")
# for tool in langchain_tools:
#     print("tool :", tool)
#     print(f"  - {tool.name}: {tool.description}")

# ChatOpenAI 모델 생성
llm = ChatOpenAI(
    model="gpt-4.1-nano",
    temperature=0,
    api_key=settings.OPENAI_API_KEY
)

# 모델에 도구 바인딩
llm_with_tools = llm.bind_tools(langchain_tools)

############################

# 사용자에게 질문을 받고 -> LLM이 생각하고 -> 도구 호출하고 -> 도구 결과 받고
# 도구 실행 결과 + 사용자 질문을 보고  -> 다시 생각하고 -> 최종 답변
# 각 단계마다 정보가 축적 되어야 하니 이 모든 정보를 담는 그릇 이 'STATE'

class AgentState(TypedDict):
    """에이전트의 상태를 정의합니다"""
    # messages: 대화 히스토리를 저장하는 리스트
    # operator.add를 사용하여 메시지를 누적
    # TypedDict : 상태 구조를 명확히 정의
    messages : Annotated[Sequence[BaseMessage], operator.add]
    # 명확성 , 안정성, 가독성
    #Annoatated  = 새 메세지가 들어오면 기존 리스트에 추가

############################

def call_model(state: AgentState):
    """LLM을 호출하는 노드"""

    print("🤖 LLM 호출 중...")

    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    print('응답 타입 : ', type(response))
    if hasattr(response, 'tool_calls'):
        print(f' 도구 호출 수 : {len(response.tool_calls)}')
    return {'messages' : [response]}


def should_continue(state: AgentState):
    """다음 노드를 결정하는 조건부 엣지"""

    messages = state["messages"]
    last_message = messages[-1]

    # 도구 호출이 있으면 "tools"로, 없으면 종료
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        print("🔧 도구 호출 필요 → tools 노드로 이동")
        return "tools"
    else:
        print("✅ 작업 완료 → 종료")
        return "end"

############################

workflow = StateGraph(AgentState)

# 노드 추가
workflow.add_node('agent', call_model)
workflow.add_node('tools', ToolNode(langchain_tools))

# 시작점 설정
workflow.set_entry_point('agent')

# 조건부 엣지 추가
workflow.add_conditional_edges(
    'agent',
    should_continue,
    {'tools': 'tools', 'end': END} # should_continue의 return 값에 따라 이동하는 노드가 달라짐
)

# tools 노드에서 agent로 돌아가는 엣지
workflow.add_edge('tools', 'agent')

# 그래프 컴파일
app = workflow.compile()

############################

def run_langgraph_agent(user_input: str):
    """LangGraph 에이전트를 실행하는 함수"""
    print("="*60)
    print("🚀 LangGraph 에이전트 시작")
    print("="*60)
    print(f"📝 질문: {user_input}\n")

    # 초기 상태
    inputs = {"messages": [HumanMessage(content=user_input)]}

    # 스트리밍 방식으로 실행 (개발 중 중간 단계 확인용)
    for output in app.stream(inputs):
        for key, value in output.items():
            print(f"\n--- {key} 노드 ---")
            if "messages" in value:
                for msg in value["messages"]:
                    if isinstance(msg, AIMessage):
                        if msg.content:
                            print(f"💬 AI: {msg.content[:200]}...")
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            for tc in msg.tool_calls:
                                print(f"🔧 도구 호출: {tc['name']}")
                    elif isinstance(msg, ToolMessage):
                        print(f"✅ 도구 결과: {msg.content[:150]}...")

    print("\n" + "="*60)

    # 최종 응답 반환
    final_state = app.invoke(inputs)
    final_message = final_state['messages'][-1]
    return final_message.content

############################

result = run_langgraph_agent("2024 * 35 를 계산하고, 오늘 날씨를 확인해 줘")
print(f"\n💬 최종 답변:\n{result}")

############################

# 메모리 저장소 생성
memory = MemorySaver()

# 메모리를 사용하는 그래프 컴파일
app_with_memory = workflow.compile(checkpointer=memory)

############################

def run_with_memory(user_input: str, thread_id: str = "1"):
    """메모리를 사용하는 에이전트 실행"""
    config = {'configurable' : {'thread_id' : thread_id}}
    inputs = {'messages' : [HumanMessage(content=user_input)]}
    result = app_with_memory.invoke(inputs, config)
    return result["messages"][-1].content

# 연속된 대화 예제
print("\n📝 대화 1:")
response1 = run_with_memory("내 이름은 철수야", thread_id="user_123")
print(f"AI: {response1}")

print("\n📝 대화 2:")
response2 = run_with_memory("내 이름이 뭐였지?", thread_id="user_123")
print(f"AI: {response2}")
