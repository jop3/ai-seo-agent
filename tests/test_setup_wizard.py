"""
Integration tests for setup wizard.
"""
import tempfile
from pathlib import Path
import yaml
import pytest
from scripts.setup import SetupWizard


class TestSetupWizard:
    """Test SetupWizard integration."""

    def test_wizard_initialization(self):
        """Test wizard initializes correctly."""
        wizard = SetupWizard()
        assert wizard.config == {}
        assert wizard.root_dir.exists()

    def test_env_file_generation_docker_model_runner(self, tmp_path):
        """Test .env file generation for Docker Model Runner."""
        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {
            "llm_provider": "docker_model_runner",
            "docker_model": "ai/phi3-mini-4k-instruct",
            "docker_model_endpoint": "http://llm:8080/v1",
            "database": "postgresql",
            "postgres_url": "postgresql://localhost:5432/test",
        }

        wizard.create_env_file()

        env_file = tmp_path / ".env"
        assert env_file.exists()

        content = env_file.read_text()
        assert "OPENAI_API_BASE=http://llm:8080/v1" in content
        assert "OPENAI_API_KEY=not-needed" in content
        assert "ai/phi3-mini-4k-instruct" in content
        assert "POSTGRES_URL=postgresql://localhost:5432/test" in content

    def test_env_file_generation_openai(self, tmp_path):
        """Test .env file generation for OpenAI."""
        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {
            "llm_provider": "openai",
            "openai_api_key": "sk-test-key",
            "database": "sqlite",
            "sqlite_path": "./test.db",
        }

        wizard.create_env_file()

        env_file = tmp_path / ".env"
        assert env_file.exists()

        content = env_file.read_text()
        assert "OPENAI_API_KEY=sk-test-key" in content
        assert "SQLITE_PATH=./test.db" in content

    def test_env_file_generation_azure_openai(self, tmp_path):
        """Test .env file generation for Azure OpenAI."""
        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {
            "llm_provider": "azure_openai",
            "azure_openai_endpoint": "https://test.openai.azure.com",
            "azure_openai_api_key": "test-key",
            "azure_openai_deployment": "gpt-4o",
            "database": "mongodb",
            "mongodb_url": "mongodb://localhost:27017/test",
        }

        wizard.create_env_file()

        env_file = tmp_path / ".env"
        assert env_file.exists()

        content = env_file.read_text()
        assert "AZURE_OPENAI_ENDPOINT=https://test.openai.azure.com" in content
        assert "AZURE_OPENAI_API_KEY=test-key" in content
        assert "AZURE_OPENAI_DEPLOYMENT=gpt-4o" in content
        assert "MONGODB_URL=mongodb://localhost:27017/test" in content

    def test_docker_compose_generation_with_model_runner(self, tmp_path):
        """Test docker-compose.yml generation with Docker Model Runner."""
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

        content = compose_file.read_text()
        parsed = yaml.safe_load(content)

        # Check services exist
        assert "services" in parsed
        assert "llm" in parsed["services"]
        assert "api" in parsed["services"]
        assert "db" in parsed["services"]
        assert "redis" in parsed["services"]

        # Check LLM service configuration
        llm_service = parsed["services"]["llm"]
        assert llm_service["image"] == "ai/phi3-mini-4k-instruct"
        assert "8080:8080" in llm_service["ports"]
        assert any(
            "MODEL_ID=ai/phi3-mini-4k-instruct" in env
            for env in llm_service["environment"]
        )

        # Check API service depends on LLM
        api_service = parsed["services"]["api"]
        assert "llm" in api_service["depends_on"]
        assert any("OPENAI_API_BASE=http://llm:8080/v1" in env for env in api_service["environment"])

    def test_docker_compose_generation_without_model_runner(self, tmp_path):
        """Test docker-compose.yml generation without Docker Model Runner."""
        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {
            "platform": "docker",
            "llm_provider": "openai",
        }

        wizard.create_docker_compose()

        compose_file = tmp_path / "docker-compose.yml"
        assert compose_file.exists()

        content = compose_file.read_text()
        parsed = yaml.safe_load(content)

        # Should not have LLM service
        assert "llm" not in parsed["services"]

        # Should have other services
        assert "api" in parsed["services"]
        assert "db" in parsed["services"]
        assert "redis" in parsed["services"]

        # API should use environment variable for API key
        api_service = parsed["services"]["api"]
        assert any("OPENAI_API_KEY=${OPENAI_API_KEY}" in env for env in api_service["environment"])

    def test_vercel_config_generation(self, tmp_path):
        """Test Vercel configuration generation."""
        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {"platform": "vercel"}

        wizard.create_vercel_config()

        vercel_file = tmp_path / "vercel.json"
        assert vercel_file.exists()

        content = vercel_file.read_text()
        parsed = yaml.safe_load(content)

        assert "version" in parsed
        assert "builds" in parsed
        assert "routes" in parsed

    def test_azure_config_generation(self, tmp_path):
        """Test Azure configuration generation."""
        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {"platform": "azure"}

        wizard.create_azure_config()

        azure_params = tmp_path / "azure" / "parameters.json"
        assert azure_params.exists()

        content = azure_params.read_text()
        parsed = yaml.safe_load(content)

        assert "parameters" in parsed
        assert "appName" in parsed["parameters"]
        assert "location" in parsed["parameters"]

    def test_postgres_schema_generation(self, tmp_path):
        """Test PostgreSQL schema generation."""
        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {"database": "postgresql"}

        wizard.create_postgres_schema()

        schema_file = tmp_path / "schema" / "postgres.sql"
        assert schema_file.exists()

        content = schema_file.read_text()
        assert "CREATE TABLE IF NOT EXISTS analyses" in content
        assert "CREATE TABLE IF NOT EXISTS agent_results" in content
        assert "CREATE INDEX" in content

    def test_complete_docker_model_runner_setup(self, tmp_path):
        """Test complete setup flow for Docker + Model Runner."""
        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {
            "platform": "docker",
            "llm_provider": "docker_model_runner",
            "docker_model": "ai/llama3.2-3b-instruct",
            "docker_model_endpoint": "http://llm:8080/v1",
            "database": "postgresql",
            "postgres_url": "postgresql://postgres:postgres@db:5432/seoagent",
            "redis_url": "redis://redis:6379/0",
        }

        # Generate all files
        wizard.create_env_file()
        wizard.create_docker_compose()

        # Check .env
        env_file = tmp_path / ".env"
        assert env_file.exists()
        env_content = env_file.read_text()
        assert "OPENAI_API_BASE=http://llm:8080/v1" in env_content
        assert "ai/llama3.2-3b-instruct" in env_content

        # Check docker-compose.yml
        compose_file = tmp_path / "docker-compose.yml"
        assert compose_file.exists()
        compose_content = compose_file.read_text()
        parsed = yaml.safe_load(compose_content)

        # Verify LLM service
        assert parsed["services"]["llm"]["image"] == "ai/llama3.2-3b-instruct"

        # Verify API connects to LLM
        assert "llm" in parsed["services"]["api"]["depends_on"]

    def test_complete_azure_openai_setup(self, tmp_path):
        """Test complete setup flow for Azure + Azure OpenAI."""
        wizard = SetupWizard()
        wizard.root_dir = tmp_path
        wizard.config = {
            "platform": "azure",
            "llm_provider": "azure_openai",
            "azure_openai_endpoint": "https://myorg.openai.azure.com",
            "azure_openai_api_key": "test-key-12345",
            "azure_openai_deployment": "gpt-4o",
            "database": "postgresql",
            "postgres_url": "Server=myserver.postgres.database.azure.com",
        }

        # Generate all files
        wizard.create_env_file()
        wizard.create_azure_config()

        # Check .env
        env_file = tmp_path / ".env"
        assert env_file.exists()
        env_content = env_file.read_text()
        assert "AZURE_OPENAI_ENDPOINT=https://myorg.openai.azure.com" in env_content
        assert "AZURE_OPENAI_API_KEY=test-key-12345" in env_content
        assert "AZURE_OPENAI_DEPLOYMENT=gpt-4o" in env_content

        # Check Azure params
        azure_params = tmp_path / "azure" / "parameters.json"
        assert azure_params.exists()
