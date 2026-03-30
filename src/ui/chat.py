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
    <title>Chat - SEO Agent</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* Global Navigation */
        .global-nav {
            background: #0f172a;
            padding: 0.75rem 2rem;
            display: flex;
            align-items: center;
            gap: 2rem;
            border-bottom: 1px solid #1e293b;
        }
        .global-nav .logo {
            font-size: 1.25rem;
            font-weight: 700;
            color: #f1f5f9;
            text-decoration: none;
        }
        .global-nav .nav-links {
            display: flex;
            gap: 0.25rem;
            margin-left: auto;
        }
        .global-nav .nav-links a {
            color: #94a3b8;
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-size: 0.9rem;
            transition: all 0.2s;
        }
        .global-nav .nav-links a:hover {
            background: #1e293b;
            color: #f1f5f9;
        }
        .global-nav .nav-links a.active {
            background: #3b82f6;
            color: white;
        }

        /* Sub Navigation */
        .sub-nav {
            background: #1e293b;
            padding: 0.5rem 2rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            border-bottom: 1px solid #334155;
        }
        .sub-nav .agent-select {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .sub-nav label {
            color: #94a3b8;
            font-size: 0.85rem;
        }
        .sub-nav select {
            background: #334155;
            color: #e2e8f0;
            border: 1px solid #475569;
            padding: 0.4rem 0.75rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
        }
        .sub-nav .quick-actions {
            display: flex;
            gap: 0.5rem;
            margin-left: 1rem;
        }
        .sub-nav .quick-actions button {
            background: #334155;
            color: #e2e8f0;
            border: none;
            padding: 0.4rem 0.75rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.8rem;
            transition: all 0.2s;
        }
        .sub-nav .quick-actions button:hover {
            background: #475569;
        }
        .sub-nav .status {
            margin-left: auto;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.75rem;
        }
        .sub-nav .status.connected { background: #166534; color: #86efac; }
        .sub-nav .status.disconnected { background: #991b1b; color: #fca5a5; }

        /* Chat area */
        #chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 1.5rem 2rem;
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
            background: #1e40af;
        }
        .message.agent {
            align-self: flex-start;
            background: #1e293b;
            border: 1px solid #334155;
        }
        .message .agent-name {
            font-size: 0.75rem;
            color: #3b82f6;
            margin-bottom: 0.5rem;
        }
        .message .tools {
            font-size: 0.75rem;
            color: #64748b;
            margin-top: 0.5rem;
            border-top: 1px solid #334155;
            padding-top: 0.5rem;
        }
        .message pre {
            background: #0f172a;
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
            color: #64748b;
            font-style: italic;
        }

        /* Input area */
        #input-container {
            background: #1e293b;
            padding: 1rem 2rem;
            border-top: 1px solid #334155;
            display: flex;
            gap: 1rem;
        }
        #message-input {
            flex: 1;
            background: #0f172a;
            border: 1px solid #334155;
            color: #e2e8f0;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-size: 1rem;
        }
        #message-input:focus {
            outline: none;
            border-color: #3b82f6;
        }
        #input-container button {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            transition: background 0.2s;
        }
        #input-container button:hover { background: #2563eb; }
        #input-container button:disabled { background: #475569; cursor: not-allowed; }
    </style>
</head>
<body>
    <!-- Global Navigation -->
    <nav class="global-nav">
        <a href="http://localhost:8080" class="logo">SEO Agent</a>
        <div class="nav-links">
            <a href="http://localhost:8080" class="active">Chat</a>
            <a href="http://localhost:8081">Dashboard</a>
            <a href="http://localhost:8082">Settings</a>
        </div>
    </nav>

    <!-- Sub Navigation - Chat specific -->
    <div class="sub-nav">
        <div class="agent-select">
            <label for="agent-select">Agent:</label>
            <select id="agent-select">
                <option value="seo-analyst">SEO Analyst</option>
                <option value="trend-analyzer">Trend Analyzer</option>
                <option value="content-writer">Content Writer</option>
                <option value="agent-tester">Agent Tester</option>
                <option value="monitoring-agent">Monitoring Agent</option>
                <option value="optimizer">Optimizer</option>
                <option value="competitor-monitor">Competitor Monitor</option>
                <option value="content-generator">Content Generator</option>
            </select>
        </div>
        <div class="quick-actions">
            <button onclick="sendQuick('Run full SEO analysis')">Full Analysis</button>
            <button onclick="sendQuick('Check AIO status for top queries')">Check AIO</button>
            <button onclick="sendQuick('Generate FAQ schema')">Generate FAQ</button>
            <button onclick="sendQuick('Show traffic anomalies')">Traffic</button>
        </div>
        <span id="status" class="status disconnected">Disconnected</span>
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
        from src.agent_runner.definitions import ALL_AGENTS
        from src.agent_runner.runner import LocalAgentRunner, ConversationalAgent

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
