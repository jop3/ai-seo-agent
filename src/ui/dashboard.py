"""
Dashboard UI with charts and trend visualization.

Provides visual reports on SEO metrics, AIO status, and trends.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from src.storage.history import get_storage, StorageBackend

app = FastAPI(title="SEO Agent Dashboard")


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - SEO Agent</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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

        /* Sub Navigation */
        .sub-nav {
            background: #1e293b;
            padding: 0.5rem 2rem;
            display: flex;
            align-items: center;
            gap: 0.25rem;
            border-bottom: 1px solid #334155;
        }
        .sub-nav a {
            color: #94a3b8;
            text-decoration: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-size: 0.85rem;
            transition: all 0.2s;
        }
        .sub-nav a:hover, .sub-nav a.active {
            background: #334155;
            color: #f1f5f9;
        }
        .sub-nav .refresh-btn {
            margin-left: auto;
            background: #3b82f6;
            color: white;
            border: none;
            padding: 0.4rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
        }
        .sub-nav .refresh-btn:hover { background: #2563eb; }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: #1e293b;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #334155;
        }
        .stat-card .label {
            font-size: 0.875rem;
            color: #94a3b8;
            margin-bottom: 0.5rem;
        }
        .stat-card .value {
            font-size: 2rem;
            font-weight: 700;
            color: #f1f5f9;
        }
        .stat-card .change {
            font-size: 0.875rem;
            margin-top: 0.5rem;
        }
        .stat-card .change.up { color: #22c55e; }
        .stat-card .change.down { color: #ef4444; }
        .stat-card .change.stable { color: #94a3b8; }

        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .chart-card {
            background: #1e293b;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #334155;
        }
        .chart-card h3 {
            font-size: 1rem;
            color: #f1f5f9;
            margin-bottom: 1rem;
        }
        .chart-card canvas {
            max-height: 300px;
        }

        .table-card {
            background: #1e293b;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #334155;
            margin-bottom: 2rem;
        }
        .table-card h3 {
            font-size: 1rem;
            color: #f1f5f9;
            margin-bottom: 1rem;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid #334155;
        }
        th {
            color: #94a3b8;
            font-weight: 500;
            font-size: 0.875rem;
        }
        td { color: #e2e8f0; }
        tr:hover { background: #334155; }

        .badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        .badge.success { background: #166534; color: #86efac; }
        .badge.warning { background: #854d0e; color: #fde047; }
        .badge.danger { background: #991b1b; color: #fca5a5; }
        .badge.info { background: #1e40af; color: #93c5fd; }

        .refresh-btn {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.875rem;
        }
        .refresh-btn:hover { background: #2563eb; }

        .header-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
        }
        .header-row h2 { font-size: 1.5rem; }

        .loading {
            display: flex;
            justify-content: center;
            padding: 2rem;
            color: #94a3b8;
        }

        @media (max-width: 768px) {
            .charts-grid { grid-template-columns: 1fr; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <!-- Global Navigation -->
    <nav class="global-nav">
        <a href="http://localhost:8080" class="logo">SEO Agent</a>
        <div class="nav-links">
            <a href="http://localhost:8080">Chat</a>
            <a href="http://localhost:8081" class="active">Dashboard</a>
            <a href="http://localhost:8082">Settings</a>
        </div>
    </nav>

    <!-- Sub Navigation - Dashboard specific -->
    <div class="sub-nav">
        <a href="#" class="active" onclick="showSection('overview')">Overview</a>
        <a href="#" onclick="showSection('aio')">AI Overviews</a>
        <a href="#" onclick="showSection('traffic')">Traffic</a>
        <a href="#" onclick="showSection('competitors')">Competitors</a>
        <a href="#" onclick="showSection('technical')">Technical</a>
        <button class="refresh-btn" onclick="refreshData()">Refresh</button>
    </div>

    <div class="container">
        <div class="header-row">
            <h2 id="section-title">Overview Dashboard</h2>
            <span id="last-updated" style="color: #94a3b8; font-size: 0.875rem;"></span>
        </div>

        <!-- Overview Section -->
        <div id="overview-section">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="label">AI Overview Coverage</div>
                    <div class="value" id="aio-coverage">--</div>
                    <div class="change stable" id="aio-trend">Loading...</div>
                </div>
                <div class="stat-card">
                    <div class="label">AIO Citation Rate</div>
                    <div class="value" id="citation-rate">--</div>
                    <div class="change stable" id="citation-trend">Loading...</div>
                </div>
                <div class="stat-card">
                    <div class="label">Organic Traffic</div>
                    <div class="value" id="organic-traffic">--</div>
                    <div class="change stable" id="traffic-trend">Loading...</div>
                </div>
                <div class="stat-card">
                    <div class="label">Technical Issues</div>
                    <div class="value" id="tech-issues">--</div>
                    <div class="change stable" id="issues-trend">Loading...</div>
                </div>
            </div>

            <div class="charts-grid">
                <div class="chart-card">
                    <h3>AIO Coverage Over Time</h3>
                    <canvas id="aio-chart"></canvas>
                </div>
                <div class="chart-card">
                    <h3>Traffic Trend</h3>
                    <canvas id="traffic-chart"></canvas>
                </div>
            </div>

            <div class="table-card">
                <h3>Top Queries - AIO Status</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Query</th>
                            <th>Has AIO</th>
                            <th>Cited</th>
                            <th>Position</th>
                            <th>Clicks</th>
                            <th>Trend</th>
                        </tr>
                    </thead>
                    <tbody id="queries-table">
                        <tr><td colspan="6" class="loading">Loading data...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- AIO Section -->
        <div id="aio-section" style="display: none;">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="label">Queries with AIO</div>
                    <div class="value" id="queries-with-aio">--</div>
                </div>
                <div class="stat-card">
                    <div class="label">You're Cited</div>
                    <div class="value" id="you-cited">--</div>
                </div>
                <div class="stat-card">
                    <div class="label">Competitors Cited</div>
                    <div class="value" id="competitors-cited">--</div>
                </div>
                <div class="stat-card">
                    <div class="label">Opportunity Score</div>
                    <div class="value" id="opportunity-score">--</div>
                </div>
            </div>

            <div class="chart-card">
                <h3>AIO Citation Distribution</h3>
                <canvas id="aio-distribution-chart"></canvas>
            </div>
        </div>

        <!-- Traffic Section -->
        <div id="traffic-section" style="display: none;">
            <div class="charts-grid">
                <div class="chart-card">
                    <h3>Daily Clicks</h3>
                    <canvas id="clicks-chart"></canvas>
                </div>
                <div class="chart-card">
                    <h3>Daily Impressions</h3>
                    <canvas id="impressions-chart"></canvas>
                </div>
            </div>

            <div class="table-card">
                <h3>Significant Traffic Changes</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Query</th>
                            <th>Previous</th>
                            <th>Current</th>
                            <th>Change</th>
                            <th>Likely Cause</th>
                        </tr>
                    </thead>
                    <tbody id="traffic-changes-table">
                        <tr><td colspan="5" class="loading">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Competitors Section -->
        <div id="competitors-section" style="display: none;">
            <div class="chart-card" style="margin-bottom: 1.5rem;">
                <h3>Competitor AIO Citation Rate</h3>
                <canvas id="competitors-chart"></canvas>
            </div>

            <div class="table-card">
                <h3>Competitor Analysis</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Competitor</th>
                            <th>AIO Citations</th>
                            <th>Avg Position</th>
                            <th>Schema Types</th>
                            <th>Threat Level</th>
                        </tr>
                    </thead>
                    <tbody id="competitors-table">
                        <tr><td colspan="5" class="loading">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Technical Section -->
        <div id="technical-section" style="display: none;">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="label">Critical Issues</div>
                    <div class="value" id="critical-issues">--</div>
                </div>
                <div class="stat-card">
                    <div class="label">Warnings</div>
                    <div class="value" id="warning-issues">--</div>
                </div>
                <div class="stat-card">
                    <div class="label">Pages Crawled</div>
                    <div class="value" id="pages-crawled">--</div>
                </div>
                <div class="stat-card">
                    <div class="label">Broken Links</div>
                    <div class="value" id="broken-links">--</div>
                </div>
            </div>

            <div class="table-card">
                <h3>Technical Issues</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Type</th>
                            <th>URL</th>
                            <th>Issue</th>
                            <th>Severity</th>
                        </tr>
                    </thead>
                    <tbody id="issues-table">
                        <tr><td colspan="4" class="loading">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        // Chart instances
        let aioChart, trafficChart, clicksChart, impressionsChart, competitorsChart, distributionChart;

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            initCharts();
            loadData();
        });

        function initCharts() {
            const chartOptions = {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { labels: { color: '#94a3b8' } }
                },
                scales: {
                    x: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
                    y: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } }
                }
            };

            // AIO Coverage Chart
            aioChart = new Chart(document.getElementById('aio-chart'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'AIO Coverage %',
                        data: [],
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        fill: true,
                        tension: 0.4
                    }, {
                        label: 'Citation Rate %',
                        data: [],
                        borderColor: '#22c55e',
                        backgroundColor: 'rgba(34, 197, 94, 0.1)',
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: chartOptions
            });

            // Traffic Chart
            trafficChart = new Chart(document.getElementById('traffic-chart'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Clicks',
                        data: [],
                        borderColor: '#8b5cf6',
                        tension: 0.4
                    }]
                },
                options: chartOptions
            });

            // Competitors Chart
            competitorsChart = new Chart(document.getElementById('competitors-chart'), {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'AIO Citation Rate %',
                        data: [],
                        backgroundColor: ['#3b82f6', '#ef4444', '#f59e0b', '#22c55e', '#8b5cf6']
                    }]
                },
                options: {
                    ...chartOptions,
                    indexAxis: 'y'
                }
            });
        }

        async function loadData() {
            document.getElementById('last-updated').textContent =
                'Last updated: ' + new Date().toLocaleTimeString();

            try {
                const response = await fetch('/api/dashboard-data');
                const data = await response.json();
                updateDashboard(data);
            } catch (error) {
                console.error('Failed to load data:', error);
                // Load demo data for development
                loadDemoData();
            }
        }

        function loadDemoData() {
            const demoData = {
                overview: {
                    aio_coverage: 42,
                    citation_rate: 15,
                    organic_traffic: 125000,
                    tech_issues: 23,
                    trends: {
                        aio: { direction: 'up', change: 5 },
                        citation: { direction: 'up', change: 3 },
                        traffic: { direction: 'down', change: -12 },
                        issues: { direction: 'down', change: -8 }
                    }
                },
                aio_trend: {
                    labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                    coverage: [35, 38, 40, 42],
                    citation: [10, 12, 13, 15]
                },
                traffic_trend: {
                    labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                    clicks: [145000, 140000, 132000, 125000]
                },
                queries: [
                    { query: 'product benefits', has_aio: true, cited: true, position: 3, clicks: 5420, trend: 'up' },
                    { query: 'how to use product', has_aio: true, cited: false, position: 5, clicks: 3210, trend: 'down' },
                    { query: 'product reviews', has_aio: true, cited: false, position: 8, clicks: 2890, trend: 'stable' },
                    { query: 'buy product online', has_aio: false, cited: false, position: 2, clicks: 4560, trend: 'up' },
                    { query: 'product alternatives', has_aio: true, cited: false, position: 12, clicks: 1980, trend: 'down' },
                ],
                competitors: [
                    { name: 'Competitor A', citation_rate: 35, position: 4.2, schemas: ['Product', 'FAQ'], threat: 'high' },
                    { name: 'Competitor B', citation_rate: 22, position: 5.8, schemas: ['Product'], threat: 'medium' },
                    { name: 'Competitor C', citation_rate: 18, position: 6.5, schemas: ['Organization'], threat: 'low' },
                ]
            };
            updateDashboard(demoData);
        }

        function updateDashboard(data) {
            // Update stats
            document.getElementById('aio-coverage').textContent = data.overview.aio_coverage + '%';
            document.getElementById('citation-rate').textContent = data.overview.citation_rate + '%';
            document.getElementById('organic-traffic').textContent = formatNumber(data.overview.organic_traffic);
            document.getElementById('tech-issues').textContent = data.overview.tech_issues;

            // Update trends
            updateTrend('aio-trend', data.overview.trends.aio);
            updateTrend('citation-trend', data.overview.trends.citation);
            updateTrend('traffic-trend', data.overview.trends.traffic);
            updateTrend('issues-trend', data.overview.trends.issues);

            // Update charts
            aioChart.data.labels = data.aio_trend.labels;
            aioChart.data.datasets[0].data = data.aio_trend.coverage;
            aioChart.data.datasets[1].data = data.aio_trend.citation;
            aioChart.update();

            trafficChart.data.labels = data.traffic_trend.labels;
            trafficChart.data.datasets[0].data = data.traffic_trend.clicks;
            trafficChart.update();

            // Update queries table
            const queriesTable = document.getElementById('queries-table');
            queriesTable.innerHTML = data.queries.map(q => `
                <tr>
                    <td>${q.query}</td>
                    <td><span class="badge ${q.has_aio ? 'success' : 'info'}">${q.has_aio ? 'Yes' : 'No'}</span></td>
                    <td><span class="badge ${q.cited ? 'success' : 'warning'}">${q.cited ? 'Yes' : 'No'}</span></td>
                    <td>${q.position}</td>
                    <td>${formatNumber(q.clicks)}</td>
                    <td><span class="change ${q.trend}">${getTrendIcon(q.trend)}</span></td>
                </tr>
            `).join('');

            // Update competitors
            competitorsChart.data.labels = data.competitors.map(c => c.name);
            competitorsChart.data.datasets[0].data = data.competitors.map(c => c.citation_rate);
            competitorsChart.update();

            const competitorsTable = document.getElementById('competitors-table');
            competitorsTable.innerHTML = data.competitors.map(c => `
                <tr>
                    <td>${c.name}</td>
                    <td>${c.citation_rate}%</td>
                    <td>${c.position}</td>
                    <td>${c.schemas.join(', ')}</td>
                    <td><span class="badge ${c.threat === 'high' ? 'danger' : c.threat === 'medium' ? 'warning' : 'info'}">${c.threat}</span></td>
                </tr>
            `).join('');
        }

        function updateTrend(elementId, trend) {
            const el = document.getElementById(elementId);
            const icon = trend.direction === 'up' ? '↑' : trend.direction === 'down' ? '↓' : '→';
            el.textContent = `${icon} ${Math.abs(trend.change)}% from last period`;
            el.className = `change ${trend.direction}`;
        }

        function getTrendIcon(trend) {
            if (trend === 'up') return '↑';
            if (trend === 'down') return '↓';
            return '→';
        }

        function formatNumber(num) {
            if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
            if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
            return num.toString();
        }

        function showSection(section) {
            // Hide all sections
            document.querySelectorAll('[id$="-section"]').forEach(el => el.style.display = 'none');

            // Show selected section
            document.getElementById(section + '-section').style.display = 'block';

            // Update nav
            document.querySelectorAll('.navbar a').forEach(a => a.classList.remove('active'));
            event.target.classList.add('active');

            // Update title
            const titles = {
                'overview': 'Overview Dashboard',
                'aio': 'AI Overviews Analysis',
                'traffic': 'Traffic Analytics',
                'competitors': 'Competitor Intelligence',
                'technical': 'Technical SEO Audit'
            };
            document.getElementById('section-title').textContent = titles[section];
        }

        function refreshData() {
            loadData();
        }
    </script>
</body>
</html>
"""


