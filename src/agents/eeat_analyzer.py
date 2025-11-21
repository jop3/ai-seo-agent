"""
E-E-A-T Analyzer Agent - Evaluates Experience, Expertise, Authoritativeness, and Trustworthiness.
"""

import re
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog
from bs4 import BeautifulSoup

from src.agents.base import BaseAgent, AgentContext
from src.core.errors import AgentError, ErrorCode
from src.models.agents import (
    AgentTask, AgentResult, AgentType, Recommendation, Alert, Priority, Severity
)

logger = structlog.get_logger()


class EEATAnalyzerAgent(BaseAgent):
    """
    Analyzes E-E-A-T signals for better AI citation eligibility.

    Google's E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness)
    is critical for being cited in AI Overviews.

    Capabilities:
    - Audit author credentials and bios
    - Check expertise signals on pages
    - Analyze trust indicators (reviews, certifications)
    - Evaluate content authoritativeness
    - Suggest E-E-A-T improvements
    """

    agent_type = AgentType.EEAT_ANALYZER

    def __init__(self, context: AgentContext):
        self.context = context
        self.logger = logger.bind(agent="eeat-analyzer")

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute E-E-A-T analysis task."""
        task_handlers = {
            "full_audit": self._full_eeat_audit,
            "analyze_author_signals": self._analyze_author_signals,
            "check_trust_indicators": self._check_trust_indicators,
            "evaluate_expertise": self._evaluate_expertise,
            "analyze_citations": self._analyze_citations,
            "competitor_eeat_comparison": self._competitor_eeat_comparison,
        }

        handler = task_handlers.get(task.task_type)
        if not handler:
            raise AgentError(
                f"Unknown task type: {task.task_type}",
                agent_type="eeat-analyzer",
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

    async def _full_eeat_audit(self, params: dict[str, Any]) -> dict[str, Any]:
        """Comprehensive E-E-A-T audit for a URL."""
        url = params.get("url", self.context.property_url)

        if not url:
            return {"data": {"error": "URL required"}, "recommendations": []}

        recommendations = []
        alerts = []

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                soup = BeautifulSoup(response.text, "lxml")

            # Score components
            scores = {
                "experience": 0,
                "expertise": 0,
                "authoritativeness": 0,
                "trustworthiness": 0,
            }
            max_scores = {
                "experience": 25,
                "expertise": 25,
                "authoritativeness": 25,
                "trustworthiness": 25,
            }

            findings = {
                "positive": [],
                "negative": [],
                "suggestions": [],
            }

            # === EXPERIENCE SIGNALS ===
            # First-hand experience indicators
            experience_patterns = [
                r"i (tried|tested|used|experienced|found)",
                r"in my experience",
                r"after (using|testing|trying)",
                r"hands-on",
                r"personal(ly)?",
                r"our team",
                r"we (tested|reviewed|evaluated)",
            ]

            text = soup.get_text().lower()
            experience_found = sum(1 for p in experience_patterns if re.search(p, text))

            if experience_found >= 3:
                scores["experience"] += 15
                findings["positive"].append("Strong first-hand experience signals")
            elif experience_found >= 1:
                scores["experience"] += 8
                findings["positive"].append("Some experience signals present")
            else:
                findings["negative"].append("No first-hand experience signals")
                findings["suggestions"].append("Add personal experience and testing details")

            # Date signals (fresh content shows active experience)
            date_indicators = soup.find_all(["time", "span", "p"], class_=re.compile(r"date|time|publish", re.I))
            if date_indicators:
                scores["experience"] += 5
                findings["positive"].append("Publication date visible")

            # Review/testing methodology
            if re.search(r"(methodology|how we (tested|reviewed)|our process)", text):
                scores["experience"] += 5
                findings["positive"].append("Testing methodology explained")

            # === EXPERTISE SIGNALS ===
            # Author information
            author_section = soup.find(["div", "section", "aside"], class_=re.compile(r"author|byline|bio", re.I))
            author_schema = soup.find("script", type="application/ld+json", string=re.compile(r'"@type"\s*:\s*"Person"'))

            if author_section:
                scores["expertise"] += 8
                findings["positive"].append("Author section present")

                # Check for credentials
                author_text = author_section.get_text().lower()
                credential_patterns = [
                    r"ph\.?d", r"m\.?d\.?", r"certified", r"expert", r"specialist",
                    r"years? (of )?experience", r"professional", r"licensed",
                ]
                credentials_found = sum(1 for p in credential_patterns if re.search(p, author_text))

                if credentials_found >= 2:
                    scores["expertise"] += 10
                    findings["positive"].append("Strong author credentials displayed")
                elif credentials_found >= 1:
                    scores["expertise"] += 5
                    findings["positive"].append("Some author credentials present")
            else:
                findings["negative"].append("No author bio/byline found")
                findings["suggestions"].append("Add detailed author bios with credentials")

            if author_schema:
                scores["expertise"] += 7
                findings["positive"].append("Person schema markup present")
            else:
                findings["suggestions"].append("Add Person schema for authors")

            # === AUTHORITATIVENESS SIGNALS ===
            # External citations/references
            external_links = []
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if href.startswith("http") and urlparse(url).netloc not in href:
                    external_links.append(href)

            # Check for authoritative citations
            authority_domains = [".gov", ".edu", ".org", "pubmed", "scholar.google", "doi.org"]
            auth_citations = [l for l in external_links if any(d in l.lower() for d in authority_domains)]

            if len(auth_citations) >= 3:
                scores["authoritativeness"] += 12
                findings["positive"].append(f"Cites {len(auth_citations)} authoritative sources")
            elif len(auth_citations) >= 1:
                scores["authoritativeness"] += 6
                findings["positive"].append("Some authoritative citations")
            else:
                findings["negative"].append("No authoritative source citations")
                findings["suggestions"].append("Add citations to .gov, .edu, or research sources")

            # Organization schema
            org_schema = soup.find("script", type="application/ld+json", string=re.compile(r'"@type"\s*:\s*"Organization"'))
            if org_schema:
                scores["authoritativeness"] += 8
                findings["positive"].append("Organization schema present")

            # Awards/recognition mentions
            if re.search(r"(award|recognized|featured in|as seen on|certified by)", text):
                scores["authoritativeness"] += 5
                findings["positive"].append("Recognition/awards mentioned")

            # === TRUSTWORTHINESS SIGNALS ===
            # HTTPS
            if url.startswith("https"):
                scores["trustworthiness"] += 5
                findings["positive"].append("HTTPS enabled")
            else:
                findings["negative"].append("Not using HTTPS")
                alerts.append(Alert(
                    title="Site not using HTTPS",
                    message="HTTPS is essential for trust and rankings",
                    severity=Severity.ERROR,
                    source="eeat-analyzer",
                ))

            # Privacy policy / Terms
            footer = soup.find(["footer", "div"], class_=re.compile(r"footer", re.I))
            footer_text = footer.get_text().lower() if footer else ""
            all_links_text = " ".join(a.get_text().lower() for a in soup.find_all("a"))

            if "privacy" in footer_text or "privacy" in all_links_text:
                scores["trustworthiness"] += 5
                findings["positive"].append("Privacy policy linked")

            if "terms" in footer_text or "terms" in all_links_text:
                scores["trustworthiness"] += 3
                findings["positive"].append("Terms of service linked")

            # Contact information
            contact_patterns = [r"contact", r"about us", r"phone", r"email", r"address"]
            contact_found = sum(1 for p in contact_patterns if re.search(p, all_links_text))

            if contact_found >= 2:
                scores["trustworthiness"] += 7
                findings["positive"].append("Contact information available")
            else:
                findings["suggestions"].append("Add clear contact information")

            # Reviews/testimonials schema
            review_schema = soup.find("script", type="application/ld+json", string=re.compile(r'"@type"\s*:\s*"Review"'))
            if review_schema or re.search(r"(customer reviews|testimonials|ratings)", text):
                scores["trustworthiness"] += 5
                findings["positive"].append("Reviews/testimonials present")

            # Calculate total score
            total_score = sum(scores.values())
            max_total = sum(max_scores.values())
            percentage = (total_score / max_total * 100) if max_total > 0 else 0

            # Generate recommendations
            if percentage < 50:
                recommendations.append(Recommendation(
                    title=f"E-E-A-T score critically low: {percentage:.0f}%",
                    description="Significant improvements needed for AI citation eligibility",
                    priority=Priority.CRITICAL,
                    category="eeat",
                ))
            elif percentage < 70:
                recommendations.append(Recommendation(
                    title=f"E-E-A-T score needs improvement: {percentage:.0f}%",
                    description="Address the suggestions to improve authority signals",
                    priority=Priority.HIGH,
                    category="eeat",
                ))

            # Add specific recommendations from suggestions
            for suggestion in findings["suggestions"][:5]:
                recommendations.append(Recommendation(
                    title=suggestion,
                    description="Improving this will boost E-E-A-T signals",
                    priority=Priority.MEDIUM,
                    category="eeat",
                ))

            return {
                "data": {
                    "url": url,
                    "total_score": total_score,
                    "max_score": max_total,
                    "percentage": round(percentage, 1),
                    "scores": scores,
                    "max_scores": max_scores,
                    "findings": findings,
                    "grade": self._score_to_grade(percentage),
                },
                "recommendations": recommendations,
                "alerts": alerts,
            }

        except Exception as e:
            self.logger.error("E-E-A-T audit failed", error=str(e))
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

    async def _analyze_author_signals(self, params: dict[str, Any]) -> dict[str, Any]:
        """Deep analysis of author expertise signals."""
        url = params.get("url")

        if not url:
            return {"data": {"error": "URL required"}, "recommendations": []}

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                soup = BeautifulSoup(response.text, "lxml")

            authors = []
            recommendations = []

            # Find author elements
            author_elements = soup.find_all(["div", "span", "a", "p"], class_=re.compile(r"author|byline|writer", re.I))
            author_elements += soup.find_all("a", rel="author")

            # Parse JSON-LD for author data
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    import json
                    data = json.loads(script.string)

                    if isinstance(data, dict):
                        author_data = data.get("author")
                        if author_data:
                            if isinstance(author_data, list):
                                for a in author_data:
                                    authors.append(self._parse_author_schema(a))
                            else:
                                authors.append(self._parse_author_schema(author_data))
                except Exception:
                    pass

            # Extract from HTML if no schema
            if not authors:
                for elem in author_elements[:3]:
                    name = elem.get_text(strip=True)
                    link = elem.get("href") if elem.name == "a" else elem.find("a", href=True)
                    link_url = link.get("href") if link and hasattr(link, "get") else None

                    if name and len(name) < 100:
                        authors.append({
                            "name": name,
                            "url": link_url,
                            "has_bio_page": link_url is not None,
                            "credentials": [],
                        })

            # Analyze author pages if available
            for author in authors:
                if author.get("url"):
                    try:
                        author_page = await client.get(author["url"])
                        author_soup = BeautifulSoup(author_page.text, "lxml")
                        author_text = author_soup.get_text().lower()

                        # Look for credentials
                        credentials = []
                        cred_patterns = {
                            "education": r"(ph\.?d|master|bachelor|m\.?b\.?a|degree)",
                            "certification": r"(certified|licensed|accredited)",
                            "experience": r"(\d+\+?\s*years?)",
                            "role": r"(ceo|founder|director|manager|expert|specialist)",
                        }

                        for cred_type, pattern in cred_patterns.items():
                            if re.search(pattern, author_text):
                                credentials.append(cred_type)

                        author["credentials"] = credentials
                        author["has_detailed_bio"] = len(author_text) > 500
                    except Exception:
                        pass

            # Generate recommendations
            if not authors:
                recommendations.append(Recommendation(
                    title="No author information found",
                    description="Add clear author bylines with links to bio pages",
                    priority=Priority.HIGH,
                    category="eeat_author",
                ))
            else:
                authors_without_bios = [a for a in authors if not a.get("has_bio_page")]
                if authors_without_bios:
                    recommendations.append(Recommendation(
                        title=f"{len(authors_without_bios)} authors missing bio pages",
                        description="Create detailed author pages with credentials and experience",
                        priority=Priority.MEDIUM,
                        category="eeat_author",
                    ))

            return {
                "data": {
                    "url": url,
                    "authors_found": len(authors),
                    "authors": authors,
                    "has_author_schema": any(a.get("from_schema") for a in authors),
                },
                "recommendations": recommendations,
            }

        except Exception as e:
            self.logger.error("Author analysis failed", error=str(e))
            return {"data": {"error": str(e)}, "recommendations": []}

    def _parse_author_schema(self, data: dict) -> dict:
        """Parse author from schema.org data."""
        if isinstance(data, str):
            return {"name": data, "from_schema": True}

        return {
            "name": data.get("name", ""),
            "url": data.get("url", ""),
            "job_title": data.get("jobTitle", ""),
            "organization": data.get("worksFor", {}).get("name", "") if isinstance(data.get("worksFor"), dict) else "",
            "same_as": data.get("sameAs", []),
            "from_schema": True,
        }

    async def _check_trust_indicators(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check trust indicators on a site."""
        url = params.get("url", self.context.property_url)

        if not url:
            return {"data": {"error": "URL required"}, "recommendations": []}

        trust_signals = {
            "security": [],
            "transparency": [],
            "social_proof": [],
            "business_info": [],
        }

        recommendations = []

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                soup = BeautifulSoup(response.text, "lxml")

            # Security
            if url.startswith("https"):
                trust_signals["security"].append({"signal": "HTTPS", "present": True})

            # Check for security badges/seals
            text = soup.get_text().lower()
            badges = ["ssl", "secure", "verified", "trusted", "mcafee", "norton", "trustpilot"]
            for badge in badges:
                if badge in text:
                    trust_signals["security"].append({"signal": f"{badge} mentioned", "present": True})

            # Transparency
            links_text = " ".join(a.get_text().lower() for a in soup.find_all("a"))

            transparency_items = [
                ("Privacy Policy", "privacy"),
                ("Terms of Service", "terms"),
                ("About Us", "about"),
                ("Contact", "contact"),
                ("Editorial Policy", "editorial"),
                ("Correction Policy", "correction"),
            ]

            for name, keyword in transparency_items:
                present = keyword in links_text
                trust_signals["transparency"].append({"signal": name, "present": present})
                if not present and keyword in ["privacy", "about", "contact"]:
                    recommendations.append(Recommendation(
                        title=f"Add {name} page",
                        description=f"Essential for trust - add a clear {name} page",
                        priority=Priority.MEDIUM,
                        category="trust",
                    ))

            # Social proof
            review_patterns = ["reviews", "testimonials", "ratings", "stars"]
            for pattern in review_patterns:
                if pattern in text:
                    trust_signals["social_proof"].append({"signal": pattern, "present": True})

            # Business info
            business_patterns = [
                ("Physical Address", r"\d+\s+\w+\s+(street|st|avenue|ave|road|rd|drive|dr)"),
                ("Phone Number", r"[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}"),
                ("Email", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
            ]

            for name, pattern in business_patterns:
                present = bool(re.search(pattern, text, re.I))
                trust_signals["business_info"].append({"signal": name, "present": present})

            # Calculate trust score
            all_signals = []
            for category in trust_signals.values():
                all_signals.extend(category)

            positive = sum(1 for s in all_signals if s.get("present"))
            total = len(all_signals)
            trust_score = (positive / total * 100) if total > 0 else 0

            return {
                "data": {
                    "url": url,
                    "trust_score": round(trust_score, 1),
                    "signals": trust_signals,
                    "positive_signals": positive,
                    "total_signals": total,
                },
                "recommendations": recommendations,
            }

        except Exception as e:
            self.logger.error("Trust check failed", error=str(e))
            return {"data": {"error": str(e)}, "recommendations": []}

    async def _evaluate_expertise(self, params: dict[str, Any]) -> dict[str, Any]:
        """Evaluate expertise signals in content."""
        url = params.get("url")
        topic = params.get("topic", "")

        if not url:
            return {"data": {"error": "URL required"}, "recommendations": []}

        expertise_signals = []
        recommendations = []

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                soup = BeautifulSoup(response.text, "lxml")

            text = soup.get_text().lower()

            # Technical depth indicators
            technical_terms = 0
            sentences = text.split(".")
            long_sentences = [s for s in sentences if len(s.split()) > 15]

            if len(long_sentences) / max(len(sentences), 1) > 0.3:
                expertise_signals.append({
                    "signal": "Complex sentence structure",
                    "score": 10,
                    "description": "Content shows depth and nuance",
                })

            # Data and statistics
            stat_patterns = [r"\d+%", r"\d+\s*(million|billion|thousand)", r"study|research|survey"]
            stats_found = sum(1 for p in stat_patterns if re.search(p, text))

            if stats_found >= 3:
                expertise_signals.append({
                    "signal": "Data-driven content",
                    "score": 15,
                    "description": "Uses statistics and research",
                })
            elif stats_found >= 1:
                expertise_signals.append({
                    "signal": "Some data references",
                    "score": 8,
                    "description": "Limited statistics usage",
                })

            # Citations to external sources
            external_links = [a for a in soup.find_all("a", href=True) if a["href"].startswith("http")]
            scholarly_links = [l for l in external_links if any(d in l["href"] for d in [".edu", ".gov", "pubmed", "doi.org"])]

            if len(scholarly_links) >= 3:
                expertise_signals.append({
                    "signal": "Scholarly citations",
                    "score": 15,
                    "description": f"Cites {len(scholarly_links)} academic/government sources",
                })

            # Original research/data
            original_patterns = [r"our (research|study|analysis|data)", r"we (found|discovered|analyzed)"]
            if any(re.search(p, text) for p in original_patterns):
                expertise_signals.append({
                    "signal": "Original research",
                    "score": 20,
                    "description": "Contains original research or analysis",
                })

            # Methodology explanation
            if re.search(r"(methodology|how we|our process|our approach)", text):
                expertise_signals.append({
                    "signal": "Methodology explained",
                    "score": 10,
                    "description": "Explains research/testing methodology",
                })

            # Calculate expertise score
            total_score = sum(s["score"] for s in expertise_signals)
            max_possible = 70

            if total_score < 30:
                recommendations.append(Recommendation(
                    title="Improve content expertise signals",
                    description="Add data, citations, and demonstrate deep topic knowledge",
                    priority=Priority.HIGH,
                    category="eeat_expertise",
                ))

            return {
                "data": {
                    "url": url,
                    "expertise_score": total_score,
                    "max_score": max_possible,
                    "percentage": round(total_score / max_possible * 100, 1),
                    "signals": expertise_signals,
                },
                "recommendations": recommendations,
            }

        except Exception as e:
            self.logger.error("Expertise evaluation failed", error=str(e))
            return {"data": {"error": str(e)}, "recommendations": []}

    async def _analyze_citations(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze citation quality and patterns."""
        url = params.get("url")

        if not url:
            return {"data": {"error": "URL required"}, "recommendations": []}

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                soup = BeautifulSoup(response.text, "lxml")

            citations = []
            domain = urlparse(url).netloc

            for link in soup.find_all("a", href=True):
                href = link["href"]
                if not href.startswith("http") or domain in href:
                    continue

                link_domain = urlparse(href).netloc
                anchor = link.get_text(strip=True)

                citation = {
                    "url": href,
                    "domain": link_domain,
                    "anchor_text": anchor[:100] if anchor else "[no anchor]",
                    "authority_type": self._classify_domain_authority(link_domain),
                }
                citations.append(citation)

            # Categorize citations
            authority_breakdown = {}
            for c in citations:
                auth_type = c["authority_type"]
                authority_breakdown[auth_type] = authority_breakdown.get(auth_type, 0) + 1

            recommendations = []

            if not citations:
                recommendations.append(Recommendation(
                    title="No external citations found",
                    description="Add references to authoritative sources to build credibility",
                    priority=Priority.HIGH,
                    category="citations",
                ))
            elif authority_breakdown.get("high_authority", 0) == 0:
                recommendations.append(Recommendation(
                    title="No high-authority citations",
                    description="Add citations to .gov, .edu, or peer-reviewed sources",
                    priority=Priority.MEDIUM,
                    category="citations",
                ))

            return {
                "data": {
                    "url": url,
                    "total_citations": len(citations),
                    "authority_breakdown": authority_breakdown,
                    "citations": citations[:20],
                },
                "recommendations": recommendations,
            }

        except Exception as e:
            self.logger.error("Citation analysis failed", error=str(e))
            return {"data": {"error": str(e)}, "recommendations": []}

    def _classify_domain_authority(self, domain: str) -> str:
        """Classify domain authority level."""
        domain_lower = domain.lower()

        if any(tld in domain_lower for tld in [".gov", ".edu"]):
            return "high_authority"
        elif any(d in domain_lower for d in ["pubmed", "scholar.google", "doi.org", "nature.com", "sciencedirect"]):
            return "high_authority"
        elif domain_lower.endswith(".org"):
            return "medium_authority"
        elif any(d in domain_lower for d in ["wikipedia", "britannica"]):
            return "reference"
        else:
            return "general"

    async def _competitor_eeat_comparison(self, params: dict[str, Any]) -> dict[str, Any]:
        """Compare E-E-A-T signals with competitors."""
        your_url = params.get("your_url", self.context.property_url)
        competitor_urls = params.get("competitor_urls", [])

        if not your_url or not competitor_urls:
            return {"data": {"error": "your_url and competitor_urls required"}, "recommendations": []}

        results = []

        # Audit your page
        your_audit = await self._full_eeat_audit({"url": your_url})
        results.append({
            "url": your_url,
            "is_yours": True,
            "score": your_audit["data"].get("percentage", 0),
            "grade": your_audit["data"].get("grade", "F"),
            "scores": your_audit["data"].get("scores", {}),
        })

        # Audit competitors
        for comp_url in competitor_urls[:5]:
            comp_audit = await self._full_eeat_audit({"url": comp_url})
            results.append({
                "url": comp_url,
                "is_yours": False,
                "score": comp_audit["data"].get("percentage", 0),
                "grade": comp_audit["data"].get("grade", "F"),
                "scores": comp_audit["data"].get("scores", {}),
            })

        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)

        # Find your ranking
        your_rank = next((i + 1 for i, r in enumerate(results) if r["is_yours"]), len(results))

        recommendations = []
        your_score = results[your_rank - 1]["score"] if results else 0

        if your_rank > 1:
            leader = results[0]
            gap = leader["score"] - your_score

            recommendations.append(Recommendation(
                title=f"E-E-A-T gap of {gap:.0f}% vs top competitor",
                description=f"You rank #{your_rank} in E-E-A-T. Improve to match {leader['url']}",
                priority=Priority.HIGH if gap > 20 else Priority.MEDIUM,
                category="eeat_competition",
            ))

        return {
            "data": {
                "your_rank": your_rank,
                "total_compared": len(results),
                "comparison": results,
            },
            "recommendations": recommendations,
        }
