# Multi-Backend Deployment Guide

This guide shows how to deploy the AI SEO agent on different cloud platforms and backends.

> **📘 For Azure deployment**, see the dedicated [Azure Deployment Guide](AZURE_DEPLOYMENT.md) which provides comprehensive Azure-specific instructions including Azure OpenAI, Cosmos DB, Container Apps, and more.

This document covers alternative platforms if you prefer to deploy outside of Azure.

## Current Azure Dependencies

The codebase currently uses these Azure services:

| Azure Service | Purpose | Status | Alternative Options |
|--------------|---------|--------|---------------------|
| **Azure OpenAI** | LLM/AI completions | Core | OpenAI API, Anthropic Claude, Google Gemini, Local LLMs |
| **Cosmos DB** | Database | Optional | PostgreSQL, MongoDB, MySQL, SQLite |
| **Blob Storage** | File storage | Optional | AWS S3, GCP Storage, Local filesystem, Vercel Blob |
| **Key Vault** | Secrets management | Optional | Environment variables, Vercel env, AWS Secrets Manager |
| **Monitor** | Telemetry/logging | Optional | Sentry, DataDog, CloudWatch, self-hosted |

**Good news:** Only Azure OpenAI is used for core functionality, and it can easily be swapped!

---

## Option 1: Vercel Deployment

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Vercel (Frontend + API Functions)                          │
│  ├─ Next.js/React Dashboard                                │
│  └─ API Routes (Serverless Functions)                      │
└─────────────────────────────────────────────────────────────┘
         │
         ├─── OpenAI API (LLM)
         ├─── Vercel Postgres (Database)
         ├─── Vercel Blob (File Storage)
         └─── Upstash Redis (Caching/Queue)
```

### Setup Steps

#### 1. Install Vercel Dependencies

```bash
# Add Vercel-specific packages
pip install vercel-postgres vercel-blob
```

#### 2. Create Vercel Configuration

**`vercel.json`:**
```json
{
  "version": 2,
  "builds": [
    {
      "src": "src/api/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "src/api/main.py"
    }
  ],
  "env": {
    "OPENAI_API_KEY": "@openai-api-key",
    "POSTGRES_URL": "@postgres-url",
    "REDIS_URL": "@redis-url"
  }
}
```

#### 3. Update Configuration for Vercel

**Create `src/config/vercel.py`:**
```python
"""Vercel-specific configuration."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings

class VercelSettings(BaseSettings):
    """Vercel platform settings."""

    # OpenAI (instead of Azure OpenAI)
    openai_api_key: SecretStr
    openai_model: str = "gpt-4o"

    # Vercel Postgres
    postgres_url: SecretStr

    # Vercel Blob Storage
    blob_read_write_token: SecretStr = SecretStr("")

    # Upstash Redis
    redis_url: str = ""
```

#### 4. Replace Azure OpenAI with OpenAI API

**Create `src/integrations/openai_client.py`:**
```python
"""OpenAI API client (alternative to Azure OpenAI)."""

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

class OpenAIClient:
    """Client for standard OpenAI API."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.model = model
        self._client = AsyncOpenAI(api_key=api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = False,
    ) -> str:
        """Send chat completion request."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
```

#### 5. Replace Cosmos DB with Vercel Postgres

**Create `src/storage/postgres.py`:**
```python
"""PostgreSQL storage (alternative to Cosmos DB)."""

import asyncpg
from typing import Any

class PostgresStorage:
    """PostgreSQL database client."""

    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self._pool = None

    async def init(self):
        """Initialize connection pool."""
        self._pool = await asyncpg.create_pool(self.connection_url)

    async def save_analysis(self, url: str, data: dict[str, Any]):
        """Save analysis results."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO analyses (url, data, created_at) VALUES ($1, $2, NOW())",
                url, data
            )

    async def get_analysis(self, url: str):
        """Retrieve analysis results."""
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM analyses WHERE url = $1 ORDER BY created_at DESC LIMIT 1",
                url
            )
