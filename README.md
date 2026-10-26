# Kairo: Autonomous AI Code Editor Agent & CLI (Django + LangGraph)

**Kairo** is an autonomous, scalable AI Code Editor Agent built with **Django (ASGI)** and **LangGraph**. Designed as a next-generation software engineering assistant, Kairo can inspect repositories, apply surgical search-and-replace edits, execute terminal test suites, self-correct errors, and seamlessly integrate into IDEs via CLI, MCP, and a native VS Code extension.

---

## 📁 Project Structure

```text
my_multi_agent_project/
├── core_project/                   # Django project configuration
│   ├── __init__.py
│   ├── asgi.py                     # Configured for asynchronous execution
│   ├── settings.py                 # Django settings registering orchestration_app
│   ├── urls.py                     # Root routing directing /api/ to orchestration_app
│   └── wsgi.py                     # WSGI entrypoint
├── orchestration_app/              # Django application managing LLM logic
│   ├── __init__.py
│   ├── apps.py                     # App configuration
│   ├── urls.py                     # Endpoint routing (/api/orchestrate/)
│   ├── views.py                    # Async Django view with SSE StreamingHttpResponse
│   ├── tests.py                    # Comprehensive test suite
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py                # TypedDict for LangGraph state with worker_outputs reducer
│   │   └── workflow.py             # StateGraph compilation, routing edges & MemorySaver
│   ├── agents/                     # Isolated agent definitions
│   │   ├── __init__.py
│   │   ├── base.py                 # Shared LLM factories and utilities
│   │   ├── supervisor_agent.py     # Main router using structured output
│   │   └── coder_agent.py          # Software engineering worker with tool bindings
│   ├── tools/                      # Shared tools library
│   │   ├── __init__.py
│   │   └── dev_tools.py            # execute_python_code tool
│   └── prompts/                    # Modular prompt library
│       ├── __init__.py
│       ├── supervisor_prompts.py   # Supervisor routing instructions
│       └── coder_prompts.py        # Senior software engineer worker instructions
├── cli.py                          # Global CLI entrypoint (`kairo` / `codeagent`)
├── mcp_server.py                   # Model Context Protocol (MCP) server for Kairo
├── vscode-extension/               # Native Kairo VS Code Extension with live SSE streaming
├── pyproject.toml                  # Standard packaging manifest for pip/pipx installation
├── manage.py                       # Django administrative CLI
├── requirements.txt                # Project dependencies
└── .env.example                    # Environment variable configuration template
```

---

## 🚀 Key Architectural Features

### 1. Scalable State Management (`state.py`)
- `AgentState` contains:
  - `messages`: `Annotated[list, add_messages]` tracking conversational turns.
  - `next_worker`: Scalable routing variable set by the supervisor (`'coder_agent'`, `'FINISH'`, etc.).
  - `worker_outputs`: Managed with an incremental merge reducer so workers (`coder_agent`, `browser_agent`, etc.) store structured outputs without overwriting each other.

### 2. Supervisor Structured Routing (`supervisor_agent.py`)
- Uses `with_structured_output(SupervisorDecision)` ensuring guaranteed, type-safe routing.
- Evaluates conversation messages and existing `worker_outputs`.

### 3. Coder / IDE Editor Agent (`coder_agent.py` & `dev_tools.py`)
- Binds a full suite of IDE tools: `read_file`, `write_file`, `edit_file` (search-and-replace with diffs), `list_directory`, `run_terminal_command`, and `execute_python_code`.
- Implements an autonomous agentic loop to inspect source files, apply surgical edits, run test suites, self-correct errors, and save structured outputs to `worker_outputs["coder_agent"]`.

### 4. Zero-Restructure Extensibility (`workflow.py`)
To add a new worker (e.g. `browser_agent`):
1. **Define the node**: Create `browser_agent.py` with `browser_node(state)`.
2. **Register the node**: `workflow.add_node("browser_agent", browser_node)`.
3. **Map the route**: Add `"browser_agent": "browser_agent"` to the supervisor conditional routing map.
4. **Add return edge**: `workflow.add_edge("browser_agent", "supervisor")`.

No restructuring of graph logic or existing agents is needed!

### 5. Async Django & SSE Streaming (`views.py`)
- Endpoint: `POST /api/orchestrate/`
- Streams real-time Server-Sent Events (SSE) using `app.astream(..., stream_mode="updates")` and Django's `StreamingHttpResponse`.

---

