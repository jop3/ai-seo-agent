"""
Simple web-based chat UI for local development.

Run with: seo-agent ui
"""

import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="SEO Agent Chat UI")


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SEO Agent Chat</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        header {
            background: #16213e;
            padding: 1rem 2rem;
            border-bottom: 1px solid #0f3460;
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        header h1 { font-size: 1.25rem; }
        header select {
            background: #0f3460;
            color: #eee;
            border: 1px solid #e94560;
            padding: 0.5rem;
            border-radius: 4px;
            cursor: pointer;
        }
        .status {
            margin-left: auto;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.75rem;
        }
        .status.connected { background: #2e7d32; }
        .status.disconnected { background: #c62828; }

        #chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 1rem 2rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        .message {
            max-width: 80%;
            padding: 1rem;
            border-radius: 12px;
            line-height: 1.5;
        }
        .message.user {
            align-self: flex-end;
            background: #0f3460;
        }
        .message.agent {
            align-self: flex-start;
            background: #16213e;
            border: 1px solid #0f3460;
        }
        .message .agent-name {
            font-size: 0.75rem;
            color: #e94560;
            margin-bottom: 0.5rem;
        }
        .message .tools {
            font-size: 0.75rem;
            color: #888;
            margin-top: 0.5rem;
            border-top: 1px solid #333;
            padding-top: 0.5rem;
        }
        .message pre {
            background: #0d1117;
            padding: 0.75rem;
            border-radius: 6px;
            overflow-x: auto;
            margin: 0.5rem 0;
        }
        .message code {
            font-family: 'Fira Code', monospace;
            font-size: 0.875rem;
        }
        .thinking {
            color: #888;
            font-style: italic;
        }

        #input-container {
            background: #16213e;
            padding: 1rem 2rem;
            border-top: 1px solid #0f3460;
            display: flex;
            gap: 1rem;
        }
        #message-input {
            flex: 1;
            background: #0f3460;
            border: 1px solid #333;
            color: #eee;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-size: 1rem;
        }
        #message-input:focus {
            outline: none;
            border-color: #e94560;
        }
        button {
            background: #e94560;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            transition: background 0.2s;
        }
        button:hover { background: #c73e54; }
        button:disabled { background: #666; cursor: not-allowed; }

        .quick-actions {
            padding: 0.5rem 2rem;
            background: #16213e;
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        .quick-actions button {
            background: #0f3460;
            padding: 0.5rem 1rem;
            font-size: 0.875rem;
        }
        .quick-actions button:hover { background: #1a4a7d; }
    </style>
</head>
<body>
    <header>
        <h1>🔍 SEO Agent</h1>
        <select id="agent-select">
            <option value="seo-analyst">SEO Analyst</option>
            <option value="agent-tester">Agent Tester</option>
            <option value="monitoring-agent">Monitoring Agent</option>
            <option value="optimizer">Optimizer</option>
        </select>
        <span id="status" class="status disconnected">Disconnected</span>
    </header>

    <div class="quick-actions">
        <button onclick="sendQuick('Run full SEO analysis')">Full Analysis</button>
        <button onclick="sendQuick('Check AIO status for top queries')">Check AIO Status</button>
        <button onclick="sendQuick('Generate FAQ schema for the homepage')">Generate FAQ</button>
        <button onclick="sendQuick('Test page for agent compatibility')">Test Page</button>
        <button onclick="sendQuick('Show traffic anomalies')">Traffic Anomalies</button>
    </div>

    <div id="chat-container">
        <div class="message agent">
            <div class="agent-name">SEO Agent</div>
            Welcome! I'm your AI SEO Agent. I can help you:
            <ul style="margin: 0.5rem 0 0 1rem;">
                <li>Analyze your site's performance in AI Overviews</li>
                <li>Test pages for AI agent compatibility</li>
                <li>Generate optimized schema markup</li>
                <li>Monitor for traffic anomalies</li>
            </ul>
        </div>
    </div>

    <form id="input-container" onsubmit="sendMessage(event)">
        <input type="text" id="message-input" placeholder="Ask the SEO agent anything..." autocomplete="off">
        <button type="submit" id="send-btn">Send</button>
    </form>

    <script>
        let ws = null;
        const chatContainer = document.getElementById('chat-container');
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        const statusEl = document.getElementById('status');
        const agentSelect = document.getElementById('agent-select');

        function connect() {
            const agent = agentSelect.value;
            ws = new WebSocket(`ws://${window.location.host}/ws/${agent}`);

            ws.onopen = () => {
                statusEl.textContent = 'Connected';
                statusEl.className = 'status connected';
                sendBtn.disabled = false;
            };

            ws.onclose = () => {
                statusEl.textContent = 'Disconnected';
                statusEl.className = 'status disconnected';
                sendBtn.disabled = true;
                setTimeout(connect, 2000);
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.type === 'thinking') {
                    showThinking(data.message);
                } else if (data.type === 'response') {
                    removeThinking();
                    addMessage('agent', data.message, data.tools, data.agent);
                } else if (data.type === 'error') {
                    removeThinking();
                    addMessage('agent', `Error: ${data.message}`);
                }
            };
        }

        function addMessage(type, content, tools = [], agentName = null) {
            const div = document.createElement('div');
            div.className = `message ${type}`;

            let html = '';
            if (type === 'agent' && agentName) {
                html += `<div class="agent-name">${agentName}</div>`;
            }

            // Simple markdown-like rendering
            html += formatContent(content);

            if (tools && tools.length > 0) {
                html += `<div class="tools">Tools used: ${tools.join(', ')}</div>`;
            }

            div.innerHTML = html;
            chatContainer.appendChild(div);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function formatContent(text) {
            // Code blocks
            text = text.replace(/```(\\w*)\\n([\\s\\S]*?)```/g, '<pre><code>$2</code></pre>');
            // Inline code
            text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
            // Bold
            text = text.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');
            // Line breaks
            text = text.replace(/\\n/g, '<br>');
            return text;
        }

        function showThinking(message) {
            removeThinking();
            const div = document.createElement('div');
            div.className = 'message agent thinking';
            div.id = 'thinking';
            div.textContent = message || 'Thinking...';
            chatContainer.appendChild(div);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function removeThinking() {
            const thinking = document.getElementById('thinking');
            if (thinking) thinking.remove();
        }

        function sendMessage(e) {
            e.preventDefault();
            const message = messageInput.value.trim();
            if (!message || !ws) return;

            addMessage('user', message);
            ws.send(JSON.stringify({ message }));
            messageInput.value = '';
        }

        function sendQuick(message) {
            if (!ws) return;
            addMessage('user', message);
            ws.send(JSON.stringify({ message }));
        }

        agentSelect.addEventListener('change', () => {
            if (ws) ws.close();
            connect();
        });

        connect();
    </script>
</body>
</html>
"""


@app.get("/")
async def get_chat_ui():
    """Serve the chat UI."""
    return HTMLResponse(content=HTML_TEMPLATE)


@app.websocket("/ws/{agent_name}")
async def websocket_chat(websocket: WebSocket, agent_name: str):
    """WebSocket endpoint for real-time chat with agents."""
    await websocket.accept()

    try:
        from src.azure_agents.definitions import ALL_AGENTS
        from src.azure_agents.runner import LocalAgentRunner, ConversationalAgent

        # Find agent
        agent_def = next((a for a in ALL_AGENTS if a.name == agent_name), None)
        if not agent_def:
            await websocket.send_json({
                "type": "error",
                "message": f"Unknown agent: {agent_name}"
            })
            return

        # Create conversational agent
        runner = LocalAgentRunner()
        conv_agent = ConversationalAgent(agent_def, runner)

        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")

            if not message:
                continue

            # Send thinking indicator
            await websocket.send_json({
                "type": "thinking",
                "message": f"{agent_def.name} is thinking..."
            })

            # Process message
            try:
                response = await conv_agent.chat(message)

                await websocket.send_json({
                    "type": "response",
                    "message": response.message,
                    "tools": response.tool_calls_made or [],
                    "agent": agent_def.name,
                    "success": response.success,
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass


def create_ui_app() -> FastAPI:
    """Create the UI app (for programmatic use)."""
    return app
