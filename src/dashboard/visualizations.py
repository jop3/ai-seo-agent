"""
Dashboard visualization configurations.

Defines chart types, colors, and layouts for frontend rendering.
Compatible with popular charting libraries (Chart.js, Recharts, D3, etc.)
"""

from typing import Any
from enum import Enum


class ChartType(str, Enum):
    """Chart types for visualizations."""
    LINE = "line"
    BAR = "bar"
    DOUGHNUT = "doughnut"
    RADAR = "radar"
    GAUGE = "gauge"
    AREA = "area"


class ColorScheme:
    """Color scheme for dashboard visualizations."""

    # Health status colors
    CRITICAL = "#EF4444"  # Red
    WARNING = "#F59E0B"   # Yellow/Orange
    GOOD = "#10B981"      # Light Green
    EXCELLENT = "#059669"  # Dark Green

    # Category colors
    TECHNICAL = "#3B82F6"      # Blue
    CONTENT = "#8B5CF6"        # Purple
    ECOMMERCE = "#EC4899"      # Pink
    AI_READINESS = "#06B6D4"   # Cyan
    LOCAL = "#14B8A6"          # Teal
    COMPETITIVE = "#F97316"    # Orange
    AUTHORITY = "#6366F1"      # Indigo

    # Trend colors
    TREND_UP = "#10B981"    # Green
    TREND_DOWN = "#EF4444"  # Red
    TREND_STABLE = "#6B7280"  # Gray

    # Background colors
    BG_PRIMARY = "#FFFFFF"
    BG_SECONDARY = "#F9FAFB"
    BG_DARK = "#111827"

    # Text colors
    TEXT_PRIMARY = "#111827"
    TEXT_SECONDARY = "#6B7280"
    TEXT_LIGHT = "#9CA3AF"


def get_overall_score_gauge_config(score: float, status: str) -> dict[str, Any]:
    """
    Configuration for overall SEO health score gauge.

    Displays large circular gauge showing 0-100 score.
    """
    return {
        "type": ChartType.GAUGE.value,
        "data": {
            "value": score,
            "max": 100,
            "min": 0,
        },
        "options": {
            "color": _get_status_color(status),
            "segments": [
                {"min": 0, "max": 40, "color": ColorScheme.CRITICAL},
                {"min": 41, "max": 60, "color": ColorScheme.WARNING},
                {"min": 61, "max": 80, "color": ColorScheme.GOOD},
                {"min": 81, "max": 100, "color": ColorScheme.EXCELLENT},
            ],
            "centerText": f"{score:.0f}",
            "centerSubtext": status.upper(),
            "showNeedle": True,
        },
        "layout": {
            "width": "100%",
            "height": 300,
            "padding": 20,
        },
    }


def get_category_scores_chart_config(categories: dict[str, Any]) -> dict[str, Any]:
    """
    Configuration for category scores bar chart.

    Horizontal bar chart showing all category scores with color coding.
    """
    labels = [cat["category"] for cat in categories.values()]
    scores = [cat["score"] for cat in categories.values()]
    colors = [_get_status_color(cat["status"]) for cat in categories.values()]

    return {
        "type": ChartType.BAR.value,
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Score",
                    "data": scores,
                    "backgroundColor": colors,
                    "borderColor": colors,
                    "borderWidth": 1,
                }
            ],
        },
        "options": {
            "indexAxis": "y",  # Horizontal bars
            "responsive": True,
            "plugins": {
                "legend": {"display": False},
                "title": {
                    "display": True,
                    "text": "Category Scores",
                    "font": {"size": 18, "weight": "bold"},
                },
            },
            "scales": {
                "x": {
                    "min": 0,
                    "max": 100,
                    "ticks": {"stepSize": 20},
                    "grid": {"color": "#E5E7EB"},
                },
                "y": {
                    "grid": {"display": False},
                },
            },
        },
        "layout": {
            "width": "100%",
            "height": 400,
        },
    }


