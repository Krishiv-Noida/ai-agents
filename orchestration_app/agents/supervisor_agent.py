"""
Supervisor Agent: Task router and delegation coordinator.
"""
from typing import Literal, Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage



from orchestration_app.graph.state import AgentState
from orchestration_app.prompts.supervisor_prompts import SUPERVISOR_SYSTEM_PROMPT
from orchestration_app.agents.base import get_chat_model, is_mock_mode


# Extensible Worker Registry:
# To add future workers (browser_agent, sql_agent, booking_agent):
# 1. Add the string literal to WorkerChoice below.
# 2. Add the worker node to workflow.py.
WorkerChoice = Literal[
    "coder_agent",
    "FINISH",
    # Scalable expansion candidates:
    # "browser_agent",
    # "sql_agent",
    # "booking_agent",
]


class SupervisorDecision(BaseModel):
    """
    Structured output schema for the Supervisor routing decision.
    Ensures that the LLM strictly responds with a valid next_worker value.
    """
    next_worker: WorkerChoice = Field(
        ...,
        description="The next specialized worker agent to invoke ('coder_agent') or 'FINISH' if complete."
    )
    reasoning: str = Field(
        ...,
        description="Clear explanation justifying the routing decision based on state and user goal."
    )


async def supervisor_node(state: AgentState) -> Dict[str, Any]:
    """
    Supervisor Agent node.
    
    Evaluates current messages and worker_outputs using structured output
    to determine the next_worker routing target.
    
    Args:
        state: The shared AgentState dictionary.
        
    Returns:
        State update dictionary containing 'next_worker' and an informational supervisor message.
    """
    messages = state.get("messages", [])
    worker_outputs = state.get("worker_outputs", {})

    if is_mock_mode():
        # Offline / Mock routing flow:
        # If coder_agent has already executed and placed output in state, finish.
        if "coder_agent" in worker_outputs:
            decision = SupervisorDecision(
                next_worker="FINISH",
                reasoning="The coder_agent has successfully generated and verified the requested code."
            )
        else:
            decision = SupervisorDecision(
                next_worker="coder_agent",
                reasoning="Routing to coder_agent to fulfill code generation and execution request."
            )
    else:
        # Production LLM routing with structured output
        llm = get_chat_model(temperature=0.0)
        structured_llm = llm.with_structured_output(SupervisorDecision)
        
        system_instruction = SUPERVISOR_SYSTEM_PROMPT
        if worker_outputs:
            system_instruction += (
                f"\n\nCURRENT WORKER OUTPUTS IN STATE:\n"
                f"{worker_outputs}\n"
                f"If the requested task has been satisfactorily fulfilled by the workers above, choose 'FINISH'."
            )
            
        formatted_messages = list(messages)
        if formatted_messages and isinstance(formatted_messages[-1], AIMessage):
            formatted_messages.append(
                HumanMessage(
                    content="Review the worker's completed output above. Decide if the user's request is fulfilled ('FINISH') or requires another worker."
                )
            )

        prompt = [SystemMessage(content=system_instruction)] + formatted_messages
        decision: SupervisorDecision = await structured_llm.ainvoke(prompt)


    router_message = AIMessage(
        content=f"[Supervisor Router]: Selected '{decision.next_worker}'. Reason: {decision.reasoning}",
        name="supervisor"
    )

    return {
        "next_worker": decision.next_worker,
        "messages": [router_message],
    }
