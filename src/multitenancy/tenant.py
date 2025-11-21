"""
Multi-tenant support for managing multiple SEO clients.

Allows a single deployment to serve multiple clients with isolated data.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from contextvars import ContextVar

import structlog
from pydantic import BaseModel, Field, SecretStr

logger = structlog.get_logger()

# Context variable for current tenant
_current_tenant: ContextVar[str | None] = ContextVar("current_tenant", default=None)


class TenantConfig(BaseModel):
    """Configuration specific to a tenant."""

    # Google
    gsc_property_url: str | None = None
    gsc_credentials_path: str | None = None

    # Competitors
    competitors: list[str] = Field(default_factory=list)

    # Alerts
    teams_webhook_url: SecretStr | None = None
    alert_email: str | None = None

    # Optimizely
    optimizely_api_key: SecretStr | None = None
    optimizely_project_id: str | None = None

    # Custom settings
    custom: dict[str, Any] = Field(default_factory=dict)


class Tenant(BaseModel):
    """A tenant (client) in the system."""

    id: str
    name: str
    domain: str
    config: TenantConfig = Field(default_factory=TenantConfig)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = True
    plan: str = "standard"  # free, standard, premium
    metadata: dict[str, Any] = Field(default_factory=dict)


@dataclass
class TenantContext:
    """Context for tenant-scoped operations."""

    tenant: Tenant
    storage_prefix: str = ""

    def __post_init__(self):
        self.storage_prefix = f"tenant_{self.tenant.id}"


class TenantManager:
    """
    Manages tenants in the system.

    Supports multiple storage backends:
    - Local JSON file (development)
    - Azure Cosmos DB (production)
    """

    def __init__(self, storage_path: str = "data/tenants.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._tenants: dict[str, Tenant] = {}
        self._load_tenants()

    def _load_tenants(self):
        """Load tenants from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path) as f:
                    data = json.load(f)
                    for tenant_data in data.get("tenants", []):
                        tenant = Tenant(**tenant_data)
                        self._tenants[tenant.id] = tenant
                logger.info("Loaded tenants", count=len(self._tenants))
            except Exception as e:
                logger.error("Failed to load tenants", error=str(e))

    def _save_tenants(self):
        """Save tenants to storage."""
        try:
            data = {
                "tenants": [t.model_dump(mode="json") for t in self._tenants.values()],
                "updated_at": datetime.utcnow().isoformat(),
            }
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error("Failed to save tenants", error=str(e))

    def create_tenant(
        self,
        tenant_id: str,
        name: str,
        domain: str,
        config: TenantConfig | None = None,
        **kwargs,
    ) -> Tenant:
        """Create a new tenant."""
        if tenant_id in self._tenants:
            raise ValueError(f"Tenant {tenant_id} already exists")

        tenant = Tenant(
            id=tenant_id,
            name=name,
            domain=domain,
            config=config or TenantConfig(),
            **kwargs,
        )

        self._tenants[tenant_id] = tenant
        self._save_tenants()

        logger.info("Created tenant", tenant_id=tenant_id, name=name)
        return tenant

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        """Get a tenant by ID."""
        return self._tenants.get(tenant_id)

    def get_tenant_by_domain(self, domain: str) -> Tenant | None:
        """Get a tenant by domain."""
        for tenant in self._tenants.values():
            if tenant.domain == domain:
                return tenant
        return None

    def list_tenants(self, active_only: bool = True) -> list[Tenant]:
        """List all tenants."""
        tenants = list(self._tenants.values())
        if active_only:
            tenants = [t for t in tenants if t.active]
        return tenants

    def update_tenant(self, tenant_id: str, **updates) -> Tenant | None:
        """Update a tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None

        for key, value in updates.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)

        tenant.updated_at = datetime.utcnow()
        self._save_tenants()

        logger.info("Updated tenant", tenant_id=tenant_id)
        return tenant

    def update_tenant_config(
        self,
        tenant_id: str,
        config_updates: dict[str, Any],
    ) -> Tenant | None:
        """Update tenant configuration."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None

        for key, value in config_updates.items():
            if hasattr(tenant.config, key):
                setattr(tenant.config, key, value)

        tenant.updated_at = datetime.utcnow()
        self._save_tenants()

        return tenant

    def delete_tenant(self, tenant_id: str) -> bool:
        """Delete a tenant (soft delete)."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False

        tenant.active = False
        tenant.updated_at = datetime.utcnow()
        self._save_tenants()

        logger.info("Deleted tenant", tenant_id=tenant_id)
        return True

    def get_context(self, tenant_id: str) -> TenantContext | None:
        """Get a tenant context for operations."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return None
        return TenantContext(tenant=tenant)


def set_current_tenant(tenant_id: str | None):
    """Set the current tenant in context."""
    _current_tenant.set(tenant_id)


def get_current_tenant() -> str | None:
    """Get the current tenant from context."""
    return _current_tenant.get()


# Global tenant manager
_manager: TenantManager | None = None


def get_tenant_manager() -> TenantManager:
    """Get the global tenant manager."""
    global _manager
    if _manager is None:
        _manager = TenantManager()
    return _manager
