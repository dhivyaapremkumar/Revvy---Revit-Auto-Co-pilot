"""LangGraph definition for the voice agent's per-command turn.

Deliberately NOT langgraph.prebuilt.create_react_agent's opaque agent<->tools
loop -- built as an explicit StateGraph (agent -> tools -> agent -> ... ->
speak) so the graph is inspectable and visualizable
(`graph.get_graph().draw_mermaid()`), showing exactly how a transcribed
voice command flows through tool-calling to a spoken response. Wake-word
detection and audio I/O happen OUTSIDE this graph, in `main.py`'s loop --
this graph only covers "transcribed text in -> spoken response out".
"""
from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from agent.config import Settings

_SYSTEM_PROMPT = (
    "You are REVVY's voice-controlled Revit assistant. You have live tool "
    "access to the currently open Revit model over RevitMCP (view/model "
    "info, placing families, executing Revit API code, opening/saving "
    "documents) plus two REVVY-specific tools: ask_building_code (search "
    "the ingested Tamil Nadu Building Code, TNCDBR, for a cited answer or "
    "compliance check) and run_model_qa (a fixed check for naming issues, "
    "missing tags, stray CAD links, and unresolved model warnings). "
    "When asked to check compliance or 'run QA', always use those tools "
    "rather than answering from general knowledge -- never assert a "
    "TNCDBR clause or a QA result you haven't actually retrieved. Keep "
    "responses concise and speakable out loud: short sentences, no "
    "markdown, no code blocks, since your reply is converted to speech."
)


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_graph(settings: Settings, tools: list[BaseTool]):
    model = ChatOpenAI(model=settings.agent_model, api_key=settings.openai_api_key, temperature=0.2)
    model_with_tools = model.bind_tools(tools)

    async def agent_node(state: AgentState) -> AgentState:
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=_SYSTEM_PROMPT), *messages]
        response = await model_with_tools.ainvoke(messages)
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()
