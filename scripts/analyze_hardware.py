#!/usr/bin/env python3
"""
Hardware Analysis Script for AI SEO Agent
Analyzes system resources and recommends optimal LLM models.
"""

import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
except ImportError:
    print("Installing required dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "-q"])
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel

console = Console()


@dataclass
class SystemSpecs:
    """System hardware specifications."""
    total_ram_gb: float
    available_ram_gb: float
    cpu_count: int
    has_gpu: bool
    gpu_name: Optional[str]
    gpu_memory_gb: Optional[float]
    platform: str
    disk_space_gb: float


@dataclass
class ModelRecommendation:
    """LLM model recommendation."""
    name: str
    provider: str  # "docker_model_runner", "ollama"
    identifier: str  # Docker model name or Ollama model name
    ram_required_gb: float
    vram_required_gb: Optional[float]
    speed: str  # "Fast", "Medium", "Slow"
    quality: str  # "Good", "Better", "Best"
    description: str


def get_system_specs() -> SystemSpecs:
    """Analyze system hardware specifications."""

    # Get RAM info
    total_ram_gb = 0
    available_ram_gb = 0

    try:
        if platform.system() == "Linux":
            with open("/proc/meminfo", "r") as f:
                meminfo = f.read()
                for line in meminfo.split("\n"):
                    if "MemTotal:" in line:
                        total_ram_gb = int(line.split()[1]) / (1024 ** 2)
                    elif "MemAvailable:" in line:
                        available_ram_gb = int(line.split()[1]) / (1024 ** 2)
        elif platform.system() == "Darwin":  # macOS
            result = subprocess.run(["sysctl", "hw.memsize"], capture_output=True, text=True)
            total_ram_gb = int(result.stdout.split(":")[1].strip()) / (1024 ** 3)
            # macOS doesn't easily provide available RAM, estimate 70%
            available_ram_gb = total_ram_gb * 0.7
        elif platform.system() == "Windows":
            try:
                import psutil
                mem = psutil.virtual_memory()
                total_ram_gb = mem.total / (1024 ** 3)
                available_ram_gb = mem.available / (1024 ** 3)
            except ImportError:
                # Fallback without psutil
                result = subprocess.run(
                    ["wmic", "ComputerSystem", "get", "TotalPhysicalMemory"],
                    capture_output=True, text=True
                )
                total_ram_gb = int(result.stdout.split("\n")[1].strip()) / (1024 ** 3)
                available_ram_gb = total_ram_gb * 0.7
    except Exception as e:
        console.print(f"[yellow]Warning: Could not detect RAM: {e}[/]")
        total_ram_gb = 8.0  # Default assumption
        available_ram_gb = 5.0

    # Get CPU count
    cpu_count = os.cpu_count() or 4

    # Check for GPU
    has_gpu = False
    gpu_name = None
    gpu_memory_gb = None

    try:
        # Try NVIDIA GPU
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            gpu_info = result.stdout.strip().split(",")
            has_gpu = True
            gpu_name = gpu_info[0].strip()
            gpu_memory_gb = float(gpu_info[1].strip().split()[0]) / 1024
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        pass

    # Get disk space
    disk_space_gb = 0
    try:
        if platform.system() != "Windows":
            result = subprocess.run(["df", "-BG", "."], capture_output=True, text=True)
            disk_space_gb = float(result.stdout.split("\n")[1].split()[3].replace("G", ""))
        else:
            import shutil
            disk_space_gb = shutil.disk_usage(".").free / (1024 ** 3)
    except Exception:
        disk_space_gb = 50.0  # Default assumption

    return SystemSpecs(
        total_ram_gb=total_ram_gb,
        available_ram_gb=available_ram_gb,
        cpu_count=cpu_count,
        has_gpu=has_gpu,
        gpu_name=gpu_name,
        gpu_memory_gb=gpu_memory_gb,
        platform=platform.system(),
        disk_space_gb=disk_space_gb
    )


def get_model_recommendations(specs: SystemSpecs) -> dict[str, list[ModelRecommendation]]:
    """Get model recommendations based on system specs."""

    recommendations = {
        "fast": [],
        "balanced": [],
        "smart": []
    }

    # Docker Model Runner models (requires Docker Desktop 4.41+)
    docker_models = [
        ModelRecommendation(
            name="SmolLM2 135M",
            provider="docker_model_runner",
            identifier="ai/smollm2-135m-instruct",
            ram_required_gb=1.0,
            vram_required_gb=None,
            speed="⚡ Very Fast",
            quality="⭐⭐ Good",
            description="Tiny model, instant responses, good for basic tasks"
        ),
        ModelRecommendation(
            name="SmolLM2 360M",
            provider="docker_model_runner",
            identifier="ai/smollm2-360m-instruct",
            ram_required_gb=2.0,
            vram_required_gb=None,
            speed="⚡ Very Fast",
            quality="⭐⭐⭐ Better",
            description="Small model, very fast, decent quality"
        ),
        ModelRecommendation(
            name="Phi-3 Mini 3.8B",
            provider="docker_model_runner",
            identifier="ai/phi3-mini-4k-instruct",
            ram_required_gb=4.0,
            vram_required_gb=None,
            speed="⚡ Fast",
            quality="⭐⭐⭐⭐ Great",
            description="Microsoft's efficient model, excellent balance"
        ),
        ModelRecommendation(
            name="Llama 3.2 1B",
            provider="docker_model_runner",
            identifier="ai/llama3.2-1b-instruct",
            ram_required_gb=2.0,
            vram_required_gb=None,
            speed="⚡ Very Fast",
            quality="⭐⭐⭐ Better",
            description="Meta's compact model, fast and capable"
        ),
        ModelRecommendation(
            name="Llama 3.2 3B",
            provider="docker_model_runner",
            identifier="ai/llama3.2-3b-instruct",
            ram_required_gb=4.0,
            vram_required_gb=None,
            speed="⚡ Fast",
            quality="⭐⭐⭐⭐ Great",
            description="Meta's balanced model, excellent for most tasks"
        ),
        ModelRecommendation(
            name="Gemma 2B",
            provider="docker_model_runner",
            identifier="ai/gemma2-2b-instruct",
            ram_required_gb=3.0,
            vram_required_gb=None,
            speed="⚡ Fast",
            quality="⭐⭐⭐ Better",
            description="Google's compact model, fast responses"
        ),
    ]

    # Ollama models (alternative, requires separate Ollama installation)
    ollama_models = [
        ModelRecommendation(
            name="Llama 3.2 1B (Ollama)",
            provider="ollama",
            identifier="llama3.2:1b",
            ram_required_gb=2.0,
            vram_required_gb=2.0,
            speed="⚡ Very Fast",
            quality="⭐⭐⭐ Better",
            description="Via Ollama - Meta's compact model"
        ),
        ModelRecommendation(
            name="Llama 3.2 3B (Ollama)",
            provider="ollama",
            identifier="llama3.2:3b",
            ram_required_gb=4.0,
            vram_required_gb=4.0,
            speed="⚡ Fast",
            quality="⭐⭐⭐⭐ Great",
            description="Via Ollama - Balanced performance"
        ),
        ModelRecommendation(
            name="Llama 3.1 8B (Ollama)",
            provider="ollama",
            identifier="llama3.1:8b",
            ram_required_gb=8.0,
            vram_required_gb=8.0,
            speed="🐢 Medium",
            quality="⭐⭐⭐⭐⭐ Excellent",
            description="Via Ollama - High quality, slower"
        ),
    ]

    # Categorize based on system specs
    available_ram = specs.available_ram_gb

    for model in docker_models + ollama_models:
        # Check if system can run this model
        can_run = model.ram_required_gb <= available_ram

        if specs.has_gpu and model.vram_required_gb:
            can_run = can_run and (model.vram_required_gb <= (specs.gpu_memory_gb or 0))

        if not can_run:
            continue

        # Categorize by speed/quality profile
        if "Very Fast" in model.speed:
            recommendations["fast"].append(model)

        if "Great" in model.quality or "Better" in model.quality:
            recommendations["balanced"].append(model)

        if "Excellent" in model.quality or "Best" in model.quality or "Great" in model.quality:
            recommendations["smart"].append(model)

    return recommendations


def display_system_info(specs: SystemSpecs):
    """Display system information."""
    console.print("\n[bold cyan]System Analysis[/]\n")

    info_table = Table(show_header=False, box=None)
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="green")

    info_table.add_row("Platform", specs.platform)
    info_table.add_row("CPU Cores", str(specs.cpu_count))
    info_table.add_row("Total RAM", f"{specs.total_ram_gb:.1f} GB")
    info_table.add_row("Available RAM", f"{specs.available_ram_gb:.1f} GB")

    if specs.has_gpu:
        info_table.add_row("GPU", f"✅ {specs.gpu_name}")
        if specs.gpu_memory_gb:
            info_table.add_row("GPU Memory", f"{specs.gpu_memory_gb:.1f} GB")
    else:
        info_table.add_row("GPU", "❌ Not detected")

    info_table.add_row("Free Disk Space", f"{specs.disk_space_gb:.1f} GB")

    console.print(info_table)