def get_trend_chart_config(trend_data: dict[str, Any]) -> dict[str, Any]:
    """
    Configuration for overall score trend line chart.

    Shows score progression over time with area fill.
    """
    return {
        "type": ChartType.AREA.value,
        "data": {
            "labels": trend_data["dates"],
            "datasets": [
                {
                    "label": "Overall Score",
                    "data": trend_data["overall_scores"],
                    "borderColor": ColorScheme.TECHNICAL,
                    "backgroundColor": f"{ColorScheme.TECHNICAL}33",  # 20% opacity
                    "fill": True,
                    "tension": 0.4,  # Smooth curves
                    "pointRadius": 4,
                    "pointHoverRadius": 6,
                }
            ],
        },
        "options": {
            "responsive": True,
            "plugins": {
                "legend": {"display": False},
                "title": {
                    "display": True,
                    "text": "SEO Health Trend (30 Days)",
                    "font": {"size": 18, "weight": "bold"},
                },
                "tooltip": {
                    "mode": "index",
                    "intersect": False,
                },
            },
            "scales": {
                "x": {
                    "grid": {"display": False},
                },
                "y": {
                    "min": 0,
                    "max": 100,
                    "ticks": {"stepSize": 20},
                    "grid": {"color": "#E5E7EB"},
                },
            },
        },
        "layout": {
            "width": "100%",
            "height": 300,
        },
    }


def get_platform_readiness_radar_config(platforms: dict[str, Any]) -> dict[str, Any]:
    """
    Configuration for platform readiness radar chart.

    Shows readiness scores for all platforms in spider/radar format.
    """
    labels = [plat["platform"] for plat in platforms.values()]
    scores = [plat["score"] for plat in platforms.values()]

    return {
        "type": ChartType.RADAR.value,
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Readiness Score",
                    "data": scores,
                    "borderColor": ColorScheme.AI_READINESS,
                    "backgroundColor": f"{ColorScheme.AI_READINESS}33",
                    "pointBackgroundColor": ColorScheme.AI_READINESS,
                    "pointBorderColor": "#fff",
                    "pointHoverBackgroundColor": "#fff",
                    "pointHoverBorderColor": ColorScheme.AI_READINESS,
                }
            ],
        },
        "options": {
            "responsive": True,
            "plugins": {
                "legend": {"display": False},
                "title": {
                    "display": True,
                    "text": "Platform Readiness",
                    "font": {"size": 18, "weight": "bold"},
                },
            },
            "scales": {
                "r": {
                    "min": 0,
                    "max": 100,
                    "ticks": {"stepSize": 20},
                    "grid": {"color": "#E5E7EB"},
                },
            },
        },
        "layout": {
            "width": "100%",
            "height": 400,
        },
    }


def get_issues_breakdown_doughnut_config(metrics: dict[str, Any]) -> dict[str, Any]:
    """
    Configuration for issues breakdown doughnut chart.

    Shows distribution of critical vs. warning vs. info issues.
    """
    return {
        "type": ChartType.DOUGHNUT.value,
        "data": {
            "labels": ["Critical", "Warnings", "Info"],
            "datasets": [
                {
                    "data": [
                        metrics.get("critical_issues", 0),
                        metrics.get("warning_issues", 0),
                        metrics.get("info_issues", 0),
                    ],
                    "backgroundColor": [
                        ColorScheme.CRITICAL,
                        ColorScheme.WARNING,
                        ColorScheme.GOOD,
                    ],
                    "borderWidth": 2,
                    "borderColor": "#FFFFFF",
                }
            ],
        },
        "options": {
            "responsive": True,
            "plugins": {
                "legend": {
                    "position": "bottom",
                    "labels": {"padding": 15, "font": {"size": 12}},
                },
                "title": {
                    "display": True,
                    "text": "Issues by Severity",
                    "font": {"size": 16, "weight": "bold"},
                },
            },
        },
        "layout": {
            "width": "100%",
            "height": 300,
        },
    }


