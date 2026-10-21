import * as vscode from 'vscode';
import * as http from 'http';
import { ChatViewProvider } from './chatViewProvider';

let threadId = 'vscode-' + Math.random().toString(36).substring(2, 9);

export function activate(context: vscode.ExtensionContext) {
    const provider = new ChatViewProvider(context.extensionUri);

    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(ChatViewProvider.viewType, provider)
    );

    // Command: Open Chat
    context.subscriptions.push(
        vscode.commands.registerCommand('codeEditorAgent.openChat', () => {
            vscode.commands.executeCommand('workbench.view.extension.code-editor-agent-sidebar');
        })
    );

    // Command: Edit Selection
    context.subscriptions.push(
        vscode.commands.registerCommand('codeEditorAgent.sendSelection', () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor selected.');
                return;
            }
            const selection = editor.document.getText(editor.selection);
            if (!selection) {
                vscode.window.showWarningMessage('No code selected in the active editor.');
                return;
            }
            const filename = editor.document.fileName;
            const prompt = `Inspect the following code from ${filename} and improve/refactor it:\n\n\`\`\`\n${selection}\n\`\`\``;
            vscode.commands.executeCommand('codeEditorAgent.processPrompt', prompt);
        })
    );

    // Internal command: Process prompt through backend SSE endpoint
    context.subscriptions.push(
        vscode.commands.registerCommand('codeEditorAgent.processPrompt', (prompt: string) => {
            const config = vscode.workspace.getConfiguration('codeEditorAgent');
            const apiUrl = config.get<string>('apiUrl', 'http://127.0.0.1:8000/api/orchestrate/');

            const url = new URL(apiUrl);
            const payload = JSON.stringify({
                message: prompt,
                thread_id: threadId
            });

            const req = http.request(
                {
                    hostname: url.hostname,
                    port: url.port || 80,
                    path: url.pathname,
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Content-Length': Buffer.byteLength(payload)
                    }
                },
                (res) => {
                    let buffer = '';

                    res.on('data', (chunk) => {
                        buffer += chunk.toString();
                        const lines = buffer.split('\n');
                        buffer = lines.pop() || '';

                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                try {
                                    const eventData = JSON.parse(line.substring(6));
                                    handleSSEEvent(eventData, provider);
                                } catch (e) {
                                    // Non-JSON SSE event
                                }
                            }
                        }
                    });

                    res.on('end', () => {
                        provider.postMessageToWebview({ type: 'completed' });
                    });
                }
            );

            req.on('error', (err) => {
                provider.postMessageToWebview({
                    type: 'error',
                    error: `Failed to connect to backend at ${apiUrl}. Make sure Django server is running (python manage.py runserver). Error: ${err.message}`
                });
            });

            req.write(payload);
            req.end();
        })
    );
}

function handleSSEEvent(eventData: any, provider: ChatViewProvider) {
    if (eventData.event === 'node_update') {
        if (eventData.node === 'supervisor') {
            const msgs = eventData.messages || [];
            const reason = msgs.length > 0 ? msgs[msgs.length - 1].content : '';
            provider.postMessageToWebview({
                type: 'routing',
                nextWorker: eventData.next_worker,
                reason: reason
            });
        } else if (eventData.node === 'coder_agent') {
            const coderOut = eventData.worker_outputs?.coder_agent || {};
            provider.postMessageToWebview({
                type: 'coderCompleted',
                summary: coderOut.summary || 'Coder Agent finished changes.',
                generatedCode: coderOut.generated_code || ''
            });
        }
    } else if (eventData.event === 'completed') {
        provider.postMessageToWebview({ type: 'completed' });
    }
}

export function deactivate() {}
