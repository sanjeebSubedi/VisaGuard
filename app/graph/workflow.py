from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.graph.state import VisaGuardState


def build_compliance_workflow(
    *,
    timeline_node: Callable[[dict[str, Any]], dict[str, Any]],
    policy_node: Callable[[dict[str, Any]], dict[str, Any]],
    compliance_node: Callable[[dict[str, Any]], dict[str, Any]],
    checkpointer: Any | None = None,
):
    graph = StateGraph(VisaGuardState)
    graph.add_node("timeline", timeline_node)
    graph.add_node("policy", policy_node)
    graph.add_node("compliance", compliance_node)
    graph.add_edge(START, "timeline")
    graph.add_edge(START, "policy")
    graph.add_edge("timeline", "compliance")
    graph.add_edge("policy", "compliance")
    graph.add_edge("compliance", END)
    return graph.compile(checkpointer=checkpointer or InMemorySaver())