def get_category_trends_multi_line_config(trend_data: dict[str, Any]) -> dict[str, Any]:
    """
    Configuration for category trends multi-line chart.

    Shows all category scores over time on one chart.
    """
    category_colors = {
        "technical": ColorScheme.TECHNICAL,
        "content": ColorScheme.CONTENT,
        "ecommerce": ColorScheme.ECOMMERCE,
        "ai_readiness": ColorScheme.AI_READINESS,
        "local": ColorScheme.LOCAL,
        "competitive": ColorScheme.COMPETITIVE,
        "authority": ColorScheme.AUTHORITY,
    }

    datasets = []
    for category_id, scores in trend_data.get("category_trends", {}).items():
        datasets.append({
            "label": category_id.replace("_", " ").title(),
            "data": scores,
            "borderColor": category_colors.get(category_id, ColorScheme.TECHNICAL),
            "backgroundColor": "transparent",
            "tension": 0.4,
            "pointRadius": 2,
            "pointHoverRadius": 4,
        })

    return {
        "type": ChartType.LINE.value,
        "data": {
            "labels": trend_data["dates"],
            "datasets": datasets,
        },
        "options": {
            "responsive": True,
            "plugins": {
                "legend": {
                    "position": "bottom",
                    "labels": {"padding": 10, "font": {"size": 11}},
                },
                "title": {
                    "display": True,
                    "text": "Category Score Trends",
                    "font": {"size": 18, "weight": "bold"},
                },
            },
            "scales": {
                "x": {"grid": {"display": False}},
                "y": {
                    "min": 0,
                    "max": 100,
                    "ticks": {"stepSize": 20},
                    "grid": {"color": "#E5E7EB"},
                },
            },
        },
        "layout": {
            "width": "100%",
            "height": 350,
        },
    }


def get_dashboard_layout_config() -> dict[str, Any]:
    """
    Complete dashboard layout configuration.

    Defines grid layout and component placement.
    """
    return {
        "layout": "grid",
        "grid": {
            "columns": 12,
            "gap": 20,
            "padding": 20,
        },
        "sections": [
            {
                "id": "header",
                "title": "SEO Health Dashboard",
                "span": 12,
                "components": [
                    {
                        "type": "quick_stats",
                        "span": 12,
                    }
                ],
            },
            {
                "id": "overview",
                "title": "Overview",
                "span": 12,
                "components": [
                    {
                        "type": "gauge",
                        "chart": "overall_score_gauge",
                        "span": 4,
                    },
                    {
                        "type": "chart",
                        "chart": "category_scores_bar",
                        "span": 8,
                    },
                ],
            },
            {
                "id": "trends",
                "title": "Trends & Analysis",
                "span": 12,
                "components": [
                    {
                        "type": "chart",
                        "chart": "trend_line",
                        "span": 8,
                    },
                    {
                        "type": "chart",
                        "chart": "issues_doughnut",
                        "span": 4,
                    },
                ],
            },
            {
                "id": "platforms",
                "title": "Platform Readiness",
                "span": 12,
                "components": [
                    {
                        "type": "chart",
                        "chart": "platform_radar",
                        "span": 6,
                    },
                    {
                        "type": "platform_list",
                        "span": 6,
                    },
                ],
            },
            {
                "id": "details",
                "title": "Detailed Analysis",
                "span": 12,
                "components": [
                    {
                        "type": "chart",
                        "chart": "category_trends_multi",
                        "span": 12,
                    },
                ],
            },
            {
                "id": "actions",
                "title": "Actions & Recommendations",
                "span": 12,
                "components": [
                    {
                        "type": "alerts_list",
                        "span": 6,
                    },
                    {
                        "type": "recommendations_list",
                        "span": 6,
                    },
                ],
            },
        ],
    }


def _get_status_color(status: str) -> str:
    """Get color for health status."""
    status_lower = status.lower()
    if status_lower == "critical":
        return ColorScheme.CRITICAL
    elif status_lower == "warning":
        return ColorScheme.WARNING
    elif status_lower == "good":
        return ColorScheme.GOOD
    elif status_lower == "excellent":
        return ColorScheme.EXCELLENT
    else:
        return ColorScheme.TEXT_SECONDARY
