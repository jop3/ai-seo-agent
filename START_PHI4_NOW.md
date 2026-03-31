# Start Phi-4 Model NOW - Quick Fix

## The Problem
Your AI SEO Agent can't connect to Phi-4 because the model isn't running yet!

## Quick Fix (2 minutes)

### Option 1: Docker Desktop UI (Easiest)

1. **Open Docker Desktop**
2. Go to **"Models"** tab (left sidebar)
3. Find **"phi4:latest"** in your pulled models
4. Click **"Run"** or **"Start"**
5. Wait for it to load (~30 seconds)
6. Test: Refresh your chat UI!

### Option 2: Command Line (Fast)

```bash
# Start Phi-4 model
docker run -d \
  --name phi4 \
  --gpus all \
  -p 8080:11434 \
  -v ollama-data:/root/.ollama \
  ollama/ollama

# Wait for container to start
sleep 5

# Load the Phi-4 model
docker exec phi4 ollama run phi4

# Keep it running
docker exec -d phi4 ollama serve
```

### Option 3: Use Ollama Directly

If Model Runner isn't working, use Ollama:

```bash
# Start Ollama
docker run -d \
  --name ollama \
  --gpus all \
  -p 11434:11434 \
  -v ollama-data:/root/.ollama \
  ollama/ollama

# Pull and run Phi-4
docker exec ollama ollama pull phi4
docker exec ollama ollama run phi4
```

Then update `.env`:
```bash
OPENAI_API_BASE=http://host.docker.internal:11434/v1
```

## Verify It's Working

```bash
# Test the model endpoint
curl http://localhost:8080/v1/models
# or
curl http://localhost:11434/v1/models

# Should return list of models including phi4
```

## Then Restart Your Services

```bash
docker-compose restart api worker ui
```

## Alternative: Quick Test Without Model

Want to test the UI works first? Use a cloud model temporarily:

Edit `.env`:
```bash
# Temporary: Use OpenAI for testing
OPENAI_API_KEY=your-actual-openai-key
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo
```

Then:
```bash
docker-compose restart api worker ui
```

Once you confirm the UI works, switch back to local Phi-4!

## What's Happening

The chat UI is trying to connect to Phi-4 at:
- `http://host.docker.internal:8080/v1`

But Phi-4 isn't running on that port yet!

**Start the model and everything will work!**

---

**TL;DR**: Open Docker Desktop → Models → Find phi4:latest → Click Run
