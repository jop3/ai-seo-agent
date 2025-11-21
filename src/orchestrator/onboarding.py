"""
Interactive onboarding system for workflow configuration.

Guides users through setup with smart questions and validation.
"""

import json
from pathlib import Path
from typing import Any

import structlog
from pydantic import ValidationError

from src.orchestrator.schemas import (
    WorkflowInput,
    WorkflowTargets,
    BusinessInfo,
    AuthorInfo,
    CompetitorConfig,
    WorkflowThresholds,
    WorkflowOptions,
)

logger = structlog.get_logger()


class OnboardingFlow:
    """
    Interactive onboarding flow for workflow configuration.

    Asks questions, validates input, and builds complete configuration.
    """

    def __init__(self):
        self.config: dict[str, Any] = {}
        self.site_type: str | None = None

    def start(self, interactive: bool = True) -> WorkflowInput:
        """
        Start the onboarding flow.

        Args:
            interactive: If True, prompts for input. If False, returns minimal config.

        Returns:
            Complete WorkflowInput configuration
        """
        if not interactive:
            return self._minimal_setup()

        print("\n" + "=" * 70)
        print("  AI SEO Agent - Workflow Configuration")
        print("=" * 70)
        print("\nLet's set up your SEO monitoring in a few quick steps.\n")

        # Step 1: Site type
        self.site_type = self._ask_site_type()

        # Step 2: Basic info
        targets = self._ask_basic_info()

        # Step 3: Competitors (optional but recommended)
        competitors = self._ask_competitors()
        targets.competitors = competitors

        # Step 4: Business info (based on site type)
        business_info = self._ask_business_info()

        # Step 5: Author info (for content sites)
        author_info = None
        if self.site_type in ["content", "blog", "news", "ecommerce"]:
            author_info = self._ask_author_info()

        # Step 6: Target queries (optional)
        queries = self._ask_target_queries()
        if queries:
            targets.target_queries = queries

        # Step 7: Thresholds and options
        thresholds = self._ask_thresholds()
        options = self._ask_options()

        # Build final config
        workflow_input = WorkflowInput(
            targets=targets,
            business_info=business_info,
            default_author=author_info,
            thresholds=thresholds,
            options=options,
        )

        # Summary
        self._show_summary(workflow_input)

        return workflow_input

    def _ask_site_type(self) -> str:
        """Ask about site type to customize questions."""
        print("What type of site are you setting up?\n")
        print("1. E-commerce / Online Store")
        print("2. Local Business (restaurant, shop, service)")
        print("3. Content / Blog / News Site")
        print("4. SaaS / Software Product")
        print("5. Corporate / Brand Site")
        print("6. Other")

        choice = input("\nEnter your choice (1-6) [1]: ").strip() or "1"

        type_map = {
            "1": "ecommerce",
            "2": "local",
            "3": "content",
            "4": "saas",
            "5": "corporate",
            "6": "other",
        }

        site_type = type_map.get(choice, "ecommerce")
        print(f"\n✓ Site type: {site_type.capitalize()}\n")
        return site_type

    def _ask_basic_info(self) -> WorkflowTargets:
        """Ask for basic domain and URL info."""
        print("─" * 70)
        print("BASIC INFORMATION")
        print("─" * 70)

        domain = input("\nYour domain (e.g., example.com): ").strip()
        while not domain:
            print("⚠ Domain is required")
            domain = input("Your domain (e.g., example.com): ").strip()

        # Infer property URL
        default_url = f"https://{domain}"
        property_url = input(f"Full site URL [{default_url}]: ").strip() or default_url

        print(f"\n✓ Domain: {domain}")
        print(f"✓ URL: {property_url}\n")

        return WorkflowTargets(
            primary_domain=domain,
            property_url=property_url,
        )

    def _ask_competitors(self) -> list[CompetitorConfig]:
        """Ask for competitor domains."""
        print("─" * 70)
        print("COMPETITORS (Recommended - enables competitive analysis)")
        print("─" * 70)

        add_competitors = input("\nDo you want to track competitors? (y/n) [y]: ").strip().lower()
        if add_competitors == "n":
            print("\n⊘ Skipping competitor tracking\n")
            return []

        print("\nEnter competitor domains (press Enter when done)")
        print("You can add 3-5 main competitors for best results.\n")

        competitors = []
        count = 1

        while count <= 10:  # Max 10 competitors
            domain = input(f"Competitor #{count} domain (or Enter to finish): ").strip()
            if not domain:
                break

            # Ask priority for first 3
            if count <= 3:
                priority = input(f"  Priority for {domain} (high/medium/low) [high]: ").strip().lower() or "high"
                if priority not in ["high", "medium", "low"]:
                    priority = "medium"
            else:
                priority = "medium"

            competitors.append(CompetitorConfig(
                domain=domain,
                priority=priority,
            ))

            count += 1

        if competitors:
            print(f"\n✓ Added {len(competitors)} competitors\n")
        else:
            print("\n⊘ No competitors added\n")

        return competitors

    def _ask_business_info(self) -> BusinessInfo | None:
        """Ask for business information."""
        print("─" * 70)
        print("BUSINESS INFORMATION (Recommended - improves schema & local SEO)")
        print("─" * 70)

        add_business = input("\nAdd business information? (y/n) [y]: ").strip().lower()
        if add_business == "n":
            print("\n⊘ Skipping business info\n")
            return None

        name = input("\nBusiness name: ").strip()
        if not name:
            return None

        url = input("Website URL (from above): ").strip()
        description = input("Business description (1 sentence): ").strip()

        # Contact info
        phone = input("Phone number (optional): ").strip() or None
        email = input("Email (optional): ").strip() or None

        # Location (if local business)
        address = None
        city = None
        state = None
        postal_code = None
        country = None

        if self.site_type == "local":
            print("\n📍 Local Business Location")
            add_location = input("Add business address? (y/n) [y]: ").strip().lower()
            if add_location != "n":
                address = input("Street address: ").strip() or None
                city = input("City: ").strip() or None
                state = input("State/Province: ").strip() or None
                postal_code = input("Postal/Zip code: ").strip() or None
                country = input("Country code (e.g., US, UK) [US]: ").strip() or "US"

        # Social profiles
        print("\n🔗 Social Profiles (Optional - improves E-E-A-T)")
        add_social = input("Add social profiles? (y/n) [n]: ").strip().lower()
        facebook = None
        twitter = None
        linkedin = None
        instagram = None

        if add_social == "y":
            facebook = input("Facebook URL (optional): ").strip() or None
            twitter = input("Twitter URL (optional): ").strip() or None
            linkedin = input("LinkedIn URL (optional): ").strip() or None
            instagram = input("Instagram URL (optional): ").strip() or None

        # Logo
        logo_url = input("\nLogo URL (optional): ").strip() or None

        print("\n✓ Business info configured\n")

        return BusinessInfo(
            name=name,
            url=url,
            description=description or None,
            phone=phone,
            email=email,
            street_address=address,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            facebook_url=facebook,
            twitter_url=twitter,
            linkedin_url=linkedin,
            instagram_url=instagram,
            logo_url=logo_url,
        )

    def _ask_author_info(self) -> AuthorInfo | None:
        """Ask for default author information."""
        print("─" * 70)
        print("AUTHOR INFORMATION (Recommended for content sites)")
        print("─" * 70)

        add_author = input("\nAdd default author for E-E-A-T analysis? (y/n) [y]: ").strip().lower()
        if add_author == "n":
            print("\n⊘ Skipping author info\n")
            return None

        name = input("\nAuthor name: ").strip()
        if not name:
            return None

        bio = input("Author bio (optional): ").strip() or None
        author_url = input("Author profile URL (optional): ").strip() or None

        # Credentials
        print("\nAuthor credentials (press Enter when done)")
        credentials = []
        count = 1
        while count <= 5:
            cred = input(f"Credential #{count} (optional): ").strip()
            if not cred:
                break
            credentials.append(cred)
            count += 1

        print("\n✓ Author info configured\n")

        return AuthorInfo(
            name=name,
            bio=bio,
            url=author_url,
            credentials=credentials if credentials else [],
        )

    def _ask_target_queries(self) -> list[str]:
        """Ask for target queries."""
        print("─" * 70)
        print("TARGET QUERIES (Optional - uses Google Search Console data if empty)")
        print("─" * 70)

        add_queries = input("\nAdd specific queries to track? (y/n) [n]: ").strip().lower()
        if add_queries != "y":
            print("\n⊘ Will use top queries from Google Search Console\n")
            return []

        print("\nEnter target queries/keywords (press Enter when done)\n")
        queries = []
        count = 1

        while count <= 20:
            query = input(f"Query #{count}: ").strip()
            if not query:
                break
            queries.append(query)
            count += 1

        if queries:
            print(f"\n✓ Added {len(queries)} target queries\n")

        return queries

    def _ask_thresholds(self) -> WorkflowThresholds:
        """Ask for alert thresholds."""
        print("─" * 70)
        print("ALERT THRESHOLDS (Optional - sensible defaults provided)")
        print("─" * 70)

        use_defaults = input("\nUse default thresholds? (y/n) [y]: ").strip().lower()
        if use_defaults != "n":
            print("\n✓ Using default thresholds\n")
            return WorkflowThresholds()

        print("\nCustomize thresholds:\n")

        traffic_drop = input("Traffic drop % to alert on [30]: ").strip()
        traffic_drop = float(traffic_drop) if traffic_drop else 30.0

        decay_days = input("Days of declining traffic for content decay [90]: ").strip()
        decay_days = int(decay_days) if decay_days else 90

        min_eeat = input("Minimum E-E-A-T score (0-100) [60]: ").strip()
        min_eeat = float(min_eeat) if min_eeat else 60.0

        print("\n✓ Thresholds configured\n")

        return WorkflowThresholds(
            traffic_drop_threshold_pct=traffic_drop,
            content_decay_days=decay_days,
            min_eeat_score=min_eeat,
        )

    def _ask_options(self) -> WorkflowOptions:
        """Ask for workflow options."""
        print("─" * 70)
        print("ANALYSIS OPTIONS")
        print("─" * 70)

        print("\nAnalysis depth:")
        print("1. Quick (5-10 min, daily checks)")
        print("2. Standard (15-20 min, weekly reviews)")
        print("3. Deep (30+ min, monthly audits)")

        depth_choice = input("\nChoose depth (1-3) [2]: ").strip() or "2"
        depth_map = {"1": "quick", "2": "standard", "3": "deep"}
        depth = depth_map.get(depth_choice, "standard")

        days_back = input("\nDays of history to analyze [30]: ").strip()
        days_back = int(days_back) if days_back else 30

        print(f"\n✓ Analysis depth: {depth}")
        print(f"✓ Lookback period: {days_back} days\n")

        return WorkflowOptions(
            analysis_depth=depth,
            days_back=days_back,
        )

    def _minimal_setup(self) -> WorkflowInput:
        """Create minimal configuration without prompts."""
        return WorkflowInput(
            targets=WorkflowTargets(
                primary_domain="example.com",
                property_url="https://example.com",
            )
        )

    def _show_summary(self, config: WorkflowInput):
        """Show configuration summary."""
        print("\n" + "=" * 70)
        print("  CONFIGURATION SUMMARY")
        print("=" * 70)

        print(f"\n📍 Domain: {config.targets.primary_domain}")
        print(f"🔗 URL: {config.targets.property_url}")

        if config.targets.competitors:
            print(f"🎯 Competitors: {len(config.targets.competitors)}")
            for comp in config.targets.competitors[:3]:
                print(f"   - {comp.domain} ({comp.priority} priority)")

        if config.business_info:
            print(f"🏢 Business: {config.business_info.name}")
            if config.business_info.city:
                print(f"📍 Location: {config.business_info.city}, {config.business_info.state}")

        if config.default_author:
            print(f"✍️  Author: {config.default_author.name}")

        if config.targets.target_queries:
            print(f"🔍 Target Queries: {len(config.targets.target_queries)}")

        print(f"\n⚡ Analysis Depth: {config.options.analysis_depth}")
        print(f"📅 Lookback: {config.options.days_back} days")

        print("\n" + "=" * 70)
        print("✅ Configuration complete!")
        print("=" * 70 + "\n")


