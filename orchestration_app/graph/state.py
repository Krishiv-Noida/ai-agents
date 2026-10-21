"""
State definitions for the LangGraph hierarchical multi-agent workflow.
"""
from typing import Annotated, Any, Dict, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


def merge_worker_outputs(
    existing: Optional[Dict[str, Any]], 
    incoming: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Reducer function to merge worker outputs incrementally.
    
    Ensures that when any worker (coder_agent, browser_agent, sql_agent, booking_agent)
    writes to worker_outputs, previous worker outputs are preserved rather than overwritten.
    """
    merged = dict(existing or {})
    if incoming:
        merged.update(incoming)
    return merged


class AgentState(TypedDict):
    """
    Core state for the Hierarchical Multi-Agent System.
    
    Attributes:
        messages: Annotated list of conversation messages managed by add_messages reducer.
        next_worker: The scalable routing variable set by the supervisor.
                     Determines the next agent to execute (e.g., 'coder_agent', 'FINISH',
                     or future agents like 'browser_agent', 'sql_agent', 'booking_agent').
        worker_outputs: A scalable dictionary to store artifacts, code, and structured data
                        from any current or future worker agent (e.g. {"coder_agent": {"generated_code": "..."}}).
    """
    messages: Annotated[list, add_messages]
    next_worker: str
    worker_outputs: Annotated[dict, merge_worker_outputs]
