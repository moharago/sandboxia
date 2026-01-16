import json
from datetime import datetime

from langchain_core.tools import tool


@tool
def calculate_tool(expression: str) -> str:
    """Perform a safe math calculation."""
    try:
        allowed_names = {"abs": abs, "round": round, "pow": pow}
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return json.dumps(
            {
                "expression": expression,
                "result": result,
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        return json.dumps({"error": f"계산 실패: {exc}"}, ensure_ascii=False)


@tool
def get_current_time_tool() -> str:
    """Return the current date and time."""
    now = datetime.now()
    return json.dumps(
        {
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day_of_week": now.strftime("%A"),
        },
        ensure_ascii=False,
    )


__all__ = ["calculate_tool", "get_current_time_tool"]