```

#### 6. Environment Variables (Vercel Dashboard)

Add these in Vercel Project Settings → Environment Variables:

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Database
POSTGRES_URL=postgres://...

# Redis (Upstash)
REDIS_URL=redis://...

# Optional: Other APIs
GOOGLE_API_KEY=...
AHREFS_API_KEY=...
```

#### 7. Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

---

## Option 2: AWS Deployment

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ AWS                                                         │
│  ├─ ECS/Fargate (API Container)                           │
│  ├─ RDS PostgreSQL (Database)                             │
│  ├─ S3 (File Storage)                                     │
│  ├─ ElastiCache Redis (Caching)                           │
│  ├─ Secrets Manager (Secrets)                             │
│  └─ CloudWatch (Monitoring)                               │
└─────────────────────────────────────────────────────────────┘
```

### Setup Steps

#### 1. Create `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install -e .

# Copy application
COPY src/ src/

# Run API
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. AWS Configuration

**Create `aws/terraform/main.tf`:**
```hcl
# RDS PostgreSQL
resource "aws_db_instance" "seo_agent" {
  identifier     = "seo-agent-db"
  engine         = "postgres"
  engine_version = "15"
  instance_class = "db.t3.micro"

  allocated_storage = 20
  storage_type      = "gp2"

  db_name  = "seoagent"
  username = "seoagent"
  password = var.db_password
}

# S3 Bucket for storage
resource "aws_s3_bucket" "seo_data" {
  bucket = "seo-agent-data"
}

# ElastiCache Redis
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "seo-agent-cache"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
}

# ECS Service
resource "aws_ecs_service" "api" {
  name            = "seo-agent-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 2
}
```

#### 3. Environment Variables (AWS Secrets Manager)

```python
# src/config/aws.py
import boto3
import json

def get_secrets():
    """Fetch secrets from AWS Secrets Manager."""
    client = boto3.client('secretsmanager', region_name='us-east-1')

    response = client.get_secret_value(SecretId='seo-agent/prod')
    return json.loads(response['SecretString'])
```

#### 4. Deploy to AWS

```bash
# Build and push Docker image
aws ecr get-login-password --region us-east-1 | docker login ...
docker build -t seo-agent .
docker tag seo-agent:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

# Deploy with Terraform
cd aws/terraform
terraform init
terraform apply
```

---

## Option 3: Google Cloud Platform (GCP)

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ GCP                                                         │
│  ├─ Cloud Run (API Container)                              │
│  ├─ Cloud SQL PostgreSQL (Database)                        │
│  ├─ Cloud Storage (Files)                                  │
│  ├─ Memorystore Redis (Caching)                            │
│  └─ Secret Manager (Secrets)                               │
└─────────────────────────────────────────────────────────────┘
```

### Setup Steps

#### 1. Cloud Run Configuration

**`cloudbuild.yaml`:**
```yaml
steps:
  # Build container
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/seo-agent', '.']

  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/seo-agent']

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'seo-agent-api'
      - '--image=gcr.io/$PROJECT_ID/seo-agent'
      - '--region=us-central1'
      - '--platform=managed'
```

#### 2. Environment Variables

```bash
# Set secrets
gcloud secrets create openai-api-key --data-file=-
gcloud secrets create postgres-password --data-file=-

# Deploy
gcloud builds submit --config cloudbuild.yaml
```

---

## Option 4: Self-Hosted / Docker Compose

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Your Server / VPS                                           │
│  ├─ API Container (FastAPI)                                │
│  ├─ PostgreSQL Container                                   │
│  ├─ Redis Container                                        │
│  └─ Nginx (Reverse Proxy)                                 │
└─────────────────────────────────────────────────────────────┘
```

### Setup Steps

#### 1. Create `docker-compose.yml`

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - POSTGRES_URL=postgresql://postgres:postgres@db:5432/seoagent
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: seoagent
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - api

volumes:
  postgres_data:
  redis_data:
```

#### 2. Deploy

```bash
# Create .env file with secrets
echo "OPENAI_API_KEY=sk-..." > .env

# Start services
docker-compose up -d

