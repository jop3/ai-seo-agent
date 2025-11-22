# Docker Model Runner - Local LLM Setup

Run AI models locally with **zero API costs** using Docker Model Runner.

## What is Docker Model Runner?

Docker Model Runner is a built-in feature in **Docker Desktop 4.41+** that allows you to run AI models as Docker containers with an OpenAI-compatible API. This means:

- ✅ **100% Free** - No API costs
- ✅ **100% Private** - Data never leaves your machine
- ✅ **OpenAI-compatible** - Works with existing OpenAI SDK code
- ✅ **Auto-download** - Models automatically pulled on first run
- ✅ **Simple setup** - Just `docker-compose up`

## Requirements

- Docker Desktop 4.41 or later
- Docker Compose v2.35.0 or later
- Minimum 4GB RAM (8GB+ recommended)
- 10GB+ free disk space

## Quick Start

### 1. Run Hardware Analysis

Check which models your system can run:

```bash
python3 scripts/analyze_hardware.py
```

This will show you:
- System RAM, CPU, GPU
- Recommended models (Fast/Balanced/Smart)
- Speed vs quality trade-offs

### 2. Run Setup Wizard

```bash
python3 scripts/setup.py
```

Choose:
- **Platform**: Docker Compose
- **LLM Provider**: Docker Model Runner
- **Model**: Based on hardware analysis recommendations

The wizard will:
- Analyze your hardware
- Show models your system can run
- Generate `docker-compose.yml` with the selected model
- Create `.env` configuration

### 3. Start Everything

```bash
docker-compose up -d
```

The first run will:
- Download the selected model (2-5 minutes)
- Start PostgreSQL and Redis
- Start your API server
- Expose the model at `http://localhost:8080`

### 4. Access Your API

```bash
curl http://localhost:8000/docs
```

## Available Models

Docker Model Runner supports multiple models from Docker Hub's AI registry:

| Model | Size | RAM | Speed | Quality | Best For |
|-------|------|-----|-------|---------|----------|
| **ai/smollm2-135m-instruct** | 135M | 1GB | ⚡⚡⚡ Very Fast | ⭐⭐ Good | Testing, development |
| **ai/smollm2-360m-instruct** | 360M | 2GB | ⚡⚡⚡ Very Fast | ⭐⭐⭐ Better | Quick responses |
| **ai/llama3.2-1b-instruct** | 1B | 2GB | ⚡⚡⚡ Very Fast | ⭐⭐⭐ Better | Compact, fast |
| **ai/phi3-mini-4k-instruct** | 3.8B | 4GB | ⚡⚡ Fast | ⭐⭐⭐⭐ Great | **Recommended** |
| **ai/llama3.2-3b-instruct** | 3B | 4GB | ⚡⚡ Fast | ⭐⭐⭐⭐ Great | Balanced |
| **ai/gemma2-2b-instruct** | 2B | 3GB | ⚡⚡ Fast | ⭐⭐⭐ Better | Google model |

## Model Selection Guide

### Fast Models (⚡⚡⚡)
**Best for**: Development, testing, quick iterations
- SmolLM2 135M/360M
- Llama 3.2 1B
- **Speed**: Instant responses (<1s)
- **Quality**: Good for basic tasks

### Balanced Models (⚡⚡ - Recommended)
**Best for**: Production, most use cases
- **Phi-3 Mini** ⭐ Recommended
- Llama 3.2 3B
- Gemma 2 2B
- **Speed**: Fast responses (1-3s)
- **Quality**: Great for SEO analysis

### Smart Models (⚡)
**Best for**: Complex analysis, high quality needed
- Larger models (if you have 8GB+ RAM)
- **Speed**: Slower responses (3-10s)
- **Quality**: Excellent, near GPT-4 quality

## Configuration

### Basic docker-compose.yml

```yaml
version: '3.8'

services:
  # Local LLM
  llm:
    image: ai/phi3-mini-4k-instruct
    ports:
      - "8080:8080"
    environment:
      - MODEL_ID=ai/phi3-mini-4k-instruct

  # Your app
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_BASE=http://llm:8080/v1
      - OPENAI_API_KEY=not-needed
    depends_on:
      - llm
```

### GPU Acceleration (NVIDIA)

