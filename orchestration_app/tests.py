"""
Automated tests for the Hierarchical Multi-Agent System.
"""
import json
import asyncio
from django.test import TestCase, AsyncRequestFactory, override_settings
from langchain_core.messages import HumanMessage
from langgraph.graph import END

from orchestration_app.graph.state import AgentState, merge_worker_outputs
from orchestration_app.tools.dev_tools import (
    execute_python_code,
    read_file,
    write_file,
    edit_file,
    list_directory,
    run_terminal_command,
)
from orchestration_app.agents.supervisor_agent import supervisor_node, SupervisorDecision
from orchestration_app.agents.coder_agent import coder_node
from orchestration_app.graph.workflow import app, route_supervisor
from orchestration_app.views import orchestrate_chat


@override_settings(MOCK_AGENT_MODE=True)
class MultiAgentSystemTests(TestCase):

    """Test suite for agent state, tools, graph routing, and Django view."""

    def test_state_reducer(self):
        """Verify that merge_worker_outputs reducer preserves and merges multi-worker artifacts."""
        initial_outputs = {"existing_agent": {"data": "val1"}}
        new_outputs = {"coder_agent": {"generated_code": "def hello(): pass"}}
        
        merged = merge_worker_outputs(initial_outputs, new_outputs)
        self.assertIn("existing_agent", merged)
        self.assertIn("coder_agent", merged)
        self.assertEqual(merged["coder_agent"]["generated_code"], "def hello(): pass")

    def test_execute_python_code_tool(self):
        """Verify that execute_python_code simulates execution success."""
        code_snippet = "print('Hello, Multi-Agent World!')"
        result = execute_python_code.invoke({"code": code_snippet})
        self.assertIn("[EXECUTION SUCCESSFUL]", result)
        self.assertIn("Exit Code: 0", result)

    def test_file_editing_tools(self):
        """Verify read_file, write_file, edit_file, and list_directory tools."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "sample.py")
            
            # 1. Write file
            w_res = write_file.invoke({
                "filepath": test_file,
                "content": "def greet(name):\n    return f'Hello, {name}'\n"
            })
            self.assertIn("[SUCCESS]", w_res)
            self.assertTrue(os.path.exists(test_file))

            # 2. Read file
            r_res = read_file.invoke({"filepath": test_file})
            self.assertIn("def greet(name):", r_res)
            self.assertIn("1 |", r_res)

            # 3. Edit file (surgical search & replace)
            e_res = edit_file.invoke({
                "filepath": test_file,
                "target": "return f'Hello, {name}'",
                "replacement": "return f'Welcome, {name}!'"
            })
            self.assertIn("[SUCCESS]", e_res)
            self.assertIn("+    return f'Welcome, {name}!'", e_res)

            # Verify edited file contents
            r_after = read_file.invoke({"filepath": test_file})
            self.assertIn("Welcome", r_after)
            self.assertNotIn("Hello", r_after)

            # 4. List directory
            list_res = list_directory.invoke({"path": tmpdir})
            self.assertIn("sample.py", list_res)

    def test_run_terminal_command_tool(self):
        """Verify run_terminal_command executes shell commands safely."""
        res = run_terminal_command.invoke({"command": "echo 'MULTI_AGENT_IDE_TEST'"})
        self.assertIn("[COMMAND EXITED WITH CODE 0]", res)
        self.assertIn("MULTI_AGENT_IDE_TEST", res)

    def test_supervisor_decision_schema(self):
        """Verify the SupervisorDecision Pydantic schema validation."""
        decision = SupervisorDecision(
            next_worker="coder_agent",
            reasoning="Testing code routing."
        )
        self.assertEqual(decision.next_worker, "coder_agent")

        decision_finish = SupervisorDecision(
            next_worker="FINISH",
            reasoning="Testing completion."
        )
        self.assertEqual(decision_finish.next_worker, "FINISH")

    def test_route_supervisor_logic(self):
        """Verify routing function correctly translates next_worker to node or END."""
        state_coder: AgentState = {
            "messages": [],
            "next_worker": "coder_agent",
            "worker_outputs": {}
        }
        self.assertEqual(route_supervisor(state_coder), "coder_agent")

        state_finish: AgentState = {
            "messages": [],
            "next_worker": "FINISH",
            "worker_outputs": {}
        }
        self.assertEqual(route_supervisor(state_finish), END)

        state_empty: AgentState = {
            "messages": [],
            "next_worker": "",
            "worker_outputs": {}
        }
        self.assertEqual(route_supervisor(state_empty), END)

    def test_end_to_end_graph_execution(self):
        """Test the compiled LangGraph workflow execution with supervisor and coder."""
        async def run_flow():
            config = {"configurable": {"thread_id": "test-flow-1"}}
            inputs = {
                "messages": [HumanMessage(content="Write a Python function to compute factorial.")],
                "next_worker": "",
                "worker_outputs": {},
            }
            steps = []
            async for chunk in app.astream(inputs, config=config, stream_mode="updates"):
                steps.append(chunk)
            return steps

        steps = asyncio.run(run_flow())
        
        # We expect 3 distinct node update steps:
        # 1. supervisor routes to coder_agent
        # 2. coder_agent generates code & saves worker_outputs
        # 3. supervisor reviews worker_outputs and selects FINISH
        self.assertTrue(len(steps) >= 3)
        
        step_nodes = [list(step.keys())[0] for step in steps]
        self.assertEqual(step_nodes[0], "supervisor")
        self.assertEqual(step_nodes[1], "coder_agent")
        self.assertEqual(step_nodes[2], "supervisor")

        # Verify coder_agent updated worker_outputs properly
        coder_step_update = steps[1]["coder_agent"]
        self.assertIn("worker_outputs", coder_step_update)
        self.assertIn("coder_agent", coder_step_update["worker_outputs"])
        self.assertIn("generated_code", coder_step_update["worker_outputs"]["coder_agent"])

    def test_orchestrate_chat_view_streaming(self):
        """Test async orchestrate_chat Django view and SSE streaming output."""
        async def run_view_test():
            factory = AsyncRequestFactory()
            payload = {
                "message": "Implement and test quicksort in Python",
                "thread_id": "unit-test-session"
            }
            request = factory.post(
                "/api/orchestrate/",
                data=json.dumps(payload),
                content_type="application/json"
            )
            
            response = await orchestrate_chat(request)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["Content-Type"], "text/event-stream")

            # Collect streaming chunks
            chunks = []
            async for chunk in response.streaming_content:
                chunks.append(chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk)

            full_stream = "".join(chunks)
            self.assertIn("started", full_stream)
            self.assertIn("node_update", full_stream)
            self.assertIn("completed", full_stream)
            self.assertIn("coder_agent", full_stream)
            return full_stream

        asyncio.run(run_view_test())
