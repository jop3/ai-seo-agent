"""
Tests for hardware analysis script.
"""
import pytest
from scripts.analyze_hardware import (
    SystemSpecs,
    ModelRecommendation,
    get_model_recommendations,
)


class TestSystemSpecs:
    """Test SystemSpecs dataclass."""

    def test_system_specs_creation(self):
        """Test creating SystemSpecs instance."""
        specs = SystemSpecs(
            total_ram_gb=16.0,
            available_ram_gb=12.0,
            cpu_count=8,
            has_gpu=True,
            gpu_name="NVIDIA RTX 3080",
            gpu_memory_gb=10.0,
            platform="Linux",
            disk_space_gb=100.0,
        )

        assert specs.total_ram_gb == 16.0
        assert specs.available_ram_gb == 12.0
        assert specs.cpu_count == 8
        assert specs.has_gpu is True
        assert specs.gpu_name == "NVIDIA RTX 3080"
        assert specs.gpu_memory_gb == 10.0


class TestModelRecommendation:
    """Test ModelRecommendation dataclass."""

    def test_model_recommendation_creation(self):
        """Test creating ModelRecommendation instance."""
        model = ModelRecommendation(
            name="Phi-3 Mini",
            provider="docker_model_runner",
            identifier="ai/phi3-mini-4k-instruct",
            ram_required_gb=4.0,
            vram_required_gb=None,
            speed="⚡ Fast",
            quality="⭐⭐⭐⭐ Great",
            description="Balanced model",
        )

        assert model.name == "Phi-3 Mini"
        assert model.provider == "docker_model_runner"
        assert model.identifier == "ai/phi3-mini-4k-instruct"
        assert model.ram_required_gb == 4.0
        assert model.vram_required_gb is None


