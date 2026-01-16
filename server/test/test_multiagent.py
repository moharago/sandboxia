import openai
import json
import requests
from datetime import datetime
from typing import TypedDict, Annotated, Sequence, Literal
import operator

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

# A 에이전트 - 3가지 도구를 다 선택, 호출, 관리
# 멀티 에이전트: A 에이전트 - 관리자, B 에이전트 - 계산기, C 에이전트 - 검색 ...

############################

@tool
def web_search_tool(query: str) -> str:
    """인터넷에서 정보를 검색합니다"""
    print(f"  🔍 검색: {query}")

    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "max_results": 2
        }

        response = requests.post(url, json=payload)
        data = response.json()

        results = []
        for result in data.get("results", [])[:2]:
            results.append(f"{result.get('title')}: {result.get('content')[:100]}")

        return "\n".join(results)
    except Exception as e:
        return f"검색 실패: {str(e)}"


@tool
def calculate_tool(expression: str) -> str:
    """수학 계산을 수행합니다"""
    print(f"  🧮 계산: {expression}")

    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return f"{expression} = {result}"
    except Exception as e:
        return f"계산 실패: {str(e)}"


@tool
def get_time_tool() -> str:
    """현재 시간을 가져옵니다"""
    print(f"  ⏰ 시간 조회")
    now = datetime.now()
    return f"{now.strftime('%Y년 %m월 %d일 %H시 %M분')}"


tools = [web_search_tool, calculate_tool, get_time_tool]

print("✅ 도구 3개 정의 완료")
for t in tools:
    print(f"  - {t.name}: {t.description}")

############################

class AgentState(TypedDict):
   messages : Annotated[Sequence[BaseMessage], operator.add]
   next : str  # 다음 에이전트
   iteration_count : int # 반복 횟수 추적 (무한 루프 방지용 , 카운터)

############################

researcher_llm = llm.bind_tools([web_search_tool])

def researcher_node(state: AgentState):
    """연구원: 웹에서 정보 검색"""
    print("🔬 연구원 에이전트 실행")

    messages = [
        SystemMessage(content = '당신은 정보 검색 전문가 입니다. 웹 검색으로 정확한 정보를 찾으세요'),
        *state['messages']
    ]

    response = researcher_llm.invoke(messages)


    # 도구 호출이 있으면 실행
    if response.tool_calls:
        tool_node = ToolNode([web_search_tool])
        tool_result = tool_node.invoke({"messages": [response]})
        return {"messages": [response] + tool_result["messages"]}
    return {"messages": [response]}

############################

# 계산원 에이전트 (계산)
calculator_llm = llm.bind_tools([calculate_tool, get_time_tool])

def calculator_node(state: AgentState):
    """계산원: 수학 계산 수행"""
    print("🧮 계산원 에이전트 실행")

    messages = [
        SystemMessage(content = '당신은 계산 전문가 입니다. 정확한 계산 결과를 제공 하세요.'),
        *state['messages']
    ]

    response = calculator_llm.invoke(messages)

    if response.tool_calls:
        tool_node = ToolNode([calculate_tool, get_time_tool])
        tool_result = tool_node.invoke({"messages": [response]})
        return {"messages": [response] + tool_result["messages"]}

    return {"messages": [response]}

############################

# 관리자 에이전트 (라우팅)
supervisor_prompt = '''
당신은 팀 관리자입니다. 작업을 적절한 팀원에게 할당 하세요.

팀원 :
- researcher : 웹 검색, 최신 정보 조사
- calculator : 수학 계산, 날짜/ 시간 계산

지시사항:
1.  사용자 요청을 분석하세요
2.  아직 작업이 안 된 부분이 있으면 적절한 팀원을 다시 선택하세요.
3.  이미 충분히 답변 했다면, FINISH를 선택하세요
4.  한번에 한명만 선택하세요

다음중 하나만 응답:
researcher, calculator, FINISH

'''

def supervisor_node(state: AgentState):
    """관리자: 작업 할당"""
    print("👔 관리자 에이전트: 작업 분석 중...")

    # 반복 횟수 체크
    iteration = state.get('iteration_count',0) + 1
    print(f'반복 {iteration} / 5')

    if iteration > 5:
        print(' 관리자 : 최대 반복 횟수 도달 -> 종료')
        return {'next' : 'FINISH',
             'iteration_count' : iteration}

    messages = [
        SystemMessage(content=supervisor_prompt),
        *state["messages"]
    ]

    response = llm.invoke(messages)
    content = response.content.lower()

    # 다음 에이전트 결정
    if "researcher" in content and iteration <= 5:
        next_agent = "researcher"
    elif "calculator" in content and iteration <= 5:
        next_agent = "calculator"
    else:
        next_agent = "FINISH"

    print(f"👔 관리자 결정: {next_agent}")

    if next_agent == "FINISH":
        # 최종 답변 생성 로직 추가!
        final_response = llm.invoke([
            SystemMessage("팀원들의 정보를 종합해서 답변 작성"),
            *state["messages"]
        ])
        return {"messages": [final_response], "next": "FINISH"}

    return {
        "messages": [response],
        "next": next_agent,
        "iteration_count": iteration
    }

############################


workflow = StateGraph(AgentState)

# 노드 추가
workflow.add_node('supervisor', supervisor_node)
workflow.add_node('researcher', researcher_node)
workflow.add_node('calculator', calculator_node)

# 시작은 관리자
workflow.set_entry_point('supervisor')

# 라우팅 함수 : 'researcher', 'calculator', '__end__' 중에 하나만 사용할 수 있도록 하는 안전장치
def router(state: AgentState) -> Literal['researcher', 'calculator', '__end__']:
  return state['next']

# 조건부 엣지
workflow.add_conditional_edges(
    'supervisor',
    router,
    {
        'researcher': 'researcher',
        'calculator': 'calculator',
        'FINISH': END
    }
)

# 작업 후 다시 관리자에게
workflow.add_edge('researcher', 'supervisor')
workflow.add_edge('calculator', 'supervisor')

# 컴파일
app = workflow.compile()

print("✅ 그래프 구성 완료")

############################

def run_agent(question: str, verbose: bool = True):
    """멀티 에이전트 실행"""
    if verbose:
        print("="*60)
        print("🤖 멀티 에이전트 시작")
        print("="*60)
        print(f"❓ 질문: {question}\n")

    inputs = {
        "messages": [HumanMessage(content=question)],
        "next": "",
        "iteration_count": 0
    }

    # recursion_limit 설정
    config = {"recursion_limit": 15}

    result = app.invoke(inputs, config)

    # 마지막 AI 메시지 찾기
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and msg.content:
            if verbose:
                print("\n" + "="*60)
                print("✅ 완료")
                print("="*60)
            return msg.content

    return "응답을 생성하지 못했습니다."

print("✅ 실행 함수 정의 완료")

############################

run_agent('오늘 날짜 확인하고, 2025년이 며칠 전인지 계산해서 알려줘.')