## 🛠️ Setup & Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
The project is configured to use local **Meta Llama (Llama 3.2)** via Ollama without any cloud API keys:
```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```
*(Optional: Set `MOCK_AGENT_MODE=True` for offline deterministic testing).*

### 3. Run Database Migrations
```bash
python manage.py migrate
```

### 4. Run Automated Tests
```bash
python manage.py test orchestration_app
```

### 5. Start the Async Development Server
Run using Uvicorn (recommended for ASGI):
```bash
uvicorn core_project.asgi:application --host 0.0.0.0 --port 8000 --reload
```
Or with Django's native ASGI runner:
```bash
python manage.py runserver
```

---

## 💻 Global CLI Usage (`kairo`)

Once installed, you can use `kairo` in **any project or folder on your computer**:

### 1. Install Globally (Recommended)

Using **uv** (Recommended - installs globally into `~/.local/bin` without needing to activate a virtualenv):
```bash
uv tool install git+https://github.com/Krishiv-Noida/ai-agents.git
```

Or using standard **pip**:
```bash
pip install git+https://github.com/Krishiv-Noida/ai-agents.git
```

*(For local development in this repo: `pip install -e .`)*

### 2. Run in Any Directory
Navigate to any project on your computer:
```bash
cd /path/to/any-project
kairo "Add a new helper function to format dates in utils.py"
```
Kairo automatically detects the active folder and performs edits directly on that project's files!

### 3. Specify a Target Folder Explicitly
```bash
kairo --dir /path/to/my-other-project "Inspect package.json and run tests"
```

### 4. Interactive Chat Mode
Run without arguments to launch an interactive conversation:
```bash
kairo
```

---

## 📡 API Usage & Streaming Verification

### Request
Send a `POST` request with JSON payload:

```bash
curl -N -X POST http://127.0.0.1:8000/api/orchestrate/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Write a Python script to calculate Fibonacci numbers up to 10 and execute it.",
    "thread_id": "session-101"
  }'
```

### Streamed SSE Response
```text
data: {"event": "started", "thread_id": "session-101"}

data: {"event": "node_update", "node": "supervisor", "next_worker": "coder_agent", "worker_outputs": null, "messages": [{"sender": "supervisor", "content": "[Supervisor Router]: Selected 'coder_agent'. Reason: Routing to coder_agent to fulfill code generation and execution request."}]}

data: {"event": "node_update", "node": "coder_agent", "next_worker": null, "worker_outputs": {"coder_agent": {"generated_code": "...", "execution_status": "success", "summary": "..."}}, "messages": [{"sender": "coder_agent", "content": "Here is the verified Python solution..."}]}

data: {"event": "node_update", "node": "supervisor", "next_worker": "FINISH", "worker_outputs": null, "messages": [{"sender": "supervisor", "content": "[Supervisor Router]: Selected 'FINISH'. Reason: The coder_agent has successfully generated and verified the requested code."}]}

---

## 🔌 IDE Integration: Model Context Protocol (MCP)

Run the agent system as an MCP server so that IDEs like **Cursor**, **Windsurf**, **Claude Desktop**, or **VS Code (Cline / Roo / Continue)** can use it as a native tool:

### 1. Test MCP Server Locally
```bash
python mcp_server.py
```

### 2. IDE MCP Configuration (`settings.json` or `claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "kairo": {
      "command": "/home/nitin/Desktop/Agents_ecosystem/.venv/bin/python",
      "args": ["/home/nitin/Desktop/Agents_ecosystem/my_multi_agent_project/mcp_server.py"]
    }
  }
}
```

Exposed MCP Tools:
- `orchestrate_coding_task`: Autonomous multi-agent software engineering & file editing.
- `read_file`: Line-numbered workspace file inspection.
- `write_file`: File creation with auto parent directory creation.
- `edit_file`: Exact surgical search-and-replace modification with unified diffs.
- `list_directory`: Workspace tree listing.
- `run_terminal_command`: Test runner and shell command executor.

---

## 💻 Native VS Code Extension

A dedicated VS Code extension is available in [`vscode-extension/`](vscode-extension/):

1. **Start the Django Backend**:
   ```bash
   python manage.py runserver
   ```
2. **Launch Extension in VS Code**:
   ```bash
   cd vscode-extension
   code .
   ```
3. Press **`F5`** to launch the Extension Development Host.
4. Use the robot icon in the Activity Bar to chat, refactor code, and insert generated changes with one click.

