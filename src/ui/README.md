# ui/ - Web Interface

HTMX + Jinja2 templates served by FastAPI on port 8080.

## Structure

```
ui/
├── app.py              # FastAPI routes
├── templates/
│   ├── base.html       # Shared layout (nav, head)
│   ├── chat.html       # Chat page
│   ├── dashboard.html  # Dashboard page
│   └── settings.html   # Settings page
└── static/
    ├── css/main.css    # All styles
    └── js/chat.js      # WebSocket chat logic
```

## Tech Stack

- **Jinja2**: Server-side templates
- **HTMX**: Dynamic updates without JS framework
- **marked.js**: Markdown rendering in chat
- **WebSocket**: Real-time chat with agents

## Adding a New Page

1. Create `templates/mypage.html` extending `base.html`
2. Add route in `app.py`:
   ```python
   @app.get("/mypage")
   async def mypage(request: Request):
       return templates.TemplateResponse("mypage.html", {"request": request, "active_page": "mypage"})
   ```
3. Add nav link in `templates/base.html`

## HTMX Patterns

```html
<!-- Load content into element -->
<button hx-get="/api/data" hx-target="#result">Load</button>

<!-- Submit form, show response -->
<form hx-post="/api/save" hx-target="#flash">
    <input name="field">
    <button type="submit">Save</button>
</form>

<!-- Swap content -->
<div hx-get="/api/refresh" hx-trigger="every 30s" hx-swap="innerHTML">
```

## Docker

```bash
docker compose --profile with-ui up -d
# Access at http://localhost:8080
```
