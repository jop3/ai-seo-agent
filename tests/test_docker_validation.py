"""
Tests for Docker configuration validation.

Note: Docker Desktop is not available in this test environment,
so these tests validate the docker-compose.yml syntax and structure
without actually running Docker.
"""
import tempfile
from pathlib import Path
import yaml
import pytest
from scripts.setup import SetupWizard


class TestDockerComposeValidation:
    """Validate docker-compose.yml generation."""

    def test_docker_compose_yaml_syntax_valid(self, tmp_path):
        """Test docker-compose.yml has valid YAML syntax."""
        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {
            "platform": "docker",
            "llm_provider": "docker_model_runner",
            "docker_model": "ai/phi3-mini-4k-instruct",
        }

        wizard.create_docker_compose()

        compose_file = tmp_path / "docker-compose.yml"
        assert compose_file.exists()

        # Should parse without errors
        content = compose_file.read_text()
        parsed = yaml.safe_load(content)

        assert isinstance(parsed, dict)
        assert "services" in parsed

    def test_docker_compose_has_required_services(self, tmp_path):
        """Test docker-compose.yml has all required services."""
        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {
            "platform": "docker",
            "llm_provider": "docker_model_runner",
            "docker_model": "ai/llama3.2-3b-instruct",
        }

        wizard.create_docker_compose()

        compose_file = tmp_path / "docker-compose.yml"
        parsed = yaml.safe_load(compose_file.read_text())

        services = parsed["services"]

        # Required services
        assert "llm" in services
        assert "api" in services
        assert "db" in services
        assert "redis" in services

    def test_docker_compose_llm_service_structure(self, tmp_path):
        """Test LLM service has correct structure."""
        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {
            "platform": "docker",
            "llm_provider": "docker_model_runner",
            "docker_model": "ai/phi3-mini-4k-instruct",
        }

        wizard.create_docker_compose()

        compose_file = tmp_path / "docker-compose.yml"
        parsed = yaml.safe_load(compose_file.read_text())

        llm_service = parsed["services"]["llm"]

        # Required fields
        assert "image" in llm_service
        assert "ports" in llm_service
        assert "environment" in llm_service

        # Correct values
        assert llm_service["image"] == "ai/phi3-mini-4k-instruct"
        assert "8080:8080" in llm_service["ports"]

    def test_docker_compose_api_depends_on_llm(self, tmp_path):
        """Test API service depends on LLM service."""
        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {
            "platform": "docker",
            "llm_provider": "docker_model_runner",
            "docker_model": "ai/smollm2-360m-instruct",
        }

        wizard.create_docker_compose()

        compose_file = tmp_path / "docker-compose.yml"
        parsed = yaml.safe_load(compose_file.read_text())

        api_service = parsed["services"]["api"]

        # API should depend on LLM
        assert "depends_on" in api_service
        assert "llm" in api_service["depends_on"]
        assert "db" in api_service["depends_on"]
        assert "redis" in api_service["depends_on"]

    def test_docker_compose_api_environment_configured(self, tmp_path):
        """Test API service environment variables are configured."""
        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {
            "platform": "docker",
            "llm_provider": "docker_model_runner",
            "docker_model": "ai/gemma2-2b-instruct",
        }

        wizard.create_docker_compose()

        compose_file = tmp_path / "docker-compose.yml"
        parsed = yaml.safe_load(compose_file.read_text())

        api_service = parsed["services"]["api"]
        env_vars = api_service["environment"]

        # Check environment variables
        env_dict = {}
        for env in env_vars:
            if "=" in env:
                key, value = env.split("=", 1)
                env_dict[key] = value

        # Should have OpenAI-compatible endpoint
        assert "OPENAI_API_BASE" in env_dict
        assert env_dict["OPENAI_API_BASE"] == "http://llm:8080/v1"

        # Should not need API key for local model
        assert "OPENAI_API_KEY" in env_dict
        assert env_dict["OPENAI_API_KEY"] == "not-needed"

    def test_docker_compose_volumes_defined(self, tmp_path):
        """Test docker-compose.yml has volumes defined."""
        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {
            "platform": "docker",
            "llm_provider": "docker_model_runner",
            "docker_model": "ai/phi3-mini-4k-instruct",
        }

        wizard.create_docker_compose()

        compose_file = tmp_path / "docker-compose.yml"
        parsed = yaml.safe_load(compose_file.read_text())

        # Should have volumes section
        assert "volumes" in parsed
        volumes = parsed["volumes"]

        # Required volumes for data persistence
        assert "postgres_data" in volumes or "postgres_data" in str(volumes)
        assert "redis_data" in volumes or "redis_data" in str(volumes)

    def test_docker_compose_postgres_configuration(self, tmp_path):
        """Test PostgreSQL service is properly configured."""
        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {
            "platform": "docker",
            "llm_provider": "docker_model_runner",
            "docker_model": "ai/phi3-mini-4k-instruct",
        }

        wizard.create_docker_compose()

        compose_file = tmp_path / "docker-compose.yml"
        parsed = yaml.safe_load(compose_file.read_text())

        db_service = parsed["services"]["db"]

        # Check PostgreSQL configuration
        assert db_service["image"] == "postgres:15"
        assert "environment" in db_service
        assert "volumes" in db_service
        assert "ports" in db_service

    def test_docker_compose_different_models(self, tmp_path):
        """Test docker-compose.yml works with different models."""
        models = [
            "ai/smollm2-135m-instruct",
            "ai/smollm2-360m-instruct",
            "ai/phi3-mini-4k-instruct",
            "ai/llama3.2-1b-instruct",
            "ai/llama3.2-3b-instruct",
            "ai/gemma2-2b-instruct",
        ]

        for model in models:
            wizard = SetupWizard()
            wizard.root_dir = tmp_path
            wizard.config = {
                "platform": "docker",
                "llm_provider": "docker_model_runner",
                "docker_model": model,
            }

            wizard.create_docker_compose()

            compose_file = tmp_path / "docker-compose.yml"
            parsed = yaml.safe_load(compose_file.read_text())

            llm_service = parsed["services"]["llm"]
            assert llm_service["image"] == model, f"Failed for model {model}"

    def test_docker_compose_without_model_runner_no_llm_service(self, tmp_path):
        """Test docker-compose.yml without Model Runner has no LLM service."""
        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {
            "platform": "docker",
            "llm_provider": "openai",
        }

        wizard.create_docker_compose()

        compose_file = tmp_path / "docker-compose.yml"
        parsed = yaml.safe_load(compose_file.read_text())

        services = parsed["services"]

        # Should NOT have LLM service when using cloud provider
        assert "llm" not in services

        # Should still have other services
        assert "api" in services
        assert "db" in services
        assert "redis" in services


class TestDockerDesktopAvailability:
    """Test Docker Desktop availability detection."""

    def test_docker_not_available_in_test_environment(self):
        """Document that Docker is not available in test environment."""
        import subprocess

        result = subprocess.run(
            ["which", "docker"], capture_output=True, text=True
        )

        # Docker should not be available in this environment
        # (This test documents the limitation)
        assert result.returncode != 0 or result.stdout.strip() == ""

    def test_docker_compose_validation_doesnt_require_docker(self, tmp_path):
        """Test that we can validate docker-compose.yml without Docker installed."""
        # This test confirms our approach: validate YAML structure
        # without requiring Docker to be installed

        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {
            "platform": "docker",
            "llm_provider": "docker_model_runner",
            "docker_model": "ai/phi3-mini-4k-instruct",
        }

        # Should work without Docker installed
        wizard.create_docker_compose()

        compose_file = tmp_path / "docker-compose.yml"
        assert compose_file.exists()

        # Can parse and validate without Docker
        parsed = yaml.safe_load(compose_file.read_text())
        assert "services" in parsed
        assert "llm" in parsed["services"]
