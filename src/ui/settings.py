"""
Settings UI for LLM Configuration

Provides a user-friendly interface for:
- Configuring LLM providers and API keys
- Managing model assignments for agents
- Creating agent groups
- Testing model connections
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.llm.config import (
    LLMSettings,
    ProviderConfig,
    ModelConfig,
    AgentModelAssignment,
    GroupModelAssignment,
    get_llm_settings,
    save_llm_settings,
)
from src.llm.provider import refresh_llm_provider
from src.agent_runner.definitions import ALL_AGENTS

app = FastAPI(title="SEO Agent Settings")


SETTINGS_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Settings - SEO Agent</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            min-height: 100vh;
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

        /* Sub Navigation / Tabs */
        .sub-nav {
            background: #1e293b;
            padding: 0.5rem 2rem;
            display: flex;
            align-items: center;
            gap: 0.25rem;
            border-bottom: 1px solid #334155;
        }
        .sub-nav .tab {
            color: #94a3b8;
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-size: 0.85rem;
            background: transparent;
            border: none;
            cursor: pointer;
            transition: all 0.2s;
        }
        .sub-nav .tab:hover {
            background: #334155;
            color: #f1f5f9;
        }
        .sub-nav .tab.active {
            background: #334155;
            color: #f1f5f9;
        }
        .sub-nav .save-btn {
            margin-left: auto;
            background: #22c55e;
            color: white;
            border: none;
            padding: 0.4rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
        }
        .sub-nav .save-btn:hover { background: #16a34a; }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }

        .tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 2rem;
            border-bottom: 1px solid #334155;
            padding-bottom: 1rem;
        }
        .tab {
            padding: 0.75rem 1.5rem;
            background: transparent;
            border: none;
            color: #94a3b8;
            cursor: pointer;
            border-radius: 6px;
            font-size: 0.95rem;
            transition: all 0.2s;
        }
        .tab:hover { background: #1e293b; color: #f1f5f9; }
        .tab.active { background: #3b82f6; color: white; }

        .card {
            background: #1e293b;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #334155;
            margin-bottom: 1.5rem;
        }
        .card h2 {
            font-size: 1.1rem;
            margin-bottom: 1rem;
            color: #f1f5f9;
        }
        .card h3 {
            font-size: 0.95rem;
            color: #94a3b8;
            margin-bottom: 0.75rem;
        }

        .form-group {
            margin-bottom: 1rem;
        }
        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            color: #94a3b8;
            font-size: 0.875rem;
        }
        .form-group input, .form-group select {
            width: 100%;
            padding: 0.75rem;
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 6px;
            color: #e2e8f0;
            font-size: 0.95rem;
        }
        .form-group input:focus, .form-group select:focus {
            outline: none;
            border-color: #3b82f6;
        }
        .form-group input[type="password"] {
            font-family: monospace;
        }
        .form-group .help {
            font-size: 0.75rem;
            color: #64748b;
            margin-top: 0.25rem;
        }

        .form-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
        }

        .btn {
            padding: 0.75rem 1.5rem;
            border-radius: 6px;
            border: none;
            cursor: pointer;
            font-size: 0.95rem;
            transition: all 0.2s;
        }
        .btn-primary { background: #3b82f6; color: white; }
        .btn-primary:hover { background: #2563eb; }
        .btn-secondary { background: #334155; color: #e2e8f0; }
        .btn-secondary:hover { background: #475569; }
        .btn-success { background: #22c55e; color: white; }
        .btn-danger { background: #ef4444; color: white; }
        .btn-sm { padding: 0.5rem 1rem; font-size: 0.875rem; }

        .provider-card {
            display: flex;
            align-items: center;
            padding: 1rem;
            background: #0f172a;
            border-radius: 8px;
            margin-bottom: 0.75rem;
            border: 1px solid #334155;
        }
        .provider-card.enabled { border-color: #22c55e; }
        .provider-card .provider-info { flex: 1; }
        .provider-card .provider-name { font-weight: 600; color: #f1f5f9; }
        .provider-card .provider-desc { font-size: 0.75rem; color: #64748b; }
        .provider-card .provider-status {
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.75rem;
            margin-left: 1rem;
        }
        .provider-card .provider-status.connected { background: #166534; color: #86efac; }
        .provider-card .provider-status.disconnected { background: #7f1d1d; color: #fca5a5; }

        .agent-row {
            display: flex;
            align-items: center;
            padding: 0.75rem;
            background: #0f172a;
            border-radius: 6px;
            margin-bottom: 0.5rem;
        }
        .agent-row .agent-name {
            flex: 1;
            font-weight: 500;
        }
        .agent-row select {
            width: 200px;
            padding: 0.5rem;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 4px;
            color: #e2e8f0;
        }

        .model-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1rem;
        }
        .model-card {
            background: #0f172a;
            border-radius: 8px;
            padding: 1rem;
            border: 1px solid #334155;
        }
        .model-card.selected { border-color: #3b82f6; background: #1e3a5f; }
        .model-card .model-name { font-weight: 600; color: #f1f5f9; margin-bottom: 0.25rem; }
        .model-card .model-provider { font-size: 0.75rem; color: #64748b; }
        .model-card .model-meta {
            display: flex;
            gap: 0.5rem;
            margin-top: 0.5rem;
            flex-wrap: wrap;
        }
        .model-card .badge {
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            background: #334155;
            color: #94a3b8;
        }
        .model-card .badge.quality { background: #7c3aed; color: white; }
        .model-card .badge.fast { background: #22c55e; color: white; }
        .model-card .badge.reasoning { background: #f59e0b; color: white; }
        .model-card .badge.local { background: #06b6d4; color: white; }

        .toast {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            padding: 1rem 1.5rem;
            background: #22c55e;
            color: white;
            border-radius: 8px;
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.3s;
            z-index: 1000;
        }
        .toast.show { opacity: 1; transform: translateY(0); }
        .toast.error { background: #ef4444; }

        .section { display: none; }
        .section.active { display: block; }

        .header-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }

        .test-result {
            padding: 1rem;
            border-radius: 6px;
            margin-top: 1rem;
            font-family: monospace;
            font-size: 0.875rem;
            white-space: pre-wrap;
        }
        .test-result.success { background: #166534; }
        .test-result.error { background: #7f1d1d; }
    </style>
</head>
<body>
    <!-- Global Navigation -->
    <nav class="global-nav">
        <a href="http://localhost:8080" class="logo">SEO Agent</a>
        <div class="nav-links">
            <a href="http://localhost:8080">Chat</a>
            <a href="http://localhost:8081">Dashboard</a>
            <a href="http://localhost:8082" class="active">Settings</a>
        </div>
    </nav>

    <!-- Sub Navigation - Settings tabs -->
    <div class="sub-nav">
        <button class="tab active" onclick="showSection('general')">General</button>
        <button class="tab" onclick="showSection('providers')">Providers</button>
        <button class="tab" onclick="showSection('models')">Models</button>
        <button class="tab" onclick="showSection('agents')">Agent Assignments</button>
        <button class="tab" onclick="showSection('groups')">Groups</button>
        <button class="tab" onclick="showSection('test')">Test Connection</button>
        <button class="save-btn" onclick="saveSettings()">Save Changes</button>
    </div>

    <div class="container">

        <!-- General Section -->
        <div id="general-section" class="section active">
            <div class="card">
                <h2 style="margin-bottom: 1rem; color: #f1f5f9;">Site Configuration</h2>
                <p style="color: #94a3b8; margin-bottom: 1.5rem;">
                    Configure your website settings. These are used by all agents for analysis.
                </p>

                <div class="form-row">
                    <div class="form-group">
                        <label>Site URL</label>
                        <input type="url" id="site-url" placeholder="https://www.example.com">
                        <p class="help">Your main website URL. Used for crawling and analysis.</p>
                    </div>
                    <div class="form-group">
                        <label>Site Name</label>
                        <input type="text" id="site-name" placeholder="My Company">
                        <p class="help">Your company or site name for reports.</p>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 1rem; color: #f1f5f9;">Google Search Console</h2>
                <p style="color: #94a3b8; margin-bottom: 1.5rem;">
                    Connect to Google Search Console to analyze your search performance data.
                </p>

                <div class="form-row">
                    <div class="form-group">
                        <label>GSC Property</label>
                        <input type="text" id="gsc-property" placeholder="sc-domain:example.com">
                        <p class="help">Your Search Console property (e.g., sc-domain:example.com)</p>
                    </div>
                    <div class="form-group">
                        <label>Service Account JSON</label>
                        <input type="file" id="gsc-credentials" accept=".json">
                        <p class="help">Upload your Google Cloud service account credentials</p>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 1rem; color: #f1f5f9;">Content Settings</h2>
                <p style="color: #94a3b8; margin-bottom: 1.5rem;">
                    Configure content generation preferences for the Content Writer agent.
                </p>

                <div class="form-row">
                    <div class="form-group">
                        <label>Blog URL Pattern</label>
                        <input type="text" id="blog-url-pattern" placeholder="/blog/*">
                        <p class="help">URL pattern for blog posts (used for style analysis)</p>
                    </div>
                    <div class="form-group">
                        <label>Default Language</label>
                        <select id="content-language">
                            <option value="sv">Swedish</option>
                            <option value="en">English</option>
                            <option value="no">Norwegian</option>
                            <option value="da">Danish</option>
                            <option value="fi">Finnish</option>
                        </select>
                        <p class="help">Primary language for generated content</p>
                    </div>
                </div>

                <div class="form-group">
                    <label>Reference Articles (for style analysis)</label>
                    <textarea id="reference-articles" rows="4" placeholder="https://example.com/blog/article-1&#10;https://example.com/blog/article-2"></textarea>
                    <p class="help">URLs of existing articles that represent your brand voice (one per line)</p>
                </div>
            </div>

            <div class="card">
                <h2 style="margin-bottom: 1rem; color: #f1f5f9;">Competitors</h2>
                <p style="color: #94a3b8; margin-bottom: 1.5rem;">
                    Add competitor domains to track in competitive analysis.
                </p>

                <div class="form-group">
                    <label>Competitor Domains</label>
                    <textarea id="competitor-domains" rows="4" placeholder="competitor1.com&#10;competitor2.com"></textarea>
                    <p class="help">Competitor domains to monitor (one per line)</p>
                </div>
            </div>
        </div>

        <!-- Providers Section -->
        <div id="providers-section" class="section">
            <div class="header-row">
                <h2>LLM Providers</h2>
                <button class="btn btn-primary" onclick="saveSettings()">Save Changes</button>
            </div>

            <div id="providers-list"></div>

            <div class="card" style="margin-top: 1rem;">
                <h3>Provider Configuration</h3>
                <div id="provider-config"></div>
            </div>
        </div>

        <!-- Models Section -->
        <div id="models-section" class="section">
            <div class="header-row">
                <h2>Available Models</h2>
                <div>
                    <select id="model-filter" onchange="filterModels()">
                        <option value="all">All Categories</option>
                        <option value="fast">Fast</option>
                        <option value="balanced">Balanced</option>
                        <option value="quality">Quality</option>
                        <option value="reasoning">Reasoning</option>
                        <option value="local">Local</option>
                    </select>
                </div>
            </div>

            <div class="card">
                <h3>Default Model</h3>
                <div class="form-group">
                    <select id="default-model" onchange="updateDefaultModel()">
                    </select>
                    <p class="help">Used when no specific agent assignment exists</p>
                </div>
            </div>

            <div class="model-grid" id="models-grid"></div>
        </div>

        <!-- Agent Assignments Section -->
        <div id="agents-section" class="section">
            <div class="header-row">
                <h2>Agent Model Assignments</h2>
                <button class="btn btn-primary" onclick="saveSettings()">Save Changes</button>
            </div>

            <p style="color: #94a3b8; margin-bottom: 1rem;">
                Assign specific models to each agent. Leave as "Use Default" to use the default model or group assignment.
            </p>

            <div class="card">
                <div id="agent-assignments"></div>
            </div>
        </div>

        <!-- Groups Section -->
        <div id="groups-section" class="section">
            <div class="header-row">
                <h2>Agent Groups</h2>
                <button class="btn btn-primary" onclick="saveSettings()">Save Changes</button>
            </div>

            <p style="color: #94a3b8; margin-bottom: 1rem;">
                Group agents together to assign the same model to multiple agents at once.
            </p>

            <div id="groups-list"></div>

            <button class="btn btn-secondary" onclick="addGroup()" style="margin-top: 1rem;">
                + Add Group
            </button>
        </div>

        <!-- Test Section -->
        <div id="test-section" class="section">
            <div class="header-row">
                <h2>Test Connection</h2>
            </div>

            <div class="card">
                <div class="form-row">
                    <div class="form-group">
                        <label>Select Model</label>
                        <select id="test-model"></select>
                    </div>
                    <div class="form-group">
                        <label>Test Prompt</label>
                        <input type="text" id="test-prompt" value="Say hello in exactly 5 words">
                    </div>
                </div>
                <button class="btn btn-primary" onclick="testConnection()">Test Connection</button>
                <div id="test-result"></div>
            </div>
        </div>
    </div>

    <div id="toast" class="toast"></div>

    <script>
        let settings = null;
        let agents = [];

        // Load initial data
        async function loadData() {
            try {
                const [settingsRes, agentsRes] = await Promise.all([
                    fetch('/api/settings'),
                    fetch('/api/agents')
                ]);
                settings = await settingsRes.json();
                agents = await agentsRes.json();
                renderAll();
            } catch (e) {
                showToast('Failed to load settings', true);
            }
        }

        function renderAll() {
            renderProviders();
            renderModels();
            renderAgentAssignments();
            renderGroups();
            renderTestSection();
        }

        function renderProviders() {
            const list = document.getElementById('providers-list');
            list.innerHTML = Object.entries(settings.providers).map(([key, p]) => `
                <div class="provider-card ${p.enabled ? 'enabled' : ''}" onclick="selectProvider('${key}')">
                    <div class="provider-info">
                        <div class="provider-name">${p.display_name || p.name}</div>
                        <div class="provider-desc">${p.description || ''}</div>
                    </div>
                    <span class="provider-status ${p.enabled && p.api_key ? 'connected' : 'disconnected'}">
                        ${p.enabled ? (p.api_key ? 'Configured' : 'No API Key') : 'Disabled'}
                    </span>
                </div>
            `).join('');

            // Show first provider config
            const firstProvider = Object.keys(settings.providers)[0];
            if (firstProvider) selectProvider(firstProvider);
        }

        function selectProvider(key) {
            const p = settings.providers[key];
            const config = document.getElementById('provider-config');

            config.innerHTML = `
                <div class="form-group">
                    <label>
                        <input type="checkbox" ${p.enabled ? 'checked' : ''}
                               onchange="settings.providers['${key}'].enabled = this.checked; renderProviders()">
                        Enable ${p.display_name || p.name}
                    </label>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>API Key</label>
                        <input type="password" value="${p.api_key || ''}"
                               onchange="settings.providers['${key}'].api_key = this.value"
                               placeholder="sk-...">
                    </div>
                    ${key === 'local' || key === 'azure' ? `
                    <div class="form-group">
                        <label>API Base URL</label>
                        <input type="text" value="${p.api_base || ''}"
                               onchange="settings.providers['${key}'].api_base = this.value"
                               placeholder="https://...">
                    </div>
                    ` : ''}
                </div>
                ${key === 'azure' ? `
                <div class="form-row">
                    <div class="form-group">
                        <label>Deployment Name</label>
                        <input type="text" value="${p.azure_deployment || ''}"
                               onchange="settings.providers['${key}'].azure_deployment = this.value">
                    </div>
                    <div class="form-group">
                        <label>API Version</label>
                        <input type="text" value="${p.azure_api_version || '2024-02-15-preview'}"
                               onchange="settings.providers['${key}'].azure_api_version = this.value">
                    </div>
                </div>
                ` : ''}
            `;
        }

        function renderModels() {
            const grid = document.getElementById('models-grid');
            const defaultSelect = document.getElementById('default-model');
            const testSelect = document.getElementById('test-model');

            const categoryBadge = (cat) => {
                const classes = { fast: 'fast', quality: 'quality', reasoning: 'reasoning', local: 'local' };
                return `<span class="badge ${classes[cat] || ''}">${cat}</span>`;
            };

            grid.innerHTML = Object.entries(settings.models).map(([key, m]) => `
                <div class="model-card ${key === settings.default_model_id ? 'selected' : ''}"
                     onclick="setDefaultModel('${key}')">
                    <div class="model-name">${m.display_name}</div>
                    <div class="model-provider">${m.provider}</div>
                    <div class="model-meta">
                        ${categoryBadge(m.category)}
                        ${m.capabilities.map(c => `<span class="badge">${c}</span>`).join('')}
                    </div>
                    ${m.input_cost > 0 ? `<div style="font-size: 0.7rem; color: #64748b; margin-top: 0.5rem;">
                        $${m.input_cost}/1M in · $${m.output_cost}/1M out
                    </div>` : ''}
                </div>
            `).join('');

            // Populate selects
            const options = Object.entries(settings.models)
                .map(([k, m]) => `<option value="${k}" ${k === settings.default_model_id ? 'selected' : ''}>${m.display_name}</option>`)
                .join('');

            defaultSelect.innerHTML = options;
            testSelect.innerHTML = options;
        }

        function setDefaultModel(modelId) {
            settings.default_model_id = modelId;
            renderModels();
        }

        function updateDefaultModel() {
            settings.default_model_id = document.getElementById('default-model').value;
            renderModels();
        }

        function filterModels() {
            const filter = document.getElementById('model-filter').value;
            const cards = document.querySelectorAll('.model-card');
            cards.forEach(card => {
                if (filter === 'all') {
                    card.style.display = 'block';
                } else {
                    const model = Object.values(settings.models).find(m =>
                        card.querySelector('.model-name').textContent === m.display_name
                    );
                    card.style.display = model && model.category === filter ? 'block' : 'none';
                }
            });
        }

        function renderAgentAssignments() {
            const container = document.getElementById('agent-assignments');
            const modelOptions = `
                <option value="">Use Default / Group</option>
                ${Object.entries(settings.models)
                    .map(([k, m]) => `<option value="${k}">${m.display_name}</option>`)
                    .join('')}
            `;

            container.innerHTML = agents.map(agent => {
                const assignment = settings.agent_assignments[agent.name] || {};
                return `
                    <div class="agent-row">
                        <span class="agent-name">${agent.name}</span>
                        <select onchange="updateAgentAssignment('${agent.name}', this.value)">
                            ${modelOptions.replace(`value="${assignment.model_id}"`, `value="${assignment.model_id}" selected`)}
                        </select>
                    </div>
                `;
            }).join('');
        }

        function updateAgentAssignment(agentName, modelId) {
            if (modelId) {
                settings.agent_assignments[agentName] = {
                    agent_name: agentName,
                    model_id: modelId
                };
            } else {
                delete settings.agent_assignments[agentName];
            }
        }

        function renderGroups() {
            const container = document.getElementById('groups-list');
            const modelOptions = Object.entries(settings.models)
                .map(([k, m]) => `<option value="${k}">${m.display_name}</option>`)
                .join('');

            container.innerHTML = settings.groups.map((group, idx) => `
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <input type="text" value="${group.group_name}"
                               onchange="settings.groups[${idx}].group_name = this.value"
                               style="background: transparent; border: none; color: #f1f5f9; font-size: 1rem; font-weight: 600;">
                        <button class="btn btn-danger btn-sm" onclick="removeGroup(${idx})">Remove</button>
                    </div>
                    <div class="form-group">
                        <label>Model for this group</label>
                        <select onchange="settings.groups[${idx}].model_id = this.value">
                            ${modelOptions.replace(`value="${group.model_id}"`, `value="${group.model_id}" selected`)}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Agents in this group</label>
                        <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem;">
                            ${agents.map(a => `
                                <label style="display: flex; align-items: center; gap: 0.25rem; padding: 0.25rem 0.5rem; background: #0f172a; border-radius: 4px; cursor: pointer;">
                                    <input type="checkbox" ${group.agent_names.includes(a.name) ? 'checked' : ''}
                                           onchange="toggleAgentInGroup(${idx}, '${a.name}', this.checked)">
                                    ${a.name}
                                </label>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `).join('');
        }

        function addGroup() {
            settings.groups.push({
                group_name: 'New Group',
                agent_names: [],
                model_id: settings.default_model_id
            });
            renderGroups();
        }

        function removeGroup(idx) {
            settings.groups.splice(idx, 1);
            renderGroups();
        }

        function toggleAgentInGroup(groupIdx, agentName, checked) {
            const group = settings.groups[groupIdx];
            if (checked && !group.agent_names.includes(agentName)) {
                group.agent_names.push(agentName);
            } else if (!checked) {
                group.agent_names = group.agent_names.filter(n => n !== agentName);
            }
        }

        function renderTestSection() {
            // Already handled in renderModels
        }

        async function testConnection() {
            const modelId = document.getElementById('test-model').value;
            const prompt = document.getElementById('test-prompt').value;
            const resultDiv = document.getElementById('test-result');

            resultDiv.innerHTML = '<div class="test-result">Testing...</div>';

            try {
                const res = await fetch('/api/test-model', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model_id: modelId, prompt })
                });
                const data = await res.json();

                if (data.success) {
                    resultDiv.innerHTML = `
                        <div class="test-result success">
✓ Connection successful!

Model: ${data.model}
Response: ${data.content}
Tokens: ${data.usage?.total_tokens || 'N/A'}
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `
                        <div class="test-result error">
✗ Connection failed

Error: ${data.error}
                        </div>
                    `;
                }
            } catch (e) {
                resultDiv.innerHTML = `<div class="test-result error">✗ Request failed: ${e.message}</div>`;
            }
        }

        async function saveSettings() {
            try {
                const res = await fetch('/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settings)
                });
                if (res.ok) {
                    showToast('Settings saved successfully!');
                } else {
                    showToast('Failed to save settings', true);
                }
            } catch (e) {
                showToast('Failed to save settings', true);
            }
        }

        function showSection(section) {
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));

            document.getElementById(section + '-section').classList.add('active');
            event.target.classList.add('active');
        }

        function showToast(message, isError = false) {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast show' + (isError ? ' error' : '');
            setTimeout(() => toast.className = 'toast', 3000);
        }

        // Initialize
        loadData();
    </script>
</body>
</html>
"""


