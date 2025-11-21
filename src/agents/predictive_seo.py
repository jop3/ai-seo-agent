"""
Predictive SEO Agent - Forecasts trends, algorithm changes, and seasonal patterns.
"""

from datetime import datetime, timedelta
from typing import Any
import statistics

import structlog

from src.agents.base import BaseAgent, AgentContext
from src.core.errors import AgentError, ErrorCode
from src.models.agents import (
    AgentTask, AgentResult, AgentType, Recommendation, Alert, Priority, Severity
)

logger = structlog.get_logger()


class PredictiveSEOAgent(BaseAgent):
    """
    Predicts SEO trends and provides proactive recommendations.

    Capabilities:
    - Forecast traffic trends based on historical data
    - Detect seasonal patterns in search behavior
    - Predict algorithm update impacts
    - Identify emerging keyword opportunities
    - Provide early warning for ranking drops
    """

    agent_type = AgentType.PREDICTIVE_SEO

    def __init__(self, context: AgentContext):
        self.context = context
        self.logger = logger.bind(agent="predictive-seo")

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute predictive SEO task."""
        task_handlers = {
            "forecast_traffic": self._forecast_traffic,
            "detect_seasonality": self._detect_seasonality,
            "predict_ranking_changes": self._predict_ranking_changes,
            "find_emerging_keywords": self._find_emerging_keywords,
            "algorithm_impact_analysis": self._algorithm_impact_analysis,
            "trend_analysis": self._trend_analysis,
        }

        handler = task_handlers.get(task.task_type)
        if not handler:
            raise AgentError(
                f"Unknown task type: {task.task_type}",
                agent_type="predictive-seo",
                task_type=task.task_type,
                code=ErrorCode.VALIDATION_ERROR,
            )

        result = await handler(task.parameters)

        return AgentResult(
            task_id=task.id,
            agent_type=self.agent_type,
            success=True,
            data=result["data"],
            recommendations=result.get("recommendations", []),
            alerts=result.get("alerts", []),
        )

    async def _forecast_traffic(self, params: dict[str, Any]) -> dict[str, Any]:
        """Forecast future traffic based on historical trends."""
        days_history = params.get("days_history", 90)
        forecast_days = params.get("forecast_days", 30)

        if not self.context.gsc_client:
            return {"data": {"error": "GSC client not configured"}, "recommendations": []}

        recommendations = []
        alerts = []

        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_history)

            # Get historical data
            data = await self.context.gsc_client.get_performance(
                property_url=self.context.property_url,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                dimensions=["date"],
            )

            rows = data.get("rows", [])
            if len(rows) < 14:
                return {
                    "data": {"error": "Insufficient historical data for forecasting"},
                    "recommendations": [],
                }

            # Extract daily clicks
            daily_clicks = []
            for row in sorted(rows, key=lambda x: x.get("date", "")):
                daily_clicks.append({
                    "date": row.get("date"),
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                })

            # Calculate trend using linear regression approximation
            clicks_values = [d["clicks"] for d in daily_clicks]
            trend = self._calculate_trend(clicks_values)

            # Calculate moving averages
            ma_7 = self._moving_average(clicks_values, 7)
            ma_30 = self._moving_average(clicks_values, 30)

            # Generate forecast
            forecast = self._generate_forecast(clicks_values, forecast_days, trend)

            # Detect anomalies
            anomalies = self._detect_anomalies(clicks_values)

            # Calculate confidence interval
            std_dev = statistics.stdev(clicks_values) if len(clicks_values) > 1 else 0

            # Generate insights
            current_avg = statistics.mean(clicks_values[-7:]) if len(clicks_values) >= 7 else clicks_values[-1]
            forecast_avg = statistics.mean([f["predicted_clicks"] for f in forecast])
            change_pct = ((forecast_avg - current_avg) / current_avg * 100) if current_avg > 0 else 0

            if change_pct < -10:
                alerts.append(Alert(
                    title="Traffic decline predicted",
                    message=f"Forecast shows {abs(change_pct):.1f}% traffic decline over next {forecast_days} days",
                    severity=Severity.WARNING,
                    source="predictive-seo",
                ))
                recommendations.append(Recommendation(
                    title="Proactive content refresh recommended",
                    description="Predicted traffic decline - consider refreshing top content and increasing publishing",
                    priority=Priority.HIGH,
                    category="predictive_seo",
                ))
            elif change_pct > 10:
                recommendations.append(Recommendation(
                    title="Capitalize on predicted growth",
                    description=f"Forecast shows {change_pct:.1f}% growth - increase content investment",
                    priority=Priority.MEDIUM,
                    category="predictive_seo",
                ))

            return {
                "data": {
                    "historical_days": len(daily_clicks),
                    "trend_direction": "growing" if trend > 0 else "declining" if trend < 0 else "stable",
                    "trend_strength": abs(trend),
                    "current_daily_avg": round(current_avg, 1),
                    "forecast_daily_avg": round(forecast_avg, 1),
                    "predicted_change_pct": round(change_pct, 1),
                    "confidence_range": round(std_dev * 1.96, 1),  # 95% CI
                    "forecast": forecast[:14],  # First 2 weeks
                    "anomalies_detected": len(anomalies),
                    "moving_averages": {
                        "ma_7_latest": round(ma_7[-1], 1) if ma_7 else None,
                        "ma_30_latest": round(ma_30[-1], 1) if ma_30 else None,
                    },
                },
                "recommendations": recommendations,
                "alerts": alerts,
            }

        except Exception as e:
            self.logger.error("Traffic forecast failed", error=str(e))
            return {"data": {"error": str(e)}, "recommendations": []}

    def _calculate_trend(self, values: list[float]) -> float:
        """Calculate trend using simple linear regression slope."""
        n = len(values)
        if n < 2:
            return 0

        x_mean = (n - 1) / 2
        y_mean = statistics.mean(values)

        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        return numerator / denominator if denominator != 0 else 0

    def _moving_average(self, values: list[float], window: int) -> list[float]:
        """Calculate moving average."""
        if len(values) < window:
            return []
        return [
            statistics.mean(values[i:i + window])
            for i in range(len(values) - window + 1)
        ]

    def _generate_forecast(
        self,
        historical: list[float],
        days: int,
        trend: float,
    ) -> list[dict[str, Any]]:
        """Generate traffic forecast."""
        forecast = []
        last_value = historical[-1] if historical else 0
        base_date = datetime.now().date()

        for i in range(1, days + 1):
            predicted = max(0, last_value + (trend * i))
            forecast.append({
                "date": (base_date + timedelta(days=i)).isoformat(),
                "predicted_clicks": round(predicted, 1),
                "day": i,
            })

        return forecast

    def _detect_anomalies(self, values: list[float]) -> list[int]:
        """Detect anomalies using IQR method."""
        if len(values) < 10:
            return []

        sorted_values = sorted(values)
        q1 = sorted_values[len(sorted_values) // 4]
        q3 = sorted_values[3 * len(sorted_values) // 4]
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        return [i for i, v in enumerate(values) if v < lower_bound or v > upper_bound]

    async def _detect_seasonality(self, params: dict[str, Any]) -> dict[str, Any]:
        """Detect seasonal patterns in traffic."""
        if not self.context.gsc_client:
            return {"data": {"error": "GSC client not configured"}, "recommendations": []}

        try:
            # Get 12 months of data for seasonality
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=365)

            data = await self.context.gsc_client.get_performance(
                property_url=self.context.property_url,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                dimensions=["date"],
            )

            rows = data.get("rows", [])
            if len(rows) < 60:
                return {
                    "data": {"error": "Need at least 60 days of data for seasonality detection"},
                    "recommendations": [],
                }

            # Group by month
            monthly_data = {}
            for row in rows:
                date_str = row.get("date", "")
                if date_str:
                    month = date_str[:7]  # YYYY-MM
                    if month not in monthly_data:
                        monthly_data[month] = {"clicks": 0, "impressions": 0, "days": 0}
                    monthly_data[month]["clicks"] += row.get("clicks", 0)
                    monthly_data[month]["impressions"] += row.get("impressions", 0)
                    monthly_data[month]["days"] += 1

            # Calculate monthly averages
            monthly_avgs = {
                month: data["clicks"] / data["days"] if data["days"] > 0 else 0
                for month, data in monthly_data.items()
            }

            # Group by day of week
            dow_data = {i: [] for i in range(7)}
            for row in rows:
                date_str = row.get("date", "")
                if date_str:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                    dow_data[date.weekday()].append(row.get("clicks", 0))

            dow_avgs = {
                ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][dow]:
                statistics.mean(clicks) if clicks else 0
                for dow, clicks in dow_data.items()
            }

            # Find best/worst periods
            sorted_months = sorted(monthly_avgs.items(), key=lambda x: x[1], reverse=True)
            best_months = sorted_months[:3]
            worst_months = sorted_months[-3:]

            sorted_days = sorted(dow_avgs.items(), key=lambda x: x[1], reverse=True)

            recommendations = []

            # Seasonal recommendation
            current_month = datetime.now().strftime("%Y-%m")
            upcoming_months = [
                (datetime.now() + timedelta(days=30 * i)).strftime("%Y-%m")
                for i in range(1, 4)
            ]

            # Check if we're heading into a historically weak period
            avg_traffic = statistics.mean(monthly_avgs.values()) if monthly_avgs else 0
            for month in upcoming_months:
                month_num = month[5:7]
                historical_same_month = [
                    v for k, v in monthly_avgs.items()
                    if k[5:7] == month_num
                ]
                if historical_same_month:
                    expected = statistics.mean(historical_same_month)
                    if expected < avg_traffic * 0.8:
                        recommendations.append(Recommendation(
                            title=f"Prepare for seasonal dip in month {month_num}",
                            description="Historical data shows lower traffic. Plan promotional content.",
                            priority=Priority.MEDIUM,
                            category="seasonality",
                        ))
                        break

            return {
                "data": {
                    "months_analyzed": len(monthly_avgs),
                    "monthly_averages": monthly_avgs,
                    "day_of_week_averages": dow_avgs,
                    "best_months": [{"month": m, "avg_clicks": round(c, 1)} for m, c in best_months],
                    "worst_months": [{"month": m, "avg_clicks": round(c, 1)} for m, c in worst_months],
                    "best_day": sorted_days[0][0],
                    "worst_day": sorted_days[-1][0],
                    "seasonality_strength": self._calculate_seasonality_strength(list(monthly_avgs.values())),
                },
                "recommendations": recommendations,
            }

        except Exception as e:
            self.logger.error("Seasonality detection failed", error=str(e))
            return {"data": {"error": str(e)}, "recommendations": []}

    def _calculate_seasonality_strength(self, monthly_values: list[float]) -> str:
        """Calculate how strong the seasonal pattern is."""
        if not monthly_values or len(monthly_values) < 3:
            return "insufficient_data"

        avg = statistics.mean(monthly_values)
        if avg == 0:
            return "no_traffic"

        max_deviation = max(abs(v - avg) / avg * 100 for v in monthly_values)

        if max_deviation > 50:
            return "strong"
        elif max_deviation > 25:
            return "moderate"
        else:
            return "weak"

    async def _predict_ranking_changes(self, params: dict[str, Any]) -> dict[str, Any]:
        """Predict potential ranking changes based on trends."""
        queries = params.get("queries", [])
        days_back = params.get("days_back", 30)

        if not self.context.gsc_client:
            return {"data": {"error": "GSC client not configured"}, "recommendations": []}

        predictions = []
        alerts = []
        recommendations = []

        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_back)

            for query in queries[:20]:  # Limit to 20 queries
                data = await self.context.gsc_client.get_performance(
                    property_url=self.context.property_url,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    dimensions=["date"],
                    dimension_filter={"dimension": "query", "expression": query},
                )

                rows = data.get("rows", [])
                if len(rows) < 7:
                    continue

                # Calculate position trend
                positions = [row.get("position", 0) for row in sorted(rows, key=lambda x: x.get("date", ""))]
                position_trend = self._calculate_trend(positions)

                # Calculate CTR trend
                ctrs = [
                    row.get("clicks", 0) / row.get("impressions", 1) * 100
                    for row in sorted(rows, key=lambda x: x.get("date", ""))
                ]
                ctr_trend = self._calculate_trend(ctrs)

                # Current values
                current_position = positions[-1] if positions else 0
                current_ctr = ctrs[-1] if ctrs else 0

                # Predict direction
                if position_trend > 0.1:  # Position increasing = ranking dropping
                    direction = "declining"
                    risk = "high" if position_trend > 0.3 else "medium"
                elif position_trend < -0.1:
                    direction = "improving"
                    risk = "low"
                else:
                    direction = "stable"
                    risk = "low"

                predictions.append({
                    "query": query,
                    "current_position": round(current_position, 1),
                    "current_ctr": round(current_ctr, 2),
                    "position_trend": round(position_trend, 3),
                    "ctr_trend": round(ctr_trend, 3),
                    "predicted_direction": direction,
                    "risk_level": risk,
                })

            # Generate alerts for high-risk queries
            high_risk = [p for p in predictions if p["risk_level"] == "high"]
            if high_risk:
                alerts.append(Alert(
                    title=f"{len(high_risk)} queries at risk of ranking drop",
                    message="Take action to prevent ranking losses",
                    severity=Severity.WARNING,
                    source="predictive-seo",
                    data={"queries": [p["query"] for p in high_risk[:5]]},
                ))
                recommendations.append(Recommendation(
                    title="Update content for at-risk queries",
                    description=f"{len(high_risk)} queries showing declining trend. Refresh content urgently.",
                    priority=Priority.HIGH,
                    category="ranking_protection",
                    data={"queries": [p["query"] for p in high_risk]},
                ))

            return {
                "data": {
                    "queries_analyzed": len(predictions),
                    "improving": len([p for p in predictions if p["predicted_direction"] == "improving"]),
                    "stable": len([p for p in predictions if p["predicted_direction"] == "stable"]),
                    "declining": len([p for p in predictions if p["predicted_direction"] == "declining"]),
                    "predictions": predictions,
                },
                "recommendations": recommendations,
                "alerts": alerts,
            }

        except Exception as e:
            self.logger.error("Ranking prediction failed", error=str(e))
            return {"data": {"error": str(e)}, "recommendations": []}

    async def _find_emerging_keywords(self, params: dict[str, Any]) -> dict[str, Any]:
        """Find emerging keyword opportunities."""
        min_growth_pct = params.get("min_growth_pct", 50)
        min_impressions = params.get("min_impressions", 100)

        if not self.context.gsc_client:
            return {"data": {"error": "GSC client not configured"}, "recommendations": []}

        try:
            end_date = datetime.now().date()
            mid_date = end_date - timedelta(days=14)
            start_date = end_date - timedelta(days=28)

            # Get recent period
            recent_data = await self.context.gsc_client.get_performance(
                property_url=self.context.property_url,
                start_date=mid_date.isoformat(),
                end_date=end_date.isoformat(),
                dimensions=["query"],
            )

            # Get previous period
            previous_data = await self.context.gsc_client.get_performance(
                property_url=self.context.property_url,
                start_date=start_date.isoformat(),
                end_date=mid_date.isoformat(),
                dimensions=["query"],
            )

            recent_by_query = {
                row.get("query", ""): row
                for row in recent_data.get("rows", [])
            }

            previous_by_query = {
                row.get("query", ""): row
                for row in previous_data.get("rows", [])
            }

            emerging = []

            for query, recent in recent_by_query.items():
                recent_impressions = recent.get("impressions", 0)
                if recent_impressions < min_impressions:
                    continue

                previous = previous_by_query.get(query, {})
                prev_impressions = previous.get("impressions", 0)

                if prev_impressions > 0:
                    growth = (recent_impressions - prev_impressions) / prev_impressions * 100
                else:
                    growth = 100 if recent_impressions > min_impressions else 0

                if growth >= min_growth_pct:
                    emerging.append({
                        "query": query,
                        "recent_impressions": recent_impressions,
                        "previous_impressions": prev_impressions,
                        "growth_pct": round(growth, 1),
                        "current_position": round(recent.get("position", 0), 1),
                        "clicks": recent.get("clicks", 0),
                        "opportunity_score": self._calculate_opportunity_score(
                            growth, recent_impressions, recent.get("position", 100)
                        ),
                    })

            # Sort by opportunity score
            emerging.sort(key=lambda x: x["opportunity_score"], reverse=True)

            recommendations = []
            if emerging:
                top_emerging = emerging[:5]
                recommendations.append(Recommendation(
                    title=f"Found {len(emerging)} emerging keyword opportunities",
                    description="These keywords are growing rapidly - create/optimize content to capture traffic",
                    priority=Priority.HIGH,
                    category="keyword_opportunities",
                    data={"top_keywords": [e["query"] for e in top_emerging]},
                ))

            return {
                "data": {
                    "emerging_keywords": emerging[:30],
                    "total_found": len(emerging),
                    "analysis_period": "14 days vs previous 14 days",
                },
                "recommendations": recommendations,
            }

        except Exception as e:
            self.logger.error("Emerging keyword detection failed", error=str(e))
            return {"data": {"error": str(e)}, "recommendations": []}

    def _calculate_opportunity_score(
        self,
        growth: float,
        impressions: int,
        position: float,
    ) -> int:
        """Calculate opportunity score for a keyword."""
        score = 0

        # Growth factor
        if growth > 200:
            score += 40
        elif growth > 100:
            score += 30
        elif growth > 50:
            score += 20

        # Volume factor
        if impressions > 1000:
            score += 30
        elif impressions > 500:
            score += 20
        elif impressions > 100:
            score += 10

        # Position factor (closer to page 1 = better opportunity)
        if position <= 10:
            score += 30
        elif position <= 20:
            score += 20
        elif position <= 30:
            score += 10

        return min(score, 100)

    async def _algorithm_impact_analysis(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze potential algorithm update impacts."""
        # Known Google algorithm update dates (approximate)
        known_updates = [
            {"date": "2024-03-05", "name": "March 2024 Core Update"},
            {"date": "2024-08-15", "name": "August 2024 Core Update"},
            {"date": "2024-11-11", "name": "November 2024 Core Update"},
        ]

        if not self.context.gsc_client:
            return {"data": {"error": "GSC client not configured"}, "recommendations": []}

        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=180)

            data = await self.context.gsc_client.get_performance(
                property_url=self.context.property_url,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                dimensions=["date"],
            )

            rows = data.get("rows", [])
            daily_data = {row.get("date"): row for row in rows}

            # Analyze impact around update dates
            impacts = []
            for update in known_updates:
                update_date = update["date"]
                if update_date < start_date.isoformat():
                    continue

                # Get 7 days before and after
                before_clicks = []
                after_clicks = []

                for i in range(-7, 0):
                    check_date = (datetime.strptime(update_date, "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d")
                    if check_date in daily_data:
                        before_clicks.append(daily_data[check_date].get("clicks", 0))

                for i in range(1, 8):
                    check_date = (datetime.strptime(update_date, "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d")
                    if check_date in daily_data:
                        after_clicks.append(daily_data[check_date].get("clicks", 0))

                if before_clicks and after_clicks:
                    before_avg = statistics.mean(before_clicks)
                    after_avg = statistics.mean(after_clicks)
                    change_pct = ((after_avg - before_avg) / before_avg * 100) if before_avg > 0 else 0

                    impacts.append({
                        "update_name": update["name"],
                        "update_date": update_date,
                        "before_avg_clicks": round(before_avg, 1),
                        "after_avg_clicks": round(after_avg, 1),
                        "impact_pct": round(change_pct, 1),
                        "impact_type": "positive" if change_pct > 5 else "negative" if change_pct < -5 else "neutral",
                    })

            recommendations = []
            negative_impacts = [i for i in impacts if i["impact_type"] == "negative"]
            if negative_impacts:
                recommendations.append(Recommendation(
                    title="Review content quality after algorithm updates",
                    description=f"{len(negative_impacts)} updates had negative impact. Review E-E-A-T signals.",
                    priority=Priority.HIGH,
                    category="algorithm_recovery",
                ))

            return {
                "data": {
                    "updates_analyzed": len(impacts),
                    "impacts": impacts,
                    "overall_trend": "volatile" if len([i for i in impacts if abs(i["impact_pct"]) > 10]) > 1 else "stable",
                },
                "recommendations": recommendations,
            }

        except Exception as e:
            self.logger.error("Algorithm impact analysis failed", error=str(e))
            return {"data": {"error": str(e)}, "recommendations": []}

    async def _trend_analysis(self, params: dict[str, Any]) -> dict[str, Any]:
        """Comprehensive trend analysis combining multiple signals."""
        # Run multiple analyses
        traffic_forecast = await self._forecast_traffic(params)
        seasonality = await self._detect_seasonality(params)

        recommendations = []
        alerts = []

        # Combine insights
        traffic_data = traffic_forecast.get("data", {})
        season_data = seasonality.get("data", {})

        # Overall health score
        health_score = 50  # Base score

        if traffic_data.get("trend_direction") == "growing":
            health_score += 20
        elif traffic_data.get("trend_direction") == "declining":
            health_score -= 20

        predicted_change = traffic_data.get("predicted_change_pct", 0)
        if predicted_change > 10:
            health_score += 15
        elif predicted_change < -10:
            health_score -= 15

        if season_data.get("seasonality_strength") == "strong":
            health_score -= 5  # More volatile

        health_score = max(0, min(100, health_score))

        return {
            "data": {
                "health_score": health_score,
                "health_status": "good" if health_score >= 60 else "concerning" if health_score >= 40 else "critical",
                "traffic_forecast": traffic_data,
                "seasonality": season_data,
            },
            "recommendations": traffic_forecast.get("recommendations", []) + seasonality.get("recommendations", []),
            "alerts": traffic_forecast.get("alerts", []) + seasonality.get("alerts", []),
        }