def display_recommendations(
    recommendations: dict[str, list[ModelRecommendation]],
    specs: SystemSpecs
):
    """Display model recommendations."""

    console.print("\n[bold cyan]Model Recommendations[/]\n")

    # Fast models
    if recommendations["fast"]:
        console.print("[bold]⚡ Fast Models[/] - Quick responses, good for development\n")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Model", style="cyan", width=25)
        table.add_column("Provider", style="yellow", width=20)
        table.add_column("Speed", width=15)
        table.add_column("Quality", width=15)
        table.add_column("RAM", style="green", width=10)

        for model in recommendations["fast"][:3]:  # Top 3
            table.add_row(
                model.name,
                model.provider.replace("_", " ").title(),
                model.speed,
                model.quality,
                f"{model.ram_required_gb:.1f} GB"
            )

        console.print(table)
        console.print()

    # Balanced models
    if recommendations["balanced"]:
        console.print("[bold]⚖️  Balanced Models[/] - Best speed/quality trade-off\n")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Model", style="cyan", width=25)
        table.add_column("Provider", style="yellow", width=20)
        table.add_column("Speed", width=15)
        table.add_column("Quality", width=15)
        table.add_column("RAM", style="green", width=10)

        for model in recommendations["balanced"][:3]:  # Top 3
            table.add_row(
                model.name,
                model.provider.replace("_", " ").title(),
                model.speed,
                model.quality,
                f"{model.ram_required_gb:.1f} GB"
            )

        console.print(table)
        console.print()

    # Smart models
    if recommendations["smart"]:
        console.print("[bold]🧠 Smart Models[/] - Highest quality, slower responses\n")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Model", style="cyan", width=25)
        table.add_column("Provider", style="yellow", width=20)
        table.add_column("Speed", width=15)
        table.add_column("Quality", width=15)
        table.add_column("RAM", style="green", width=10)

        for model in recommendations["smart"][:3]:  # Top 3
            table.add_row(
                model.name,
                model.provider.replace("_", " ").title(),
                model.speed,
                model.quality,
                f"{model.ram_required_gb:.1f} GB"
            )

        console.print(table)
        console.print()

    # Show recommendation
    if specs.available_ram_gb >= 8:
        rec_text = "[green]Your system can run high-quality models![/]"
    elif specs.available_ram_gb >= 4:
        rec_text = "[yellow]Recommend balanced models for best experience[/]"
    else:
        rec_text = "[yellow]Recommend fast/small models due to limited RAM[/]"

    console.print(Panel(rec_text, title="Recommendation", border_style="cyan"))


