"""Web UI for local development."""

from src.ui.chat import app as chat_app, create_ui_app

__all__ = ["chat_app", "create_ui_app"]