@app.get("/")
async def dashboard():
    """Serve the dashboard UI."""
    return HTMLResponse(content=DASHBOARD_HTML)


@app.get("/api/dashboard-data")
async def get_dashboard_data():
    """Get dashboard data from storage and live sources."""
    storage = get_storage()

    # Get trend data
    # In production, this would pull from actual stored metrics

    return {
        "overview": {
            "aio_coverage": 42,
            "citation_rate": 15,
            "organic_traffic": 125000,
            "tech_issues": 23,
            "trends": {
                "aio": {"direction": "up", "change": 5},
                "citation": {"direction": "up", "change": 3},
                "traffic": {"direction": "down", "change": -12},
                "issues": {"direction": "down", "change": -8},
            },
        },
        "aio_trend": {
            "labels": ["Week 1", "Week 2", "Week 3", "Week 4"],
            "coverage": [35, 38, 40, 42],
            "citation": [10, 12, 13, 15],
        },
        "traffic_trend": {
            "labels": ["Week 1", "Week 2", "Week 3", "Week 4"],
            "clicks": [145000, 140000, 132000, 125000],
        },
        "queries": [
            {"query": "product benefits", "has_aio": True, "cited": True, "position": 3, "clicks": 5420, "trend": "up"},
            {"query": "how to use", "has_aio": True, "cited": False, "position": 5, "clicks": 3210, "trend": "down"},
            {"query": "reviews", "has_aio": True, "cited": False, "position": 8, "clicks": 2890, "trend": "stable"},
        ],
        "competitors": [
            {"name": "Competitor A", "citation_rate": 35, "position": 4.2, "schemas": ["Product", "FAQ"], "threat": "high"},
            {"name": "Competitor B", "citation_rate": 22, "position": 5.8, "schemas": ["Product"], "threat": "medium"},
        ],
    }


def create_dashboard_app() -> FastAPI:
    """Create the dashboard app."""
    return app
