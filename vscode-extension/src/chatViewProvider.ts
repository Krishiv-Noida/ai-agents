import * as vscode from 'vscode';

export class ChatViewProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'codeEditorAgent.chatView';
    private _view?: vscode.WebviewView;

    constructor(private readonly _extensionUri: vscode.Uri) {}

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'sendMessage': {
                    vscode.commands.executeCommand('codeEditorAgent.processPrompt', data.text);
                    break;
                }
                case 'insertCode': {
                    const editor = vscode.window.activeTextEditor;
                    if (editor) {
                        editor.edit((editBuilder) => {
                            editBuilder.insert(editor.selection.active, data.code);
                        });
                        vscode.window.showInformationMessage('Code inserted into editor.');
                    } else {
                        vscode.window.showWarningMessage('No active editor to insert code into.');
                    }
                    break;
                }
            }
        });
    }

    public postMessageToWebview(message: any) {
        if (this._view) {
            this._view.webview.postMessage(message);
        }
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Editor Agent</title>
    <style>
        body {
            font-family: var(--vscode-font-family, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif);
            font-size: var(--vscode-font-size, 13px);
            color: var(--vscode-foreground);
            background-color: var(--vscode-sideBar-background);
            padding: 10px;
            margin: 0;
            display: flex;
            flex-direction: column;
            height: 100vh;
            box-sizing: border-box;
        }
        #header {
            font-weight: 600;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--vscode-panel-border);
            padding-bottom: 6px;
        }
        #status-tag {
            font-size: 11px;
            color: var(--vscode-testing-iconPassed);
        }
        #chat-messages {
            flex: 1;
            overflow-y: auto;
            margin-bottom: 10px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .msg {
            padding: 8px 10px;
            border-radius: 6px;
            line-height: 1.4;
            word-break: break-word;
        }
        .msg-user {
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            align-self: flex-end;
            max-width: 85%;
        }
        .msg-agent {
            background-color: var(--vscode-editor-background);
            border: 1px solid var(--vscode-widget-border);
            align-self: flex-start;
            max-width: 95%;
        }
        .msg-supervisor {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
            border-left: 2px solid var(--vscode-activityBarBadge-background);
            padding-left: 6px;
        }
        pre {
            background: var(--vscode-textCodeBlock-background);
            padding: 6px;
            border-radius: 4px;
            overflow-x: auto;
            font-family: var(--vscode-editor-font-family, monospace);
            font-size: 12px;
            position: relative;
        }
        .action-btn {
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
            border: none;
            padding: 3px 6px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 11px;
            margin-top: 4px;
        }
        .action-btn:hover {
            background: var(--vscode-button-secondaryHoverBackground);
        }
        #input-container {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        textarea {
            width: 100%;
            height: 70px;
            box-sizing: border-box;
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border: 1px solid var(--vscode-input-border);
            border-radius: 4px;
            padding: 6px;
            resize: vertical;
            font-family: inherit;
        }
        #send-btn {
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 6px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
        }
        #send-btn:hover {
            background: var(--vscode-button-hoverBackground);
        }
    </style>
</head>
<body>
    <div id="header">
        <span>🤖 Code Editor Agent</span>
        <span id="status-tag">Ready</span>
    </div>
    <div id="chat-messages">
        <div class="msg msg-agent">
            Hello! I am your AI Code Editor Agent. Ask me to create files, refactor existing code, or run test suites.
        </div>
    </div>
    <div id="input-container">
        <textarea id="prompt-input" placeholder="e.g. Create a file utils.py with string reverse..."></textarea>
        <button id="send-btn">Send to Agent</button>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        const chatMessages = document.getElementById('chat-messages');
        const promptInput = document.getElementById('prompt-input');
        const sendBtn = document.getElementById('send-btn');
        const statusTag = document.getElementById('status-tag');

        function appendMessage(text, role, isCode = false) {
            const div = document.createElement('div');
            div.className = 'msg msg-' + role;
            if (isCode) {
                const pre = document.createElement('pre');
                pre.textContent = text;
                const copyBtn = document.createElement('button');
                copyBtn.className = 'action-btn';
                copyBtn.textContent = 'Insert into Editor';
                copyBtn.onclick = () => {
                    vscode.postMessage({ type: 'insertCode', code: text });
                };
                div.appendChild(pre);
                div.appendChild(copyBtn);
            } else {
                div.textContent = text;
            }
            chatMessages.appendChild(div);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        sendBtn.addEventListener('click', () => {
            const text = promptInput.value.trim();
            if (!text) return;
            appendMessage(text, 'user');
            promptInput.value = '';
            statusTag.textContent = 'Agent Working...';
            statusTag.style.color = 'var(--vscode-charts-orange)';
            vscode.postMessage({ type: 'sendMessage', text: text });
        });

        promptInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                sendBtn.click();
            }
        });

        window.addEventListener('message', (event) => {
            const msg = event.data;
            if (msg.type === 'routing') {
                appendMessage('Supervisor -> ' + msg.nextWorker + ': ' + msg.reason, 'supervisor');
            } else if (msg.type === 'coderCompleted') {
                appendMessage(msg.summary, 'agent');
                if (msg.generatedCode) {
                    appendMessage(msg.generatedCode, 'agent', true);
                }
            } else if (msg.type === 'completed') {
                statusTag.textContent = 'Ready';
                statusTag.style.color = 'var(--vscode-testing-iconPassed)';
            } else if (msg.type === 'error') {
                appendMessage('Error: ' + msg.error, 'agent');
                statusTag.textContent = 'Error';
                statusTag.style.color = 'var(--vscode-errorForeground)';
            }
        });
    </script>
</body>
</html>`;
    }
}
