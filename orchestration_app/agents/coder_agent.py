"""
Coder Agent: Senior software engineering worker node for IDE and CLI workflows.
"""
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage, HumanMessage

from orchestration_app.graph.state import AgentState
from orchestration_app.prompts.coder_prompts import CODER_SYSTEM_PROMPT
from orchestration_app.tools.dev_tools import (
    read_file,
    write_file,
    edit_file,
    list_directory,
    run_terminal_command,
    execute_python_code,
)
from orchestration_app.agents.base import get_chat_model, is_mock_mode


CODER_TOOLS = [
    read_file,
    write_file,
    edit_file,
    list_directory,
    run_terminal_command,
    execute_python_code,
]
TOOL_MAP = {t.name: t for t in CODER_TOOLS}


def _format_content(content: Any) -> str:
    """Safely extracts text string from string or multimodal/block-based content."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            elif isinstance(part, str):
                parts.append(part)
            else:
                parts.append(str(part))
        return "".join(parts)
    return str(content)


async def coder_node(state: AgentState) -> Dict[str, Any]:
    """
    Autonomous Coder / Code Editor worker node.
    
    Binds the full IDE toolset (reading, writing, editing files, terminal commands),
    processes user requests via an agentic loop, and saves structured artifacts to
    state['worker_outputs']['coder_agent'] before returning control to the supervisor.
    
    Args:
        state: The current AgentState dictionary.
        
    Returns:
        State update dictionary containing generated messages and updated worker_outputs.
    """
    messages = state.get("messages", [])

    if is_mock_mode():
        # Simulated run for offline testing and verification
        sample_code = (
            "def calculate_fibonacci(n: int) -> int:\n"
            "    \"\"\"Return the nth Fibonacci number.\"\"\"\n"
            "    if n <= 0:\n"
            "        return 0\n"
            "    elif n == 1:\n"
            "        return 1\n"
            "    a, b = 0, 1\n"
            "    for _ in range(2, n + 1):\n"
            "        a, b = b, a + b\n"
            "    return b\n\n"
            "# Verification test\n"
            "assert calculate_fibonacci(10) == 55\n"
            "print(f'Fibonacci(10) = {calculate_fibonacci(10)}')"
        )
        tool_output = await execute_python_code.ainvoke({"code": sample_code})

        coder_response_text = (
            "Here is the verified Python solution implemented according to specifications:\n\n"
            f"```python\n{sample_code}\n```\n\n"
            f"**Execution & Test Verification:**\n```\n{tool_output}\n```"
        )

        coder_message = AIMessage(content=coder_response_text, name="coder_agent")

        return {
            "messages": [coder_message],
            "worker_outputs": {
                "coder_agent": {
                    "generated_code": sample_code,
                    "execution_status": "success",
                    "execution_output": tool_output,
                    "summary": coder_response_text,
                    "files_modified": [],
                    "commands_run": [],
                }
            },
        }

    # Production LLM workflow with bound IDE toolset
    llm = get_chat_model(temperature=0.2)
    llm_with_tools = llm.bind_tools(CODER_TOOLS)

    formatted_messages = list(messages)
    if formatted_messages and isinstance(formatted_messages[-1], AIMessage):
        formatted_messages.append(
            HumanMessage(
                content="Please fulfill the assigned coding or file editing task using the available tools."
            )
        )

    current_prompt = [SystemMessage(content=CODER_SYSTEM_PROMPT)] + formatted_messages
    generated_messages: List[Any] = []
    files_modified: List[str] = []
    commands_run: List[str] = []
    execution_result = ""
    generated_code = ""

    # Multi-step agent loop (up to 8 steps to allow inspect -> edit -> test -> verify)
    max_steps = 8
    for _ in range(max_steps):
        response = await llm_with_tools.ainvoke(current_prompt)
        generated_messages.append(response)
        current_prompt.append(response)

        if not response.tool_calls:
            # Model finished thinking and tool calling
            break

        for tool_call in response.tool_calls:
            t_name = tool_call["name"]
            t_args = tool_call.get("args", {})
            tool_fn = TOOL_MAP.get(t_name)

            if tool_fn:
                try:
                    tool_output = await tool_fn.ainvoke(t_args)
                except Exception as exc:
                    tool_output = f"[Error executing {t_name}]: {exc}"
            else:
                tool_output = f"[Error]: Tool '{t_name}' not found."

            output_str = str(tool_output)

            # Track files and commands
            if t_name in ("write_file", "edit_file"):
                fpath = t_args.get("filepath", "")
                if fpath and fpath not in files_modified:
                    files_modified.append(fpath)
                if "content" in t_args:
                    generated_code = t_args["content"]
            elif t_name == "run_terminal_command":
                cmd = t_args.get("command", "")
                if cmd:
                    commands_run.append(cmd)
                execution_result += f"\n{output_str}\n"
            elif t_name == "execute_python_code":
                code_arg = t_args.get("code", "")
                if code_arg:
                    generated_code = code_arg
                execution_result += f"\n{output_str}\n"

            tool_msg = ToolMessage(
                content=output_str,
                tool_call_id=tool_call["id"],
                name=t_name,
            )
            generated_messages.append(tool_msg)
            current_prompt.append(tool_msg)

    # Extract final text summary
    last_ai = next((m for m in reversed(generated_messages) if isinstance(m, AIMessage) and not m.tool_calls), None)
    if last_ai and last_ai.content:
        summary_text = _format_content(last_ai.content)
    else:
        summary_text = _format_content(generated_messages[-1].content) if generated_messages else "Code editing task completed."

    if not generated_code:
        generated_code = summary_text

    worker_output_payload = {
        "coder_agent": {
            "generated_code": generated_code,
            "execution_output": execution_result.strip(),
            "summary": summary_text,
            "files_modified": files_modified,
            "commands_run": commands_run,
            "status": "completed",
        }
    }

    return {
        "messages": generated_messages,
        "worker_outputs": worker_output_payload,
    }
