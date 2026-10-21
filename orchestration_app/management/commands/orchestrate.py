"""
Django management command to run the multi-agent system directly from the CLI.
Supports both single-shot prompts and an interactive REPL mode.
"""
import asyncio
import os
import sys
import uuid
from django.core.management.base import BaseCommand
from langchain_core.messages import HumanMessage

from orchestration_app.graph.workflow import app


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


class Command(BaseCommand):
    help = "Run the Hierarchical Multi-Agent System via command-line interface (CLI)."

    def add_arguments(self, parser):
        parser.add_argument(
            "message",
            nargs="?",
            type=str,
            default=None,
            help="Prompt/instruction for the multi-agent system. If omitted, starts an interactive REPL.",
        )
        parser.add_argument(
            "--thread-id",
            type=str,
            default=None,
            help="Session thread ID for conversation memory across turns.",
        )
        parser.add_argument(
            "--mock",
            action="store_true",
            help="Force mock execution mode (offline deterministic test without API calls).",
        )
        parser.add_argument(
            "--dir",
            "-d",
            type=str,
            default=None,
            help="Target workspace directory to inspect and edit (defaults to current folder).",
        )

    def handle(self, *args, **options):
        if options["mock"]:
            os.environ["MOCK_AGENT_MODE"] = "true"

        if options.get("dir"):
            target_dir = os.path.abspath(options["dir"])
            os.environ["CODEAGENT_WORKSPACE"] = target_dir
        elif "CODEAGENT_WORKSPACE" not in os.environ:
            os.environ["CODEAGENT_WORKSPACE"] = os.getcwd()

        workspace = os.environ["CODEAGENT_WORKSPACE"]
        thread_id = options["thread_id"] or str(uuid.uuid4())[:8]
        message = options["message"]

        if message:
            # Single-shot CLI execution
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n🚀 Running task in session: [{thread_id}]"))
            self.stdout.write(self.style.NOTICE(f"📁 Target Workspace: {workspace}\n"))
            asyncio.run(self._run_prompt(message, thread_id))
        else:
            # Interactive multi-turn REPL mode
            self.stdout.write(self.style.SUCCESS("\n========================================================"))
            self.stdout.write(self.style.SUCCESS("🤖 Code Editor Agent CLI (Multi-Agent)"))
            self.stdout.write(self.style.SUCCESS(f"Session Thread ID: {thread_id}"))
            self.stdout.write(self.style.NOTICE(f"📁 Target Workspace: {workspace}"))
            self.stdout.write("Type your prompt and press Enter. Type 'exit' or 'quit' to stop.")
            self.stdout.write(self.style.SUCCESS("========================================================\n"))

            while True:
                try:
                    user_input = input("\nYou > ").strip()
                except (EOFError, KeyboardInterrupt):
                    self.stdout.write("\nExiting CLI.")
                    break

                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit", "q"):
                    self.stdout.write("Goodbye!")
                    break

                asyncio.run(self._run_prompt(user_input, thread_id))

    async def _run_prompt(self, user_message: str, thread_id: str):
        inputs = {
            "messages": [HumanMessage(content=user_message)],
            "next_worker": "",
            "worker_outputs": {},
        }
        config = {"configurable": {"thread_id": thread_id}}

        self.stdout.write(self.style.WARNING("⚡ Executing multi-agent workflow...\n"))

        try:
            async for chunk in app.astream(inputs, config=config, stream_mode="updates"):
                for node_name, node_update in chunk.items():
                    if node_name == "supervisor":
                        next_worker = node_update.get("next_worker")
                        msgs = node_update.get("messages", [])
                        reason = msgs[-1].content if msgs else ""
                        self.stdout.write(self.style.SUCCESS(f"🔹 [Supervisor]: Routing to -> {next_worker}"))
                        if reason:
                            self.stdout.write(f"   {reason}\n")

                    elif node_name == "coder_agent":
                        worker_outputs = node_update.get("worker_outputs", {}).get("coder_agent", {})
                        summary = worker_outputs.get("summary")
                        exec_out = worker_outputs.get("execution_output")
                        files_modified = worker_outputs.get("files_modified", [])
                        commands_run = worker_outputs.get("commands_run", [])

                        self.stdout.write(self.style.MIGRATE_LABEL("💻 [Coder Agent]: Completed work."))
                        if files_modified:
                            self.stdout.write(self.style.SUCCESS(f"   📁 Files Modified/Created: {', '.join(files_modified)}"))
                        if commands_run:
                            self.stdout.write(self.style.NOTICE(f"   ⚡ Terminal Commands: {', '.join(commands_run)}"))
                        if exec_out:
                            self.stdout.write(self.style.NOTICE("\n--- Code & Verification Output ---"))
                            self.stdout.write(exec_out)
                            self.stdout.write(self.style.NOTICE("----------------------------------\n"))
                        if summary:
                            self.stdout.write(f"\n{summary}\n")
                        else:
                            for msg in node_update.get("messages", []):
                                content = _format_content(getattr(msg, "content", msg))
                                self.stdout.write(content)

            self.stdout.write(self.style.SUCCESS(f"\n✅ Task completed for thread: [{thread_id}]"))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"\n❌ Error during execution: {exc}"))
