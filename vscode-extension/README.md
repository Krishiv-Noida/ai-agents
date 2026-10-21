# Code Editor Agent - VS Code Extension

An AI Code Editor Agent interface embedded directly inside VS Code, connected to your asynchronous LangGraph multi-agent backend.

---

## 🌟 Features

- **Sidebar AI Chat Panel**: Dedicated sidebar icon and chat panel for conversational editing, refactoring, and file generation.
- **Real-Time Streaming**: Streams live Supervisor routing events, Coder Agent progress, and verification results via Server-Sent Events (SSE).
- **One-Click Insert**: "Insert into Editor" button on generated code snippets to insert directly into your active editor.
- **Selection Refactoring**: Select code in any editor, press `Ctrl+Shift+P` (or `Cmd+Shift+P`), and run **`Code Editor Agent: Edit Current Selection`**.

---

## 🚀 Quickstart & Development

### 1. Ensure Backend is Running
The extension connects to your Django SSE orchestration endpoint at `http://127.0.0.1:8000/api/orchestrate/`:

```bash
# In your project root with virtualenv active:
source ../.venv/bin/activate
python manage.py runserver
```

### 2. Launch in VS Code
1. Open this `vscode-extension` directory in VS Code:
   ```bash
   code vscode-extension
   ```
2. Press **`F5`** (or go to `Run and Debug` -> `Run Extension`).
3. A new **Extension Development Host** VS Code window will open with the robot icon on the Activity Bar.
4. Click the robot icon to open the chat panel and start chatting with your Code Editor Agent!

---

## ⚙️ Configuration

In your VS Code `settings.json`:
```json
{
  "codeEditorAgent.apiUrl": "http://127.0.0.1:8000/api/orchestrate/"
}
```
