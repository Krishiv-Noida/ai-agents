"""
LangGraph workflow compilation and graph orchestration.
"""
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from orchestration_app.graph.state import AgentState
from orchestration_app.agents.supervisor_agent import supervisor_node
from orchestration_app.agents.coder_agent import coder_node


def route_supervisor(state: AgentState) -> str:
    """
    Evaluates the 'next_worker' state variable set by the supervisor node.
    Routes execution to the designated worker node or to END.
    
    Args:
        state: The current AgentState dictionary.
        
    Returns:
        The target node name ('coder_agent', 'browser_agent', etc.) or END.
    """
    next_worker = state.get("next_worker")
    if not next_worker or next_worker == "FINISH":
        return END
    return next_worker


def build_workflow() -> StateGraph:
    """
    Constructs the StateGraph with scalable node registrations and edges.
    
    Extensibility Guide:
    To register new worker agents (e.g. 'browser_agent', 'sql_agent', 'booking_agent'):
      1. Add node: workflow.add_node("browser_agent", browser_node)
      2. Add routing map: WORKER_ROUTING_MAP["browser_agent"] = "browser_agent"
      3. Add return edge: workflow.add_edge("browser_agent", "supervisor")
    """
    workflow = StateGraph(AgentState)

    # 1. Register agent nodes with exact identifiers
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("coder_agent", coder_node)

    # Future workers can be registered identically:
    # workflow.add_node("browser_agent", browser_node)
    # workflow.add_node("sql_agent", sql_node)
    # workflow.add_node("booking_agent", booking_node)

    # 2. Set the hierarchical entry point to the supervisor
    workflow.set_entry_point("supervisor")

    # 3. Dynamic conditional routing from the supervisor based on 'next_worker'
    worker_routing_map = {
        "coder_agent": "coder_agent",
        END: END,
        # Future workers map seamlessly:
        # "browser_agent": "browser_agent",
        # "sql_agent": "sql_agent",
        # "booking_agent": "booking_agent",
    }

    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        worker_routing_map,
    )

    # 4. Deterministic edge returning control from worker agents back to supervisor
    workflow.add_edge("coder_agent", "supervisor")

    # Future workers similarly report back to the supervisor:
    # workflow.add_edge("browser_agent", "supervisor")
    # workflow.add_edge("sql_agent", "supervisor")
    # workflow.add_edge("booking_agent", "supervisor")

    return workflow


# In-memory checkpointer for conversational thread persistence
checkpointer = MemorySaver()

# Compile the runnable graph application
app = build_workflow().compile(checkpointer=checkpointer)
