# Docker Model Runner Setup - FREE Local AI!

Docker Model Runner is Docker Desktop's built-in AI model runtime. It's the easiest way to run local LLMs!

## Prerequisites

- **Docker Desktop 4.41+** (includes Model Runner)
- Your system: ✅ Perfect specs!
  - 64GB RAM
  - NVIDIA RTX 5070 Ti (12GB VRAM)
  - 16 cores

## Quick Setup (5 minutes)

### Step 1: Enable Docker Model Runner

1. Open **Docker Desktop**
2. Go to **Settings** → **Extensions**
3. Enable **"Docker AI Model Runner"** (if not already enabled)
4. Or install from: https://hub.docker.com/extensions/docker/model-runner-extension

### Step 2: Pull a Model via Docker Desktop UI

1. Open Docker Desktop
2. Go to the **Model Runner** tab (left sidebar)
3. Browse available models
4. Pull **"Microsoft Phi-3 Mini"** (recommended for your system)
   - Size: ~2.3GB
   - Quality: Excellent
   - Speed: Very Fast with GPU

Alternative models:
- **Llama 3.2 3B** - Similar performance
- **Gemma 2 2B** - Google's model
- **SmolLM2 360M** - Fastest, good for testing

### Step 3: Configure Your Application

Update your `.env` file:

```bash
# Docker Model Runner (OpenAI-compatible API)
OPENAI_API_BASE=http://host.docker.internal:8080/v1
OPENAI_API_KEY=not-needed
OPENAI_MODEL=phi3
```

### Step 4: Start Services

```bash
# Make sure Model Runner is running in Docker Desktop
# Then start your services:
docker-compose up -d
```

## Using Model Runner via CLI

### List Available Models

```bash
docker model ls
```

### Pull a Model

```bash
docker model pull phi3
# or
docker model pull llama3.2:3b
```

### Run a Model

```bash
docker model run phi3
# Starts API on http://localhost:8080
```

### Test the Model

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "phi3",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Integration with AI SEO Agent

Once Model Runner is running, your AI SEO Agent will automatically use it!

### Configuration

In `.env`:
```bash
# Point to Model Runner API
OPENAI_API_BASE=http://host.docker.internal:8080/v1
OPENAI_API_KEY=not-needed
OPENAI_MODEL=phi3
```

### Start Everything

```bash
# 1. Start Model Runner in Docker Desktop (with your model)
# 2. Start AI SEO Agent
docker-compose up -d

# 3. Test
curl http://localhost:8000/health
```

## GPU Acceleration

Docker Model Runner **automatically detects and uses your NVIDIA GPU**!

You should see:
- **5-10x faster inference**
- GPU usage in Task Manager
- Lower latency responses

Check GPU usage:
```bash
nvidia-smi
```

## Recommended Models for Your System

With 64GB RAM + RTX 5070 Ti:

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| **Phi-3 Mini** ⭐ | 2.3GB | ⚡⚡⚡ | ⭐⭐⭐⭐ | **Recommended** |
| **Llama 3.2 3B** | 2.0GB | ⚡⚡⚡ | ⭐⭐⭐⭐ | Alternative |
| **Gemma 2 2B** | 1.5GB | ⚡⚡⚡ | ⭐⭐⭐ | Google model |

All will use your GPU automatically!

## Troubleshooting

### Model Runner Not Available?

Update Docker Desktop:
```bash
# Check version
docker --version

# Need 4.41 or higher
```

### Can't Connect to Model?

1. Check Model Runner is running in Docker Desktop
2. Verify model is loaded
3. Test endpoint:
```bash
curl http://localhost:8080/v1/models
```

### Performance Issues?

- Check GPU is being used: `nvidia-smi`
- Ensure Model Runner has GPU access in Docker Desktop settings
- Try a smaller model if needed

## Alternative: Using Existing Setup

If you prefer to continue without Model Runner for now:

1. Keep using cloud APIs (Azure OpenAI, etc.)
2. Or install Ollama separately
3. Model Runner can be added later - it's just another option!

## Cost Savings

With Docker Model Runner:
- **OpenAI GPT-4**: $50-500/month → **$0**
- **Claude**: $60-600/month → **$0**
- **Total savings**: $600-6000/year!

## Next Steps

1. ✅ Enable Model Runner in Docker Desktop
2. ✅ Pull Phi-3 Mini model
3. ✅ Update .env configuration
4. ✅ Start services: `docker-compose up -d`
5. ✅ Test: http://localhost:8000/docs

---

**Need help?** Check Docker Model Runner docs: https://docs.docker.com/desktop/extensions/model-runner/