class ConfigManager:
    """Manages saving and loading workflow configurations."""

    def __init__(self, config_dir: str = ".seo-agent"):
        self.config_dir = Path.home() / config_dir
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "workflow-config.json"

    def save(self, config: WorkflowInput, name: str = "default") -> Path:
        """Save configuration to file."""
        configs = self.load_all()
        configs[name] = config.model_dump()

        with open(self.config_file, "w") as f:
            json.dump(configs, f, indent=2)

        logger.info("Configuration saved", name=name, path=str(self.config_file))
        return self.config_file

    def load(self, name: str = "default") -> WorkflowInput | None:
        """Load configuration from file."""
        configs = self.load_all()
        config_data = configs.get(name)

        if not config_data:
            return None

        try:
            return WorkflowInput(**config_data)
        except ValidationError as e:
            logger.error("Invalid configuration", name=name, error=str(e))
            return None

    def load_all(self) -> dict[str, Any]:
        """Load all saved configurations."""
        if not self.config_file.exists():
            return {}

        try:
            with open(self.config_file) as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load configurations", error=str(e))
            return {}

    def list_configs(self) -> list[str]:
        """List all saved configuration names."""
        return list(self.load_all().keys())

    def delete(self, name: str) -> bool:
        """Delete a saved configuration."""
        configs = self.load_all()
        if name in configs:
            del configs[name]
            with open(self.config_file, "w") as f:
                json.dump(configs, f, indent=2)
            return True
        return False


def quick_setup(
    domain: str,
    competitors: list[str] | None = None,
    business_name: str | None = None,
) -> WorkflowInput:
    """
    Quick setup helper for programmatic configuration.

    Args:
        domain: Primary domain
        competitors: List of competitor domains
        business_name: Business name

    Returns:
        WorkflowInput ready to use
    """
    from src.orchestrator.schemas import create_full_config

    return create_full_config(
        domain=domain,
        property_url=f"https://{domain}",
        competitors=competitors or [],
        business_name=business_name or domain.split(".")[0].title(),
    )