def get_top_recommendation(specs: SystemSpecs) -> Optional[ModelRecommendation]:
    """Get single top recommendation based on specs."""
    recommendations = get_model_recommendations(specs)

    # Prefer balanced models
    if recommendations["balanced"]:
        return recommendations["balanced"][0]
    elif recommendations["fast"]:
        return recommendations["fast"][0]
    elif recommendations["smart"]:
        return recommendations["smart"][0]

    return None


def main():
    """Main function."""
    console.clear()

    panel = Panel(
        "[bold cyan]🔍 Hardware Analysis for AI SEO Agent[/]\n\n"
        "Analyzing your system to recommend optimal LLM models...",
        border_style="cyan"
    )
    console.print(panel)
    console.print()

    # Analyze system
    with console.status("[cyan]Analyzing system hardware...[/]"):
        specs = get_system_specs()

    # Display results
    display_system_info(specs)

    # Get recommendations
    recommendations = get_model_recommendations(specs)
    display_recommendations(recommendations, specs)

    # Docker info
    console.print("\n[bold]Note:[/]")
    console.print("• [cyan]Docker Model Runner[/] models require Docker Desktop 4.41+")
    console.print("• [cyan]Ollama[/] models require separate Ollama installation")
    console.print("• All models run 100% locally with no API costs")
    console.print("\n[dim]Run [yellow]python3 scripts/setup.py[/] to configure your setup[/]\n")


if __name__ == "__main__":
    main()
