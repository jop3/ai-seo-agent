"""Data models for the AI SEO Agent."""

from src.models.seo import (
    AIOverviewResult,
    PageAnalysis,
    Query,
    QueryClassification,
    SERPResult,
    TrafficData,
)
from src.models.agents import AgentTask, AgentResult, Recommendation, Alert
from src.models.content import Page, SchemaMarkup, OptimizationSuggestion

__all__ = [
    "AIOverviewResult",
    "PageAnalysis",
    "Query",
    "QueryClassification",
    "SERPResult",
    "TrafficData",
    "AgentTask",
    "AgentResult",
    "Recommendation",
    "Alert",
    "Page",
    "SchemaMarkup",
    "OptimizationSuggestion",
]