@app.get("/")
async def settings_page():
    """Serve the settings UI."""
    return HTMLResponse(content=SETTINGS_HTML)


@app.get("/api/settings")
async def get_settings():
    """Get current LLM settings."""
    settings = get_llm_settings()
    return settings.model_dump()


class SettingsUpdate(BaseModel):
    """Settings update payload."""
    providers: dict
    models: dict
    default_model_id: str
    groups: list
    agent_assignments: dict
    enable_fallbacks: bool = True
    enable_caching: bool = True
    log_requests: bool = True


@app.post("/api/settings")
async def update_settings(update: SettingsUpdate):
    """Update LLM settings."""
    try:
        settings = LLMSettings.model_validate(update.model_dump())
        if save_llm_settings(settings):
            refresh_llm_provider()
            return {"success": True}
        else:
            raise HTTPException(status_code=500, detail="Failed to save settings")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/agents")
async def get_agents():
    """Get list of available agents."""
    return [
        {"name": agent.name, "description": agent.description}
        for agent in ALL_AGENTS
    ]


class TestModelRequest(BaseModel):
    """Test model request."""
    model_id: str
    prompt: str


@app.post("/api/test-model")
async def test_model(request: TestModelRequest):
    """Test a model connection."""
    from src.llm.provider import get_llm_provider

    try:
        provider = get_llm_provider()
        result = await provider.chat(
            messages=[{"role": "user", "content": request.prompt}],
            model_override=request.model_id,
            max_tokens=100,
        )
        return {
            "success": True,
            "model": result.get("model"),
            "content": result.get("content"),
            "usage": result.get("usage"),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def create_settings_app() -> FastAPI:
    """Create the settings app."""
    return app
