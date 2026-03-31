# AI SEO Agent - User Interface Guide

Your AI SEO Agent has **3 different interfaces** to choose from!

## 🎨 Available Interfaces

### 1. **Swagger API Docs** (Already Running) ✅
**Best for:** Testing API endpoints, exploring functionality

```
URL: http://localhost:8000/docs
```

**Features:**
- Interactive API documentation
- Test all endpoints directly in browser
- See request/response schemas
- Try out API calls without coding

**Already running!** Just open the URL in your browser.

---

### 2. **Web Chat UI** 💬
**Best for:** Interactive chat with AI agents

```bash
# Start the chat UI
docker-compose --profile with-ui up -d

# Access at:
http://localhost:8080
```

**Features:**
- Chat interface with AI agents
- Interactive conversations
- Real-time responses
- User-friendly web interface

---

### 3. **Dashboard UI** 📊
**Best for:** Viewing analytics, charts, and trends

```bash
# Start the dashboard
docker-compose --profile with-dashboard up -d

# Access at:
http://localhost:8081
```

**Features:**
- Visual charts and graphs
- SEO performance trends
- Analytics dashboard
- Monitoring overview

---

### 4. **Run ALL UIs at Once** 🚀

```bash
# Start everything!
docker-compose --profile with-ui --profile with-dashboard up -d
```

**Access points:**
- API Docs: http://localhost:8000/docs
- Chat UI: http://localhost:8080
- Dashboard: http://localhost:8081

---

## 📋 Quick Start Commands

### Start Just the Chat UI
```bash
docker-compose --profile with-ui up -d
```

### Start Just the Dashboard
```bash
docker-compose --profile with-dashboard up -d
```

### Start Both UIs
```bash
docker-compose --profile with-ui --profile with-dashboard up -d
```

### View Logs
```bash
# Chat UI logs
docker-compose logs -f ui

# Dashboard logs
docker-compose logs -f dashboard
```

### Stop UIs
```bash
# Stop everything
docker-compose down

# Or stop specific services
docker-compose stop ui
docker-compose stop dashboard
```

---

## 🎯 What Should I Use?

| Use Case | Recommended Interface | Port |
|----------|----------------------|------|
| **Testing API endpoints** | Swagger API Docs | 8000 |
| **Interactive chat** | Web Chat UI | 8080 |
| **View analytics** | Dashboard UI | 8081 |
| **Development/debugging** | API Docs + Logs | 8000 |
| **Demo to stakeholders** | Chat UI or Dashboard | 8080/8081 |
| **Production monitoring** | Dashboard UI | 8081 |

---

## 🔧 Configuration

All UIs use the same `.env` configuration:

```bash
# Edit your configuration
nano .env  # or use your editor
```

Key settings:
- `AZURE_OPENAI_*` - For AI model access
- `GSC_*` - For Google Search Console data
- `REDIS_URL` - Already configured for docker-compose

---

## 🚀 Full Setup Example

```bash
# 1. Make sure base services are running
docker-compose ps

# 2. Start the UIs you want
docker-compose --profile with-ui --profile with-dashboard up -d

# 3. Check status
docker-compose ps

# 4. Access in browser:
# - API: http://localhost:8000/docs
# - Chat: http://localhost:8080
# - Dashboard: http://localhost:8081
```

---

## 🐛 Troubleshooting

### UI Won't Start

```bash
# Check logs
docker-compose logs ui
docker-compose logs dashboard

# Rebuild if needed
docker-compose build
docker-compose --profile with-ui up -d
```

### Port Already in Use

Change ports in `docker-compose.yml`:

```yaml
ui:
  ports:
    - "8082:8080"  # Use 8082 instead
```

### UI Shows Errors

1. Check if API is running: `curl http://localhost:8000/health`
2. Check if Redis is running: `docker-compose ps redis`
3. View logs: `docker-compose logs api redis`

---

## 📊 Service Overview

| Service | Port | Status | Profile |
|---------|------|--------|---------|
| **API** | 8000 | ✅ Running | default |
| **Worker** | - | ✅ Running | default |
| **Redis** | 6379 | ✅ Running | default |
| **Chat UI** | 8080 | Optional | `with-ui` |
| **Dashboard** | 8081 | Optional | `with-dashboard` |
| **Scheduler** | - | Optional | `with-scheduler` |

---

## 💡 Tips

### 1. Development Mode
For development, run everything:
```bash
docker-compose --profile with-ui --profile with-dashboard up -d
docker-compose logs -f
```

### 2. Production Mode
For production, you might only need the API:
```bash
docker-compose up -d api worker redis
```

### 3. Quick Testing
Use Swagger UI (no extra services needed):
```
http://localhost:8000/docs
```

### 4. Resource Management
UIs use minimal resources, but if needed:
```bash
# Run only what you need
docker-compose up -d api redis  # Just API
docker-compose --profile with-dashboard up -d  # Add dashboard later
```

---

## 🎉 Next Steps

1. **Start with Swagger UI** - Already running at http://localhost:8000/docs
2. **Try Chat UI** - Run: `docker-compose --profile with-ui up -d`
3. **Explore Dashboard** - Run: `docker-compose --profile with-dashboard up -d`
4. **Configure your settings** - Edit `.env` with your API keys

---

## 📚 More Information

- **Quick Start**: See `DOCKER_QUICKSTART.md`
- **Full Documentation**: See `README.md`
- **CLI Commands**: Run `docker-compose exec api python -m src.cli --help`

---

**Enjoy your AI SEO Agent!** 🚀
