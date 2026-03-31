#!/usr/bin/env python3
"""Simple hardware check for Windows - no emojis"""
import platform
import psutil
import subprocess

print("=" * 60)
print("System Hardware Analysis")
print("=" * 60)
print()

# Basic system info
print(f"Platform: {platform.system()} {platform.release()}")
print(f"Python: {platform.python_version()}")
print()

# CPU
cpu_count = psutil.cpu_count(logical=False)
cpu_threads = psutil.cpu_count(logical=True)
print(f"CPU Cores: {cpu_count} physical, {cpu_threads} logical")

# Memory
ram = psutil.virtual_memory()
total_gb = ram.total / (1024**3)
available_gb = ram.available / (1024**3)
print(f"RAM: {total_gb:.1f} GB total, {available_gb:.1f} GB available")

# Disk
disk = psutil.disk_usage('.')
disk_free_gb = disk.free / (1024**3)
print(f"Disk Space: {disk_free_gb:.1f} GB free")

# GPU detection
has_gpu = False
gpu_info = "Not detected"
try:
    result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0 and result.stdout.strip():
        gpu_info = result.stdout.strip()
        has_gpu = True
except:
    pass

print(f"GPU: {gpu_info}")
print()

# Model recommendations
print("=" * 60)
print("Recommended Local LLM Models")
print("=" * 60)
print()

if total_gb >= 16:
    print("RECOMMENDED: Phi-3 Mini (3.8B parameters)")
    print("  - RAM Required: 4GB")
    print("  - Speed: Fast")
    print("  - Quality: Great")
    print("  - Docker Model: ai/phi3-mini-4k-instruct")
    print()
    print("Alternative: Llama 3.2 3B")
    print("  - RAM Required: 4GB")
    print("  - Speed: Fast")
    print("  - Quality: Great")
    print()
elif total_gb >= 8:
    print("RECOMMENDED: Llama 3.2 1B")
    print("  - RAM Required: 2GB")
    print("  - Speed: Very Fast")
    print("  - Quality: Good")
    print("  - Docker Model: ai/llama3.2:1b")
    print()
    print("Alternative: Phi-3 Mini (if you have 8GB+)")
    print("  - RAM Required: 4GB")
    print()
elif total_gb >= 4:
    print("RECOMMENDED: SmolLM2 360M")
    print("  - RAM Required: 2GB")
    print("  - Speed: Very Fast")
    print("  - Quality: Good for testing")
    print()
else:
    print("WARNING: Low RAM detected. 4GB+ recommended for local LLMs")

print()
print("=" * 60)
print("Next Steps")
print("=" * 60)
print()
print("To set up Docker Model Runner with local LLM:")
print()
print("1. Update your .env file:")
print("   OPENAI_API_BASE=http://llm:8080/v1")
print("   OPENAI_API_KEY=not-needed")
print()
print("2. Add LLM service to docker-compose.yml (I'll do this for you!)")
print()
print("3. Restart: docker-compose up -d")
print()
