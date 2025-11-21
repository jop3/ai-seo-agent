"""AI Agents for SEO optimization."""

from src.agents.base import BaseAgent, AgentContext
from src.agents.seo_analyst import SEOAnalystAgent
from src.agents.agent_tester import AgentTesterAgent
from src.agents.monitoring import MonitoringAgent
from src.agents.optimizer import OptimizationRecommenderAgent
from src.agents.competitor_monitor import CompetitorMonitorAgent
from src.agents.content_generator import ContentGeneratorAgent
from src.agents.multi_engine_tracker import MultiEngineTrackerAgent
from src.agents.technical_seo import TechnicalSEOAgent
from src.agents.link_analysis import LinkAnalysisAgent
from src.agents.serp_features import SERPFeaturesAgent
from src.agents.content_decay import ContentDecayAgent
from src.agents.schema_agent import SchemaAgent
from src.agents.predictive_seo import PredictiveSEOAgent
from src.agents.local_seo import LocalSEOAgent

__all__ = [
    # Base
    "BaseAgent",
    "AgentContext",
    # Core agents
    "SEOAnalystAgent",
    "AgentTesterAgent",
    "MonitoringAgent",
    "OptimizationRecommenderAgent",
    # Extended agents
    "CompetitorMonitorAgent",
    "ContentGeneratorAgent",
    "MultiEngineTrackerAgent",
    "TechnicalSEOAgent",
    "LinkAnalysisAgent",
    "SERPFeaturesAgent",
    "ContentDecayAgent",
    "SchemaAgent",
    "PredictiveSEOAgent",
    "LocalSEOAgent",
]