class TestModelRecommendations:
    """Test model recommendation logic."""

    def test_low_memory_system_recommendations(self):
        """Test recommendations for low memory system (2GB)."""
        specs = SystemSpecs(
            total_ram_gb=2.0,
            available_ram_gb=1.5,
            cpu_count=2,
            has_gpu=False,
            gpu_name=None,
            gpu_memory_gb=None,
            platform="Linux",
            disk_space_gb=50.0,
        )

        recommendations = get_model_recommendations(specs)

        # Should have fast/small models only
        assert len(recommendations["fast"]) > 0

        # All recommended models should fit in 1.5GB RAM
        for category in ["fast", "balanced", "smart"]:
            for model in recommendations[category]:
                if model.provider == "docker_model_runner":
                    assert model.ram_required_gb <= 1.5

    def test_medium_memory_system_recommendations(self):
        """Test recommendations for medium memory system (8GB)."""
        specs = SystemSpecs(
            total_ram_gb=8.0,
            available_ram_gb=6.0,
            cpu_count=4,
            has_gpu=False,
            gpu_name=None,
            gpu_memory_gb=None,
            platform="Linux",
            disk_space_gb=100.0,
        )

        recommendations = get_model_recommendations(specs)

        # Should have models in all categories
        assert len(recommendations["fast"]) > 0
        assert len(recommendations["balanced"]) > 0

        # All Docker Model Runner models should fit in 6GB RAM
        for category in ["fast", "balanced", "smart"]:
            for model in recommendations[category]:
                if model.provider == "docker_model_runner":
                    assert model.ram_required_gb <= 6.0

    def test_high_memory_system_recommendations(self):
        """Test recommendations for high memory system (16GB+)."""
        specs = SystemSpecs(
            total_ram_gb=16.0,
            available_ram_gb=14.0,
            cpu_count=8,
            has_gpu=False,
            gpu_name=None,
            gpu_memory_gb=None,
            platform="Linux",
            disk_space_gb=200.0,
        )

        recommendations = get_model_recommendations(specs)

        # Should have models in all categories
        assert len(recommendations["fast"]) > 0
        assert len(recommendations["balanced"]) > 0
        assert len(recommendations["smart"]) > 0

        # Should include larger models
        all_models = (
            recommendations["fast"]
            + recommendations["balanced"]
            + recommendations["smart"]
        )
        large_models = [m for m in all_models if m.ram_required_gb >= 8.0]

        # With 14GB available, should recommend some 8GB models
        assert len(large_models) > 0

    def test_gpu_system_recommendations(self):
        """Test recommendations for system with GPU."""
        specs = SystemSpecs(
            total_ram_gb=16.0,
            available_ram_gb=12.0,
            cpu_count=8,
            has_gpu=True,
            gpu_name="NVIDIA RTX 3080",
            gpu_memory_gb=10.0,
            platform="Linux",
            disk_space_gb=200.0,
        )

        recommendations = get_model_recommendations(specs)

        # Should include Ollama models that can use GPU
        ollama_models = []
        for category in ["fast", "balanced", "smart"]:
            for model in recommendations[category]:
                if model.provider == "ollama":
                    ollama_models.append(model)

        # Ollama models should be recommended with GPU
        assert len(ollama_models) > 0

        # Check that Ollama models respect VRAM limits
        for model in ollama_models:
            if model.vram_required_gb:
                assert model.vram_required_gb <= 10.0

    def test_recommendations_categorization(self):
        """Test that models are properly categorized."""
        specs = SystemSpecs(
            total_ram_gb=8.0,
            available_ram_gb=6.0,
            cpu_count=4,
            has_gpu=False,
            gpu_name=None,
            gpu_memory_gb=None,
            platform="Linux",
            disk_space_gb=100.0,
        )

        recommendations = get_model_recommendations(specs)

        # Fast models should have "Fast" or "Very Fast" in speed
        for model in recommendations["fast"]:
            assert "Fast" in model.speed

        # Balanced models should have Better, Great, or Excellent quality
        for model in recommendations["balanced"]:
            assert any(
                quality in model.quality
                for quality in ["Better", "Great", "Excellent"]
            )

        # Smart models should have Great or Excellent quality
        for model in recommendations["smart"]:
            assert any(
                quality in model.quality for quality in ["Great", "Excellent", "Best"]
            )

    def test_no_out_of_memory_recommendations(self):
        """Test that recommendations never exceed available RAM."""
        specs = SystemSpecs(
            total_ram_gb=4.0,
            available_ram_gb=3.0,
            cpu_count=2,
            has_gpu=False,
            gpu_name=None,
            gpu_memory_gb=None,
            platform="Linux",
            disk_space_gb=50.0,
        )

        recommendations = get_model_recommendations(specs)

        # Check all recommended models
        for category in ["fast", "balanced", "smart"]:
            for model in recommendations[category]:
                # Docker Model Runner models should fit in available RAM
                if model.provider == "docker_model_runner":
                    assert (
                        model.ram_required_gb <= 3.0
                    ), f"{model.name} requires {model.ram_required_gb}GB but only {3.0}GB available"

    def test_docker_model_runner_models_present(self):
        """Test that Docker Model Runner models are included."""
        specs = SystemSpecs(
            total_ram_gb=8.0,
            available_ram_gb=6.0,
            cpu_count=4,
            has_gpu=False,
            gpu_name=None,
            gpu_memory_gb=None,
            platform="Linux",
            disk_space_gb=100.0,
        )

        recommendations = get_model_recommendations(specs)

        # Should have Docker Model Runner models
        docker_models = []
        for category in ["fast", "balanced", "smart"]:
            for model in recommendations[category]:
                if model.provider == "docker_model_runner":
                    docker_models.append(model)

        assert len(docker_models) > 0

        # Check for expected models
        model_names = [m.name for m in docker_models]
        # Should have at least some of the common models
        assert any("Phi" in name for name in model_names) or any(
            "Llama" in name for name in model_names
        )

    def test_minimum_ram_no_recommendations(self):
        """Test system with insufficient RAM gets limited recommendations."""
        specs = SystemSpecs(
            total_ram_gb=0.5,
            available_ram_gb=0.3,
            cpu_count=1,
            has_gpu=False,
            gpu_name=None,
            gpu_memory_gb=None,
            platform="Linux",
            disk_space_gb=10.0,
        )

        recommendations = get_model_recommendations(specs)

        # With only 0.3GB available, should have very few or no recommendations
        total_recommendations = (
            len(recommendations["fast"])
            + len(recommendations["balanced"])
            + len(recommendations["smart"])
        )

        # Most models require at least 1GB
        assert total_recommendations < 5
