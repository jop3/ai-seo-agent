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
from src.agents.eeat_analyzer import EEATAnalyzerAgent
from src.agents.multi_platform_seo import MultiPlatformSEOAgent
from src.agents.ai_content_analyzer import AIContentAnalyzerAgent
from src.agents.geo_analyzer import GEOAnalyzerAgent
from src.agents.ecommerce_seo import EcommerceSEOAgent
from src.agents.ai_visibility_control import AIVisibilityControlAgent
from src.agents.visual_search import VisualSearchAgent
from src.agents.product_feed_analyzer import ProductFeedAnalyzerAgent
from src.agents.conversational_commerce import ConversationalCommerceAgent

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
    # Future-proofing agents
    "EEATAnalyzerAgent",
    "MultiPlatformSEOAgent",
    "AIContentAnalyzerAgent",
    "GEOAnalyzerAgent",
    # E-commerce specialized agents
    "EcommerceSEOAgent",
    "AIVisibilityControlAgent",
    "VisualSearchAgent",
    "ProductFeedAnalyzerAgent",
    "ConversationalCommerceAgent",
]