If you have an NVIDIA GPU, uncomment these lines in `docker-compose.yml`:

```yaml
llm:
  image: ai/phi3-mini-4k-instruct
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

This will use your GPU and make models **5-10x faster**.

## Usage Examples

### Testing the Model

```bash
# Test the LLM directly
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "phi3-mini",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Using with Python OpenAI SDK

```python
from openai import OpenAI

# Point to local model
client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="not-needed"
)

response = client.chat.completions.create(
    model="phi3-mini",
    messages=[{"role": "user", "content": "Analyze this webpage..."}]
)
```

## Monitoring

### View Logs

```bash
# View API logs
docker-compose logs -f api

# View LLM model logs
docker-compose logs -f llm

# View all logs
docker-compose logs -f
```

### Check Resource Usage

```bash
# Check Docker stats
docker stats

# Check model container
docker stats seo-agent-llm-1
```

## Troubleshooting

### Model download is slow

Docker Model Runner downloads models from Docker Hub. First run may take 2-10 minutes depending on model size and network speed.

```bash
# View download progress
docker-compose logs -f llm
```

### Out of memory

If you get OOM errors:

1. Check available RAM: `free -h` (Linux) or `vm_stat` (macOS)
2. Choose a smaller model (e.g., SmolLM2 instead of Llama)
3. Close other applications
4. Increase Docker Desktop memory limit (Preferences → Resources)

### Model not responding

```bash
# Restart the LLM service
docker-compose restart llm

# Check if model is healthy
curl http://localhost:8080/health
```

### Wrong Docker version

Docker Model Runner requires:
- Docker Desktop 4.41+
- Docker Compose v2.35.0+

Check versions:
```bash
docker --version
docker-compose --version
```

Upgrade Docker Desktop: https://www.docker.com/products/docker-desktop

## Performance Tips

### 1. Choose the Right Model

- **Development**: SmolLM2 360M (instant responses)
- **Production**: Phi-3 Mini or Llama 3.2 3B (best balance)
- **Quality-critical**: Largest model your RAM supports

### 2. Enable GPU Acceleration

If you have NVIDIA GPU, enable it in docker-compose.yml for 5-10x speedup.

### 3. Increase Context Size

Some models support larger context:

```yaml
llm:
  image: ai/phi3-mini-4k-instruct
  environment:
    - CONTEXT_SIZE=4096  # Increase for longer inputs
```

### 4. Adjust Thread Count

```yaml
llm:
  environment:
    - NUM_THREADS=8  # Match your CPU cores
```

## Cost Comparison

| Provider | Cost/Month | Speed | Quality |
|----------|-----------|-------|---------|
| **Docker Model Runner** | **$0** | Medium | Good-Great |
| OpenAI GPT-4o | $50-500 | Fast | Excellent |
| Anthropic Claude | $60-600 | Fast | Excellent |
| Azure OpenAI | $50-500 | Fast | Excellent |

**Docker Model Runner saves $600-6000/year** for moderate usage!

## Switching Between Models

You can easily switch models by editing `docker-compose.yml`:

```yaml
# Change this line:
image: ai/phi3-mini-4k-instruct

# To any other model:
image: ai/llama3.2-3b-instruct
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

## Migration from OpenAI

Already using OpenAI? No code changes needed!

Just update your environment variables:

```bash
# Before (OpenAI)
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1

# After (Docker Model Runner)
OPENAI_API_KEY=not-needed
OPENAI_API_BASE=http://llm:8080/v1
```

Your code continues working as-is!

## Additional Resources

- [Docker Model Runner Official Docs](https://docs.docker.com/ai/model-runner/)
- [Available Models on Docker Hub](https://hub.docker.com/search?q=ai%2F)
- [Hardware Analysis Script](scripts/analyze_hardware.py)
- [Setup Wizard](scripts/setup.py)

## Support

If you encounter issues:

1. Run hardware analysis: `python3 scripts/analyze_hardware.py`
2. Check Docker version: `docker --version` (need 4.41+)
3. View logs: `docker-compose logs -f llm`
4. Try a smaller model if OOM errors occur

For Docker Model Runner issues, see the [official troubleshooting guide](https://docs.docker.com/ai/model-runner/).
