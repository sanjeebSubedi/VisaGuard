from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph


def build_dso_workflow(*, state_loader_node: Callable[[dict[str, Any]], dict[str, Any]], intent_router_node: Callable[[dict[str, Any]], dict[str, Any]], context_retriever_node: Callable[[dict[str, Any]], dict[str, Any]], synthesizer_node: Callable[[dict[str, Any]], dict[str, Any]]):
    graph = StateGraph(dict)
    graph.add_node('state_loader', state_loader_node)
    graph.add_node('intent_router', intent_router_node)
    graph.add_node('context_retriever', context_retriever_node)
    graph.add_node('synthesizer', synthesizer_node)
    graph.add_edge(START, 'state_loader')
    graph.add_edge('state_loader', 'intent_router')
    graph.add_edge('intent_router', 'context_retriever')
    graph.add_edge('context_retriever', 'synthesizer')
    graph.add_edge('synthesizer', END)
    return graph.compile()
