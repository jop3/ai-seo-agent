"""
Shared UI Components

Provides consistent navigation and styling across all UI pages.
"""

# Main navigation bar - same across all pages
MAIN_NAV_CSS = """
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
    display: flex;
    align-items: center;
    gap: 0.5rem;
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

/* Page-specific sub-navigation */
.sub-nav {
    background: #1e293b;
    padding: 0.5rem 2rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    border-bottom: 1px solid #334155;
}
.sub-nav h2 {
    font-size: 1rem;
    color: #f1f5f9;
    font-weight: 600;
    margin-right: 1rem;
}
.sub-nav .sub-links {
    display: flex;
    gap: 0.25rem;
}
.sub-nav .sub-links a,
.sub-nav .sub-links button {
    color: #94a3b8;
    text-decoration: none;
    padding: 0.4rem 0.75rem;
    border-radius: 4px;
    font-size: 0.85rem;
    background: transparent;
    border: none;
    cursor: pointer;
    transition: all 0.2s;
}
.sub-nav .sub-links a:hover,
.sub-nav .sub-links button:hover {
    background: #334155;
    color: #f1f5f9;
}
.sub-nav .sub-links a.active,
.sub-nav .sub-links button.active {
    background: #334155;
    color: #f1f5f9;
}
.sub-nav .sub-actions {
    margin-left: auto;
    display: flex;
    gap: 0.5rem;
    align-items: center;
}
"""


def get_main_nav_html(active_page: str = "") -> str:
    """
    Get the main navigation HTML.

    Args:
        active_page: One of "chat", "dashboard", "settings"
    """
    def active_class(page: str) -> str:
        return "active" if page == active_page else ""

    return f"""
    <nav class="global-nav">
        <a href="http://localhost:8080" class="logo">
            <span>SEO Agent</span>
        </a>
        <div class="nav-links">
            <a href="http://localhost:8080" class="{active_class('chat')}">Chat</a>
            <a href="http://localhost:8081" class="{active_class('dashboard')}">Dashboard</a>
            <a href="http://localhost:8082" class="{active_class('settings')}">Settings</a>
        </div>
    </nav>
    """


# Common page styles
BASE_STYLES = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0f172a;
    color: #e2e8f0;
    min-height: 100vh;
}

/* Common card styles */
.card {
    background: #1e293b;
    border-radius: 12px;
    padding: 1.5rem;
    border: 1px solid #334155;
    margin-bottom: 1.5rem;
}

/* Common button styles */
.btn {
    padding: 0.6rem 1.2rem;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    font-size: 0.9rem;
    transition: all 0.2s;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}
.btn-primary { background: #3b82f6; color: white; }
.btn-primary:hover { background: #2563eb; }
.btn-secondary { background: #334155; color: #e2e8f0; }
.btn-secondary:hover { background: #475569; }
.btn-success { background: #22c55e; color: white; }
.btn-success:hover { background: #16a34a; }
.btn-danger { background: #ef4444; color: white; }
.btn-danger:hover { background: #dc2626; }
.btn-sm { padding: 0.4rem 0.8rem; font-size: 0.8rem; }

/* Common form styles */
.form-group {
    margin-bottom: 1rem;
}
.form-group label {
    display: block;
    margin-bottom: 0.5rem;
    color: #94a3b8;
    font-size: 0.875rem;
}
.form-group input,
.form-group select,
.form-group textarea {
    width: 100%;
    padding: 0.75rem;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #e2e8f0;
    font-size: 0.95rem;
}
.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
    outline: none;
    border-color: #3b82f6;
}

/* Badge styles */
.badge {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 500;
}
.badge-success { background: #166534; color: #86efac; }
.badge-warning { background: #854d0e; color: #fde047; }
.badge-danger { background: #991b1b; color: #fca5a5; }
.badge-info { background: #1e40af; color: #93c5fd; }

/* Container */
.container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 1.5rem 2rem;
}

/* Toast notifications */
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
"""


def get_full_styles(extra_css: str = "") -> str:
    """Get combined base styles + navigation + extra page-specific styles."""
    return BASE_STYLES + MAIN_NAV_CSS + extra_css
