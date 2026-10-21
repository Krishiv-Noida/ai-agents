#!/usr/bin/env python
"""
Model Context Protocol (MCP) Server for the Code Editor Agent.

Exposes the Hierarchical Multi-Agent System and its workspace tools over MCP (stdio).
Compatible with VS Code (Cline, Roo, Continue), Cursor, Windsurf, Claude Desktop, and Antigravity.
"""
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

# Ensure project root is in Python path and Django settings are loaded
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core_project.settings")

import django
django.setup()

from langchain_core.messages import HumanMessage
from mcp.server.mcpserver import MCPServer

from orchestration_app.graph.workflow import app
from orchestration_app.tools.dev_tools import (
    read_file as _read_file_tool,
    write_file as _write_file_tool,
    edit_file as _edit_file_tool,
    list_directory as _list_directory_tool,
    run_terminal_command as _run_terminal_command_tool,
)

server = MCPServer("code-editor-agent")


def _format_content(content) -> str:
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


@server.tool()
async def orchestrate_coding_task(prompt: str, thread_id: Optional[str] = None) -> str:
    """
    Runs the autonomous multi-agent coding workflow on a prompt or task description.
    
    The Supervisor routes the task to the Coder Agent, which autonomously inspects
    files, creates or edits code using surgical diffs, runs tests, and verifies the solution.
    
    Args:
        prompt: The software engineering task, bug report, or editing instruction.
        thread_id: Optional thread ID to maintain conversational memory across turns.
        
    Returns:
        Structured summary of the completed work, including files modified and test results.
    """
    session_id = thread_id or str(uuid.uuid4())[:8]
    inputs = {
        "messages": [HumanMessage(content=prompt)],
        "next_worker": "",
        "worker_outputs": {},
    }
    config = {"configurable": {"thread_id": session_id}}

    coder_summary = ""
    files_modified = []
    commands_run = []
    exec_out = ""

    async for chunk in app.astream(inputs, config=config, stream_mode="updates"):
        for node_name, node_update in chunk.items():
            if node_name == "coder_agent":
                worker_outputs = node_update.get("worker_outputs", {}).get("coder_agent", {})
                coder_summary = worker_outputs.get("summary", "")
                exec_out = worker_outputs.get("execution_output", "")
                files_modified.extend(worker_outputs.get("files_modified", []))
                commands_run.extend(worker_outputs.get("commands_run", []))

    response_lines = [
        f"### Code Editor Agent Task Completed [Session: {session_id}]",
        "",
    ]
    if files_modified:
        response_lines.append(f"**Files Created / Modified:** {', '.join(set(files_modified))}")
    if commands_run:
        response_lines.append(f"**Commands Executed:** {', '.join(commands_run)}")
    if exec_out:
        response_lines.extend(["", "```text", exec_out, "```"])
    if coder_summary:
        response_lines.extend(["", coder_summary])

    return "\n".join(response_lines)


@server.tool()
def read_file(filepath: str, start_line: int = 1, end_line: int = -1) -> str:
    """
    Reads workspace file content with line numbers.
    
    Args:
        filepath: Relative or absolute path to the file.
        start_line: 1-indexed starting line number.
        end_line: 1-indexed ending line number (-1 for end of file).
    """
    return _read_file_tool.invoke({"filepath": filepath, "start_line": start_line, "end_line": end_line})


@server.tool()
def write_file(filepath: str, content: str) -> str:
    """
    Creates or overwrites a file in the workspace with given content.
    
    Args:
        filepath: Path to the file to create or overwrite.
        content: Full text or code content to write.
    """
    return _write_file_tool.invoke({"filepath": filepath, "content": content})


@server.tool()
def edit_file(filepath: str, target: str, replacement: str) -> str:
    """
    Applies a surgical search-and-replace modification to a workspace file.
    
    Args:
        filepath: Path to the target file.
        target: Exact text block to replace (must match whitespace and indentation).
        replacement: New text block to insert.
    """
    return _edit_file_tool.invoke({"filepath": filepath, "target": target, "replacement": replacement})


@server.tool()
def list_directory(path: str = ".", max_depth: int = 2) -> str:
    """
    Lists files and directories in the workspace, filtering out caches and virtual environments.
    
    Args:
        path: Directory path to inspect (default: workspace root).
        max_depth: Maximum recursion depth.
    """
    return _list_directory_tool.invoke({"path": path, "max_depth": max_depth})


@server.tool()
def run_terminal_command(command: str) -> str:
    """
    Executes a shell command in the project root and returns stdout, stderr, and exit code.
    
    Args:
        command: Bash command to run (e.g. 'pytest', 'python manage.py test').
    """
    return _run_terminal_command_tool.invoke({"command": command})


if __name__ == "__main__":
    server.run(transport="stdio")
