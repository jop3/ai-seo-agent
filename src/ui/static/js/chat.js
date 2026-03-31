// Chat functionality with WebSocket and streaming
let ws = null;
let currentAgent = 'settings-assistant';
let currentMessageDiv = null;

// Conversation persistence
function getConversationKey() {
    return `chat_history_${currentAgent}`;
}

function saveConversation() {
    const container = document.getElementById('chat-container');
    if (!container) return;

    const messages = [];
    container.querySelectorAll('.message').forEach(msg => {
        const isUser = msg.classList.contains('user');
        const agentName = msg.querySelector('.agent-name')?.textContent || '';
        const content = msg.querySelector('.message-content')?.getAttribute('data-raw')
            || msg.querySelector('.message-content')?.textContent || '';

        // Skip the welcome message
        if (!isUser && content.includes("Welcome! I'm your guide")) return;

        messages.push({
            type: isUser ? 'user' : 'agent',
            agent: agentName,
            content: content
        });
    });

    sessionStorage.setItem(getConversationKey(), JSON.stringify(messages));
}

function loadConversation() {
    const saved = sessionStorage.getItem(getConversationKey());
    if (!saved) return;

    try {
        const messages = JSON.parse(saved);
        messages.forEach(msg => {
            addMessage(msg.content, msg.type, msg.agent, true); // skipSave=true
        });
    } catch (e) {
        console.error('Failed to load conversation:', e);
    }
}

function clearConversation() {
    sessionStorage.removeItem(getConversationKey());
    const container = document.getElementById('chat-container');
    if (container) {
        // Keep only the welcome message
        const welcome = container.querySelector('.message.agent');
        container.innerHTML = '';
        if (welcome) container.appendChild(welcome);
    }
}

function connect() {
    const agentSelect = document.getElementById('agent-select');
    currentAgent = agentSelect ? agentSelect.value : 'settings-assistant';

    if (ws) ws.close();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/${currentAgent}`);

    ws.onopen = () => {
        updateStatus('Connected', true);
    };

    ws.onclose = () => {
        updateStatus('Disconnected', false);
        setTimeout(connect, 3000);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateStatus('Error', false);
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'start') {
            // Start of response - loading already shown by sendMessage, just update agent name if needed
            if (!currentMessageDiv) {
                showLoading(data.agent);
            }
        } else if (data.type === 'stream') {
            // Streaming chunk - append to current message
            appendToMessage(data.content);
        } else if (data.type === 'end') {
            // End of response - finalize message
            hideLoading();
            finalizeMessage(data.agent);
            enableSend();
        } else if (data.type === 'error') {
            // Remove loading indicator if present
            if (currentMessageDiv) {
                currentMessageDiv.remove();
                currentMessageDiv = null;
            }
            addMessage(data.message, 'agent', data.agent);
            enableSend();
        } else if (data.type === 'response') {
            // Non-streaming response (fallback) - replace loading with actual response
            if (currentMessageDiv) {
                currentMessageDiv.remove();
                currentMessageDiv = null;
            }
            addMessage(data.message, 'agent', data.agent);
            enableSend();
        }
    };
}

function updateStatus(text, connected) {
    const status = document.getElementById('status');
    if (status) {
        status.textContent = text;
        status.className = `status ${connected ? 'connected' : 'disconnected'}`;
    }
}

function showLoading(agentName) {
    const container = document.getElementById('chat-container');
    if (!container) return;

    // Create message div with loading indicator
    currentMessageDiv = document.createElement('div');
    currentMessageDiv.className = 'message agent';
    currentMessageDiv.innerHTML = `
        <div class="agent-name">${agentName || 'Agent'}</div>
        <div class="message-content">
            <span class="loading-dots">
                <span>.</span><span>.</span><span>.</span>
            </span>
        </div>
    `;

    container.appendChild(currentMessageDiv);
    container.scrollTop = container.scrollHeight;
}

function appendToMessage(content) {
    if (!currentMessageDiv) return;

    const contentDiv = currentMessageDiv.querySelector('.message-content');
    if (contentDiv) {
        // Remove loading dots if present
        const loadingDots = contentDiv.querySelector('.loading-dots');
        if (loadingDots) {
            loadingDots.remove();
        }

        // Append new content and re-render markdown
        const existingText = contentDiv.getAttribute('data-raw') || '';
        const newText = existingText + content;
        contentDiv.setAttribute('data-raw', newText);

        // Render markdown
        if (typeof marked !== 'undefined') {
            contentDiv.innerHTML = marked.parse(newText);
        } else {
            contentDiv.textContent = newText;
        }
    }

    // Scroll to bottom
    const container = document.getElementById('chat-container');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

function finalizeMessage(agentName) {
    if (!currentMessageDiv) return;

    const contentDiv = currentMessageDiv.querySelector('.message-content');
    if (contentDiv) {
        const rawText = contentDiv.getAttribute('data-raw') || contentDiv.textContent;
        if (typeof marked !== 'undefined') {
            contentDiv.innerHTML = marked.parse(rawText);
        }
    }

    currentMessageDiv = null;

    // Save conversation after response is complete
    saveConversation();
}

function hideLoading() {
    // Loading is handled in message div now
}

function addMessage(text, type, agentName, skipSave = false) {
    const container = document.getElementById('chat-container');
    if (!container) return;

    const div = document.createElement('div');
    div.className = `message ${type}`;

    if (type === 'agent' && agentName) {
        const rendered = typeof marked !== 'undefined' ? marked.parse(text || '') : text;
        div.innerHTML = `<div class="agent-name">${agentName}</div><div class="message-content" data-raw="${text.replace(/"/g, '&quot;')}">${rendered}</div>`;
    } else {
        div.innerHTML = `<div class="message-content"></div>`;
        const contentDiv = div.querySelector('.message-content');
        contentDiv.textContent = text;
        contentDiv.setAttribute('data-raw', text);
    }

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;

    // Save conversation after adding message (unless loading from storage)
    if (!skipSave) {
        saveConversation();
    }
}

function sendMessage(event) {
    if (event) event.preventDefault();

    const input = document.getElementById('message-input');
    const message = input.value.trim();

    if (message && ws && ws.readyState === WebSocket.OPEN) {
        addMessage(message, 'user');
        // Show loading immediately for responsive feedback
        showLoading(currentAgent.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()));
        ws.send(JSON.stringify({ message }));
        input.value = '';
        disableSend();
    }
}

function sendQuick(message) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        addMessage(message, 'user');
        // Show loading immediately for responsive feedback
        showLoading(currentAgent.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()));
        ws.send(JSON.stringify({ message }));
        disableSend();
    }
}

function disableSend() {
    const btn = document.getElementById('send-btn');
    if (btn) btn.disabled = true;
}

function enableSend() {
    const btn = document.getElementById('send-btn');
    if (btn) btn.disabled = false;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const agentSelect = document.getElementById('agent-select');
    if (agentSelect) {
        agentSelect.addEventListener('change', () => {
            // Clear conversation when switching agents
            clearConversation();
            connect();
        });
    }

    const form = document.getElementById('chat-form');
    if (form) {
        form.addEventListener('submit', sendMessage);
    }

    // Load previous conversation for this agent
    loadConversation();

    // Connect to WebSocket
    connect();
});