# View logs
docker-compose logs -f api
```

---

## LLM Provider Alternatives

Instead of Azure OpenAI, you can use:

### 1. OpenAI API (Recommended for Vercel)

```python
# No changes needed - uses same openai library!
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key="sk-...")
```

### 2. Anthropic Claude

```bash
pip install anthropic
```

```python
from anthropic import AsyncAnthropic

class ClaudeClient:
    def __init__(self, api_key: str):
        self._client = AsyncAnthropic(api_key=api_key)

    async def chat(self, messages, temperature=0.7, max_tokens=2000):
        response = await self._client.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.content[0].text
```

### 3. Google Gemini

```bash
pip install google-generativeai
```

```python
import google.generativeai as genai

class GeminiClient:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    async def chat(self, messages, temperature=0.7):
        # Convert messages format
        prompt = messages[-1]['content']
        response = await self.model.generate_content_async(prompt)
        return response.text
```

### 4. Local LLMs (Ollama, LM Studio)

```python
import httpx

class LocalLLMClient:
    def __init__(self, endpoint: str = "http://localhost:11434"):
        self.endpoint = endpoint

    async def chat(self, messages, model="llama3", temperature=0.7):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                }
            )
            return response.json()['message']['content']
```

---

## Database Alternatives

### 1. PostgreSQL (Recommended)

```bash
pip install asyncpg sqlalchemy[asyncio]
```

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
SessionLocal = sessionmaker(engine, class_=AsyncSession)
```

### 2. MongoDB

```bash
pip install motor  # Async MongoDB driver
```

```python
from motor.motor_asyncio import AsyncIOMotorClient

class MongoStorage:
    def __init__(self, connection_url: str):
        self.client = AsyncIOMotorClient(connection_url)
        self.db = self.client.seo_agent

    async def save_analysis(self, url: str, data: dict):
        await self.db.analyses.insert_one({
            "url": url,
            "data": data,
            "created_at": datetime.utcnow()
        })
```

### 3. SQLite (Development/Small Scale)

```python
import aiosqlite

class SQLiteStorage:
    def __init__(self, db_path: str = "./seo_agent.db"):
        self.db_path = db_path

    async def save_analysis(self, url: str, data: dict):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO analyses (url, data) VALUES (?, ?)",
                (url, json.dumps(data))
            )
            await db.commit()
```

---

## Quick Migration Guide

### From Azure to Vercel (Fastest)

1. **Replace Azure OpenAI with OpenAI:**
   ```python
   # Old: Azure OpenAI
   from src.integrations.azure_openai import AzureOpenAIClient

   # New: Standard OpenAI
   from openai import AsyncOpenAI
   client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
   ```

2. **Add Vercel Postgres:**
   ```bash
   vercel postgres create
   ```

3. **Deploy:**
   ```bash
   vercel --prod
   ```

### From Azure to AWS (Full Stack)

1. **Containerize:**
   ```bash
   docker build -t seo-agent .
   ```

2. **Push to ECR:**
   ```bash
   aws ecr push ...
   ```

3. **Deploy to ECS/Fargate:**
   ```bash
   terraform apply
   ```

---

## Recommended Setups by Use Case

| Use Case | Platform | Database | LLM | Storage | Cost/Month |
|----------|----------|----------|-----|---------|------------|
| **MVP/Prototype** | Vercel | Vercel Postgres | OpenAI API | Vercel Blob | ~$20-50 |
| **Small Business** | Docker Compose | PostgreSQL | OpenAI/Claude | Local/S3 | ~$30-100 |
| **Enterprise** | AWS/GCP | RDS/Cloud SQL | Azure OpenAI | S3/Cloud Storage | ~$500+ |
| **Self-Hosted** | VPS | PostgreSQL | Local LLM (Ollama) | Local FS | ~$10-20 |

---

## Next Steps

1. Choose your platform (Vercel recommended for quick start)
2. Set up database (Vercel Postgres for Vercel, RDS for AWS)
3. Replace Azure OpenAI with your chosen LLM provider
4. Update environment variables
5. Deploy!

Would you like me to create specific deployment scripts for your chosen platform?
