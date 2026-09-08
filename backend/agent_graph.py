"""Optional LangGraph orchestration wrapper."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from backend.agent import evaluate_request as _evaluate_sequential
from backend.schemas import EvaluateResponse


class AgentState(TypedDict, total=False):
    query: str
    scenario_loan_amount: int | None
    loan_amount: int | None
    result: EvaluateResponse


def _run_pipeline(state: AgentState) -> AgentState:
    result = _evaluate_sequential(
        state["query"],
        state.get("scenario_loan_amount"),
        state.get("loan_amount"),
    )
    return {"result": result}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("evaluate", _run_pipeline)
    graph.set_entry_point("evaluate")
    graph.add_edge("evaluate", END)
    return graph.compile()


def evaluate_with_graph(
    query: str,
    scenario_loan_amount: int | None = None,
    loan_amount: int | None = None,
) -> EvaluateResponse:
    app = build_graph()
    final = app.invoke(
        {
            "query": query,
            "scenario_loan_amount": scenario_loan_amount,
            "loan_amount": loan_amount,
        }
    )
    return final["result"]
