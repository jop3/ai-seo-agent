"""
AI Content Analyzer Agent - Detects and optimizes AI-generated content.
"""

import re
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

from src.agents.base import BaseAgent, AgentContext
from src.core.errors import AgentError, ErrorCode
from src.models.agents import (
    AgentTask, AgentResult, AgentType, Recommendation, Alert, Priority, Severity
)

logger = structlog.get_logger()


class AIContentAnalyzerAgent(BaseAgent):
    """
    Analyzes content for AI-generation patterns and optimization.

    Google's stance: AI content is not inherently bad, but must be
    helpful, original, and demonstrate E-E-A-T. This agent helps
    ensure AI-assisted content meets quality standards.

    Capabilities:
    - Detect common AI-generated content patterns
    - Analyze content quality and originality signals
    - Suggest humanization improvements
    - Check for AI content penalties risk
    - Optimize AI-assisted content for SEO
    """

    agent_type = AgentType.AI_CONTENT_ANALYZER

    def __init__(self, context: AgentContext):
        self.context = context
        self.logger = logger.bind(agent="ai-content-analyzer")

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute AI content analysis task."""
        task_handlers = {
            "detect_ai_patterns": self._detect_ai_patterns,
            "analyze_content_quality": self._analyze_content_quality,
            "humanization_suggestions": self._humanization_suggestions,
            "originality_check": self._originality_check,
            "optimize_ai_content": self._optimize_ai_content,
        }

        handler = task_handlers.get(task.task_type)
        if not handler:
            raise AgentError(
                f"Unknown task type: {task.task_type}",
                agent_type="ai-content-analyzer",
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

    async def _detect_ai_patterns(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Detect common patterns that indicate AI-generated content.

        These patterns don't necessarily indicate bad content, but
        can help identify areas that may need humanization.
        """
        url = params.get("url")
        text = params.get("text")

        if url and not text:
            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    response = await client.get(url)
                    soup = BeautifulSoup(response.text, "lxml")
                    # Get main content, excluding navigation, footer, etc.
                    article = soup.find("article") or soup.find("main") or soup.find("body")
                    text = article.get_text() if article else soup.get_text()
            except Exception as e:
                return {"data": {"error": f"Failed to fetch URL: {e}"}, "recommendations": []}

        if not text:
            return {"data": {"error": "URL or text required"}, "recommendations": []}

        # AI pattern detection
        patterns_detected = []
        ai_likelihood_score = 0

        # 1. Overuse of transitional phrases
        transition_phrases = [
            r"\bin conclusion\b", r"\bfurthermore\b", r"\bmoreover\b",
            r"\badditionally\b", r"\bconsequently\b", r"\bnevertheless\b",
            r"\bin summary\b", r"\bto summarize\b", r"\bin essence\b",
            r"\bit'?s worth noting\b", r"\bit'?s important to note\b",
        ]
        transition_count = sum(len(re.findall(p, text.lower())) for p in transition_phrases)
        word_count = len(text.split())

        if word_count > 0 and transition_count / (word_count / 100) > 2:
            patterns_detected.append({
                "pattern": "Excessive transitional phrases",
                "severity": "medium",
                "description": f"Found {transition_count} transitional phrases ({transition_count/(word_count/100):.1f} per 100 words)",
            })
            ai_likelihood_score += 15

        # 2. Formulaic structure phrases
        formulaic_phrases = [
            r"in today'?s (world|age|society|digital)",
            r"when it comes to",
            r"at the end of the day",
            r"it goes without saying",
            r"needless to say",
            r"as we all know",
            r"there'?s no denying",
            r"one cannot (ignore|underestimate|overstate)",
            r"plays a (crucial|vital|key|important) role",
            r"in the (realm|world|sphere) of",
            r"serves as a (testament|reminder)",
            r"(delve|dive) (into|deeper)",
        ]
        formulaic_count = sum(len(re.findall(p, text.lower())) for p in formulaic_phrases)

        if formulaic_count > 3:
            patterns_detected.append({
                "pattern": "Formulaic AI-typical phrases",
                "severity": "high",
                "description": f"Found {formulaic_count} commonly overused AI phrases",
            })
            ai_likelihood_score += 20

        # 3. Repetitive sentence starters
        sentences = re.split(r'[.!?]+', text)
        sentence_starters = [s.strip().split()[0].lower() for s in sentences if s.strip() and s.strip().split()]
        starter_counts = {}
        for starter in sentence_starters:
            starter_counts[starter] = starter_counts.get(starter, 0) + 1

        repetitive_starters = {k: v for k, v in starter_counts.items() if v > 3 and k in ["the", "this", "it", "these", "there", "however"]}
        if repetitive_starters:
            patterns_detected.append({
                "pattern": "Repetitive sentence starters",
                "severity": "low",
                "description": f"Overused starters: {list(repetitive_starters.keys())}",
            })
            ai_likelihood_score += 10

        # 4. Lack of personal pronouns (I, we, my, our)
        personal_pronouns = len(re.findall(r'\b(I|we|my|our|me|us)\b', text, re.I))
        if word_count > 300 and personal_pronouns < 3:
            patterns_detected.append({
                "pattern": "Lack of personal perspective",
                "severity": "medium",
                "description": "Very few personal pronouns - content feels impersonal",
            })
            ai_likelihood_score += 15

        # 5. Perfect grammar with no contractions
        contractions = len(re.findall(r"\b(don't|can't|won't|isn't|aren't|couldn't|wouldn't|shouldn't|it's|that's|there's|here's|what's|who's|how's|we're|they're|you're|I'm|I've|we've|they've|you've)\b", text, re.I))
        if word_count > 500 and contractions < 2:
            patterns_detected.append({
                "pattern": "Absence of contractions",
                "severity": "low",
                "description": "Very formal writing with no contractions",
            })
            ai_likelihood_score += 5

        # 6. Hedge words and qualifiers
        hedge_words = [
            r"\bgenerally\b", r"\btypically\b", r"\busually\b",
            r"\boften\b", r"\bsometimes\b", r"\bmay\b", r"\bmight\b",
            r"\bcould\b", r"\bpotentially\b", r"\bpossibly\b",
        ]
        hedge_count = sum(len(re.findall(p, text.lower())) for p in hedge_words)

        if word_count > 0 and hedge_count / (word_count / 100) > 3:
            patterns_detected.append({
                "pattern": "Excessive hedging language",
                "severity": "low",
                "description": f"High use of qualifying words ({hedge_count/(word_count/100):.1f} per 100 words)",
            })
            ai_likelihood_score += 10

        # 7. List-heavy content
        bullet_points = len(re.findall(r'^\s*[-•*]\s', text, re.MULTILINE))
        numbered_items = len(re.findall(r'^\s*\d+[.)]\s', text, re.MULTILINE))

        if bullet_points + numbered_items > word_count / 50:
            patterns_detected.append({
                "pattern": "Excessive lists",
                "severity": "low",
                "description": "Heavy reliance on bullet points and numbered lists",
            })
            ai_likelihood_score += 5

        # Calculate final assessment
        ai_likelihood_score = min(ai_likelihood_score, 100)

        if ai_likelihood_score >= 60:
            assessment = "high_ai_likelihood"
        elif ai_likelihood_score >= 35:
            assessment = "moderate_ai_likelihood"
        else:
            assessment = "low_ai_likelihood"

        recommendations = []

        if ai_likelihood_score >= 35:
            recommendations.append(Recommendation(
                title=f"AI content patterns detected (score: {ai_likelihood_score})",
                description="Consider humanizing the content to reduce AI detection risk",
                priority=Priority.MEDIUM if ai_likelihood_score < 60 else Priority.HIGH,
                category="ai_content",
            ))

        alerts = []
        if ai_likelihood_score >= 60:
            alerts.append(Alert(
                title="High AI content likelihood detected",
                message="This content shows strong AI-generation patterns that may affect rankings",
                severity=Severity.WARNING,
                source="ai-content-analyzer",
            ))

        return {
            "data": {
                "url": url,
                "word_count": word_count,
                "ai_likelihood_score": ai_likelihood_score,
                "assessment": assessment,
                "patterns_detected": patterns_detected,
                "note": "These patterns indicate style, not necessarily AI origin. Focus on quality, not detection.",
            },
            "recommendations": recommendations,
            "alerts": alerts,
        }

    async def _analyze_content_quality(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze content quality regardless of AI involvement.

        Google rewards helpful content - this checks for signals
        that indicate genuinely useful content.
        """
        url = params.get("url")

        if not url:
            return {"data": {"error": "URL required"}, "recommendations": []}

        quality_signals = []
        quality_score = 0
        max_score = 100
        recommendations = []

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                soup = BeautifulSoup(response.text, "lxml")

            article = soup.find("article") or soup.find("main") or soup.find("body")
            text = article.get_text() if article else soup.get_text()
            word_count = len(text.split())

            # 1. Content depth (word count)
            if word_count >= 2000:
                quality_signals.append({"signal": "Comprehensive length", "score": 15})
                quality_score += 15
            elif word_count >= 1000:
                quality_signals.append({"signal": "Good content length", "score": 10})
                quality_score += 10
            elif word_count >= 500:
                quality_signals.append({"signal": "Moderate length", "score": 5})
                quality_score += 5
            else:
                quality_signals.append({"signal": "Thin content", "score": 0})
                recommendations.append(Recommendation(
                    title="Content too thin",
                    description="Add more comprehensive coverage of the topic",
                    priority=Priority.HIGH,
                    category="content_quality",
                ))

            # 2. Original data/statistics
            stats_patterns = [r'\d+%', r'\d+\s*(million|billion|thousand)', r'study shows', r'research (found|indicates)']
            stats_found = sum(1 for p in stats_patterns if re.search(p, text.lower()))

            if stats_found >= 3:
                quality_signals.append({"signal": "Data-driven content", "score": 15})
                quality_score += 15
            elif stats_found >= 1:
                quality_signals.append({"signal": "Some statistics", "score": 8})
                quality_score += 8

            # 3. Expert quotes or citations
            quote_patterns = [r'"[^"]{20,}"', r'"[^"]{20,}"', r'according to', r'says \w+', r'notes \w+']
            quotes_found = sum(1 for p in quote_patterns if re.search(p, text))

            if quotes_found >= 2:
                quality_signals.append({"signal": "Expert quotes/citations", "score": 10})
                quality_score += 10

            # 4. Structured content (headings)
            headings = soup.find_all(['h2', 'h3', 'h4'])
            if len(headings) >= 5:
                quality_signals.append({"signal": "Well-structured with headings", "score": 10})
                quality_score += 10
            elif len(headings) >= 2:
                quality_signals.append({"signal": "Some structure", "score": 5})
                quality_score += 5

            # 5. Images with alt text
            images = soup.find_all("img")
            images_with_alt = [img for img in images if img.get("alt")]

            if len(images_with_alt) >= 3:
                quality_signals.append({"signal": "Multiple relevant images", "score": 10})
                quality_score += 10
            elif len(images_with_alt) >= 1:
                quality_signals.append({"signal": "Has images", "score": 5})
                quality_score += 5

            # 6. Internal/external links
            all_links = soup.find_all("a", href=True)
            internal = [l for l in all_links if not l["href"].startswith("http") or self.context.client_domain in l["href"]]
            external = [l for l in all_links if l["href"].startswith("http") and self.context.client_domain not in l["href"]]

            if len(external) >= 3:
                quality_signals.append({"signal": "Good external references", "score": 10})
                quality_score += 10

            if len(internal) >= 3:
                quality_signals.append({"signal": "Good internal linking", "score": 5})
                quality_score += 5

            # 7. Unique perspective/experience indicators
            experience_patterns = [r'\bi (tried|tested|used|found|discovered)', r'in my experience', r'we (tested|reviewed)', r'hands-on']
            experience_found = sum(1 for p in experience_patterns if re.search(p, text.lower()))

            if experience_found >= 2:
                quality_signals.append({"signal": "First-hand experience", "score": 15})
                quality_score += 15
            elif experience_found >= 1:
                quality_signals.append({"signal": "Some personal experience", "score": 8})
                quality_score += 8
            else:
                recommendations.append(Recommendation(
                    title="Add first-hand experience",
                    description="Include personal testing, experience, or unique insights",
                    priority=Priority.MEDIUM,
                    category="content_quality",
                ))

            # 8. FAQ or direct answers
            faq_present = bool(soup.find(class_=re.compile(r'faq', re.I)) or re.search(r'\?[\s\n]+[A-Z]', text))
            if faq_present:
                quality_signals.append({"signal": "FAQ/Q&A format", "score": 5})
                quality_score += 5

            percentage = (quality_score / max_score) * 100

            return {
                "data": {
                    "url": url,
                    "word_count": word_count,
                    "quality_score": quality_score,
                    "max_score": max_score,
                    "percentage": round(percentage, 1),
                    "grade": self._score_to_grade(percentage),
                    "quality_signals": quality_signals,
                },
                "recommendations": recommendations,
            }

        except Exception as e:
            self.logger.error("Content quality analysis failed", error=str(e))
            return {"data": {"error": str(e)}, "recommendations": []}

    def _score_to_grade(self, percentage: float) -> str:
        """Convert percentage to letter grade."""
        if percentage >= 90:
            return "A"
        elif percentage >= 80:
            return "B"
        elif percentage >= 70:
            return "C"
        elif percentage >= 60:
            return "D"
        else:
            return "F"

    async def _humanization_suggestions(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Provide specific suggestions to humanize AI-generated content.
        """
        url = params.get("url")
        text = params.get("text")

        if url and not text:
            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    response = await client.get(url)
                    soup = BeautifulSoup(response.text, "lxml")
                    article = soup.find("article") or soup.find("main") or soup.body
                    text = article.get_text() if article else soup.get_text()
            except Exception as e:
                return {"data": {"error": f"Failed to fetch URL: {e}"}, "recommendations": []}

        if not text:
            return {"data": {"error": "URL or text required"}, "recommendations": []}

        suggestions = []

        # Check for issues and provide specific suggestions
        text_lower = text.lower()

        # 1. Add personal anecdotes
        if not re.search(r'\b(I|we|my|our)\b', text, re.I) or len(re.findall(r'\b(I|we|my|our)\b', text, re.I)) < 3:
            suggestions.append({
                "category": "Personal Touch",
                "issue": "Content lacks personal perspective",
                "suggestion": "Add personal anecdotes, experiences, or opinions. Start sentences with 'I found...' or 'In my experience...'",
                "example": "Instead of 'This product is effective' → 'I've been using this product for 3 months and noticed significant improvements'",
                "priority": "high",
            })

        # 2. Vary sentence structure
        sentences = re.split(r'[.!?]+', text)
        if len(sentences) > 10:
            avg_words = sum(len(s.split()) for s in sentences) / len(sentences)
            if 15 <= avg_words <= 25:  # Very uniform
                suggestions.append({
                    "category": "Sentence Variety",
                    "issue": "Sentences are too uniform in length",
                    "suggestion": "Mix short punchy sentences with longer explanatory ones",
                    "example": "Add some 5-word sentences. Then follow with a more detailed explanation that provides context and nuance.",
                    "priority": "medium",
                })

        # 3. Replace common AI phrases
        ai_phrase_replacements = [
            ("in today's world", "right now", "currently"),
            ("it's worth noting", "notably", "keep in mind"),
            ("at the end of the day", "ultimately", "finally"),
            ("when it comes to", "regarding", "for"),
            ("plays a crucial role", "is essential", "matters significantly"),
            ("delve into", "explore", "examine", "look at"),
            ("in the realm of", "in", "within"),
        ]

        for phrases in ai_phrase_replacements:
            original = phrases[0]
            if original in text_lower:
                suggestions.append({
                    "category": "Phrase Replacement",
                    "issue": f"Overused phrase: '{original}'",
                    "suggestion": f"Replace with: {', '.join(phrases[1:])}",
                    "priority": "low",
                })

        # 4. Add contractions
        formal_patterns = [
            ("do not", "don't"),
            ("cannot", "can't"),
            ("will not", "won't"),
            ("it is", "it's"),
            ("they are", "they're"),
        ]
        for formal, informal in formal_patterns:
            if formal in text_lower and informal not in text_lower:
                suggestions.append({
                    "category": "Natural Language",
                    "issue": f"Too formal: '{formal}'",
                    "suggestion": f"Use contractions like '{informal}' for a more natural tone",
                    "priority": "low",
                })
                break  # Only suggest once

        # 5. Add specific details
        vague_patterns = ["many people", "some experts", "various studies", "in many cases"]
        for pattern in vague_patterns:
            if pattern in text_lower:
                suggestions.append({
                    "category": "Specificity",
                    "issue": f"Vague reference: '{pattern}'",
                    "suggestion": "Replace vague references with specific names, numbers, or sources",
                    "example": f"Instead of '{pattern}' → 'Dr. Jane Smith from Harvard' or '73% of users in our 2024 survey'",
                    "priority": "high",
                })
                break

        # 6. Add emotional language
        emotional_words = ["love", "hate", "excited", "frustrated", "amazing", "terrible", "honestly", "frankly"]
        if not any(word in text_lower for word in emotional_words):
            suggestions.append({
                "category": "Emotional Connection",
                "issue": "Content feels emotionally flat",
                "suggestion": "Add genuine emotional reactions and opinions",
                "example": "Include phrases like 'I was genuinely surprised...', 'What really frustrated me...', 'I honestly think...'",
                "priority": "medium",
            })

        # 7. Questions for engagement
        if text.count("?") < 2:
            suggestions.append({
                "category": "Reader Engagement",
                "issue": "Few or no questions to readers",
                "suggestion": "Add rhetorical questions or direct questions to engage readers",
                "example": "What's the first thing you notice? Have you ever experienced this?",
                "priority": "low",
            })

        return {
            "data": {
                "url": url,
                "suggestions_count": len(suggestions),
                "suggestions": suggestions,
                "humanization_checklist": [
                    "Add personal stories and experiences",
                    "Include specific names, dates, and numbers",
                    "Use contractions naturally",
                    "Vary sentence length dramatically",
                    "Express genuine opinions and emotions",
                    "Ask questions to engage readers",
                    "Include imperfections (colloquialisms, humor)",
                    "Reference current events or trends",
                    "Show your unique perspective",
                ],
            },
            "recommendations": [
                Recommendation(
                    title=f"{len(suggestions)} humanization opportunities found",
                    description="Apply these suggestions to make content feel more authentic",
                    priority=Priority.MEDIUM,
                    category="content_humanization",
                ),
            ] if suggestions else [],
        }

    async def _originality_check(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Check for originality signals in content.

        Note: Full plagiarism checking requires external APIs.
        This provides heuristic-based originality assessment.
        """
        url = params.get("url")

        if not url:
            return {"data": {"error": "URL required"}, "recommendations": []}

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                soup = BeautifulSoup(response.text, "lxml")

            article = soup.find("article") or soup.find("main") or soup.body
            text = article.get_text() if article else soup.get_text()

            originality_signals = []
            score = 0
            max_score = 100
            recommendations = []

            # 1. Unique data/research
            original_patterns = [
                r"our (research|study|analysis|survey|data)",
                r"we (found|discovered|tested|analyzed|measured)",
                r"in our (test|experiment|review)",
                r"based on our",
            ]
            original_research = sum(1 for p in original_patterns if re.search(p, text.lower()))

            if original_research >= 2:
                originality_signals.append({"signal": "Original research/data", "score": 30})
                score += 30
            elif original_research >= 1:
                originality_signals.append({"signal": "Some original insights", "score": 15})
                score += 15
            else:
                recommendations.append(Recommendation(
                    title="Add original research or data",
                    description="Include unique findings, surveys, or analysis",
                    priority=Priority.HIGH,
                    category="originality",
                ))

            # 2. Unique perspective indicators
            opinion_patterns = [
                r"I (think|believe|feel|argue)",
                r"my (opinion|view|take|perspective)",
                r"in my experience",
                r"I'?ve (found|noticed|observed)",
            ]
            opinions = sum(1 for p in opinion_patterns if re.search(p, text.lower()))

            if opinions >= 3:
                originality_signals.append({"signal": "Strong personal perspective", "score": 20})
                score += 20
            elif opinions >= 1:
                originality_signals.append({"signal": "Some personal perspective", "score": 10})
                score += 10

            # 3. Specific examples and case studies
            example_patterns = [
                r"for example",
                r"case study",
                r"real-?world example",
                r"here'?s (how|what|an example)",
            ]
            examples = sum(1 for p in example_patterns if re.search(p, text.lower()))

            if examples >= 3:
                originality_signals.append({"signal": "Rich with examples", "score": 15})
                score += 15
            elif examples >= 1:
                originality_signals.append({"signal": "Has examples", "score": 8})
                score += 8

            # 4. Unique imagery
            images = soup.find_all("img")
            # Check for original image naming patterns (not stock photos)
            original_images = [img for img in images if img.get("src") and
                            not any(stock in img["src"].lower() for stock in
                                  ["stock", "shutterstock", "getty", "unsplash", "pexels", "istockphoto"])]

            if len(original_images) >= 3:
                originality_signals.append({"signal": "Original images", "score": 15})
                score += 15

            # 5. Unique quotes or interviews
            if re.search(r'(interview|spoke with|told us|said in an email)', text.lower()):
                originality_signals.append({"signal": "Original interviews/quotes", "score": 20})
                score += 20

            percentage = (score / max_score) * 100

            return {
                "data": {
                    "url": url,
                    "originality_score": score,
                    "max_score": max_score,
                    "percentage": round(percentage, 1),
                    "originality_signals": originality_signals,
                    "note": "This is a heuristic check. For full plagiarism checking, use Copyscape or similar services.",
                },
                "recommendations": recommendations,
            }

        except Exception as e:
            self.logger.error("Originality check failed", error=str(e))
            return {"data": {"error": str(e)}, "recommendations": []}

    async def _optimize_ai_content(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Comprehensive AI content optimization recommendations.

        Combines detection, quality, and humanization into
        actionable optimization plan.
        """
        url = params.get("url")

        if not url:
            return {"data": {"error": "URL required"}, "recommendations": []}

        # Run all analyses
        detection_result = await self._detect_ai_patterns({"url": url})
        quality_result = await self._analyze_content_quality({"url": url})
        humanization_result = await self._humanization_suggestions({"url": url})
        originality_result = await self._originality_check({"url": url})

        # Compile optimization plan
        optimization_plan = []
        all_recommendations = []

        # Priority 1: High AI likelihood issues
        ai_score = detection_result["data"].get("ai_likelihood_score", 0)
        if ai_score >= 50:
            optimization_plan.append({
                "priority": 1,
                "area": "AI Pattern Reduction",
                "current_state": f"AI likelihood: {ai_score}%",
                "actions": [p["description"] for p in detection_result["data"].get("patterns_detected", [])],
            })

        # Priority 2: Quality improvements
        quality_score = quality_result["data"].get("percentage", 0)
        if quality_score < 70:
            optimization_plan.append({
                "priority": 2,
                "area": "Content Quality",
                "current_state": f"Quality score: {quality_score}%",
                "actions": [r.description for r in quality_result.get("recommendations", [])],
            })

        # Priority 3: Originality
        originality_score = originality_result["data"].get("percentage", 0)
        if originality_score < 60:
            optimization_plan.append({
                "priority": 3,
                "area": "Originality & Uniqueness",
                "current_state": f"Originality score: {originality_score}%",
                "actions": [r.description for r in originality_result.get("recommendations", [])],
            })

        # Priority 4: Humanization
        humanization_count = humanization_result["data"].get("suggestions_count", 0)
        if humanization_count > 3:
            top_suggestions = humanization_result["data"].get("suggestions", [])[:5]
            optimization_plan.append({
                "priority": 4,
                "area": "Humanization",
                "current_state": f"{humanization_count} opportunities",
                "actions": [s["suggestion"] for s in top_suggestions],
            })

        # Calculate overall score
        overall_score = (
            (100 - ai_score) * 0.25 +  # Lower AI score is better
            quality_score * 0.35 +
            originality_score * 0.25 +
            max(0, 100 - humanization_count * 10) * 0.15
        )

        # Generate top-level recommendation
        if overall_score < 50:
            all_recommendations.append(Recommendation(
                title="Content needs significant optimization",
                description="Follow the optimization plan to improve AI content quality",
                priority=Priority.HIGH,
                category="ai_content_optimization",
            ))
        elif overall_score < 70:
            all_recommendations.append(Recommendation(
                title="Content has room for improvement",
                description="Address the highlighted areas to strengthen content",
                priority=Priority.MEDIUM,
                category="ai_content_optimization",
            ))

        return {
            "data": {
                "url": url,
                "overall_score": round(overall_score, 1),
                "component_scores": {
                    "ai_detection": 100 - ai_score,  # Inverted - lower AI detection is better
                    "quality": quality_score,
                    "originality": originality_score,
                    "humanization": max(0, 100 - humanization_count * 10),
                },
                "optimization_plan": optimization_plan,
                "google_helpful_content_alignment": [
                    "Does this content demonstrate first-hand expertise?",
                    "Does it provide substantial value beyond what's freely available?",
                    "Will readers feel satisfied after reading?",
                    "Is it written for humans first, search engines second?",
                    "Does it answer questions thoroughly?",
                ],
            },
            "recommendations": all_recommendations,
        }
