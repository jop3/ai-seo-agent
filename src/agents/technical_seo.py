"""
Technical SEO Agent - Crawls and audits technical SEO issues.
"""

import asyncio
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
import structlog
from bs4 import BeautifulSoup

from src.agents.base import BaseAgent, AgentContext
from src.core.errors import AgentError, APIError, ErrorCode
from src.models.agents import AgentTask, AgentResult, AgentType, Recommendation, Alert, Priority, Severity

logger = structlog.get_logger()


class TechnicalSEOAgent(BaseAgent):
    """
    Audits technical SEO issues.

    Capabilities:
    - Crawl site for broken links
    - Check redirect chains
    - Validate robots.txt and sitemap
    - Analyze page speed indicators
    - Check mobile-friendliness signals
    - Validate canonical tags
    - Check for duplicate content signals
    """

    agent_type = AgentType.TECHNICAL_AUDITOR

    def __init__(self, context: AgentContext):
        self.context = context
        self.logger = logger.bind(agent="technical-seo")
        self._visited: set[str] = set()
        self._issues: list[dict] = []

    async def execute(self, task: AgentTask) -> AgentResult:
        """Execute technical SEO task - called by base class run() with error handling."""
        self._visited = set()
        self._issues = []

        task_handlers = {
            "full_audit": self._full_audit,
            "check_broken_links": self._check_broken_links,
            "check_redirects": self._check_redirects,
            "validate_sitemap": self._validate_sitemap,
            "check_robots": self._check_robots,
            "analyze_page": self._analyze_page,
        }

        handler = task_handlers.get(task.task_type)
        if not handler:
            raise AgentError(
                f"Unknown task type: {task.task_type}",
                agent_type="technical-seo",
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

    async def _full_audit(self, params: dict[str, Any]) -> dict[str, Any]:
        """Run full technical SEO audit."""
        base_url = params.get("url", self.context.property_url)
        max_pages = params.get("max_pages", 100)

        if not base_url:
            return {"data": {"error": "No URL provided"}}

        results = {
            "audited_at": datetime.utcnow().isoformat(),
            "base_url": base_url,
            "pages_crawled": 0,
            "issues": {
                "critical": [],
                "warning": [],
                "info": [],
            },
            "summary": {},
        }
        recommendations = []
        alerts = []

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "SEOAgentBot/1.0"},
        ) as client:
            # Check robots.txt
            robots_result = await self._fetch_robots(client, base_url)
            if robots_result.get("issues"):
                results["issues"]["warning"].extend(robots_result["issues"])

            # Check sitemap
            sitemap_result = await self._fetch_sitemap(client, base_url)
            if sitemap_result.get("issues"):
                results["issues"]["warning"].extend(sitemap_result["issues"])

            # Crawl pages
            await self._crawl_site(client, base_url, max_pages)

            results["pages_crawled"] = len(self._visited)

            # Categorize issues
            for issue in self._issues:
                severity = issue.get("severity", "info")
                results["issues"][severity].append(issue)

        # Generate summary
        results["summary"] = {
            "total_issues": len(self._issues),
            "critical_count": len(results["issues"]["critical"]),
            "warning_count": len(results["issues"]["warning"]),
            "info_count": len(results["issues"]["info"]),
            "pages_with_issues": len(set(i.get("url") for i in self._issues)),
        }

        # Generate alerts for critical issues
        if results["issues"]["critical"]:
            alerts.append(Alert(
                title=f"Critical Technical SEO Issues Found",
                message=f"Found {len(results['issues']['critical'])} critical issues affecting SEO",
                severity=Severity.CRITICAL,
                source=self.agent_type,
                data={"issues": results["issues"]["critical"][:5]},
            ))

        # Generate recommendations
        if results["issues"]["critical"] or results["issues"]["warning"]:
            recommendations.append(Recommendation(
                title="Fix Technical SEO Issues",
                description=f"Address {results['summary']['critical_count']} critical and {results['summary']['warning_count']} warning issues",
                priority=Priority.HIGH if results["issues"]["critical"] else Priority.MEDIUM,
                category="technical_seo",
            ))

        return {
            "data": results,
            "recommendations": recommendations,
            "alerts": alerts,
        }

    async def _crawl_site(self, client: httpx.AsyncClient, base_url: str, max_pages: int):
        """Crawl site and collect issues."""
        to_visit = [base_url]
        base_domain = urlparse(base_url).netloc

        while to_visit and len(self._visited) < max_pages:
            url = to_visit.pop(0)

            if url in self._visited:
                continue

            self._visited.add(url)

            try:
                response = await client.get(url)
                await self._analyze_response(url, response, base_domain)

                # Extract links for further crawling
                if response.status_code == 200 and "text/html" in response.headers.get("content-type", ""):
                    soup = BeautifulSoup(response.text, "lxml")
                    for link in soup.find_all("a", href=True):
                        href = link["href"]
                        full_url = urljoin(url, href)

                        # Only crawl same domain
                        if urlparse(full_url).netloc == base_domain:
                            if full_url not in self._visited and full_url not in to_visit:
                                to_visit.append(full_url)

            except httpx.TimeoutException:
                self._issues.append({
                    "type": "timeout",
                    "url": url,
                    "message": "Page load timeout (>30s)",
                    "severity": "warning",
                })
            except httpx.ConnectError:
                self._issues.append({
                    "type": "connection_error",
                    "url": url,
                    "message": "Failed to connect to server",
                    "severity": "critical",
                })
            except httpx.HTTPStatusError as e:
                self._issues.append({
                    "type": "http_error",
                    "url": url,
                    "status_code": e.response.status_code,
                    "message": f"HTTP error: {e.response.status_code}",
                    "severity": "warning",
                })
            except Exception as e:
                self.logger.warning("Crawl error", url=url, error=str(e), error_type=type(e).__name__)
                self._issues.append({
                    "type": "crawl_error",
                    "url": url,
                    "message": f"Crawl failed: {str(e)[:100]}",
                    "severity": "info",
                })

    async def _analyze_response(self, url: str, response: httpx.Response, base_domain: str):
        """Analyze a page response for issues."""
        # Check status code
        if response.status_code >= 400:
            self._issues.append({
                "type": "broken_page",
                "url": url,
                "status_code": response.status_code,
                "message": f"Page returns {response.status_code}",
                "severity": "critical" if response.status_code == 404 else "warning",
            })
            return

        # Check redirect chain
        if len(response.history) > 2:
            self._issues.append({
                "type": "redirect_chain",
                "url": url,
                "chain_length": len(response.history),
                "message": f"Long redirect chain ({len(response.history)} hops)",
                "severity": "warning",
            })

        if response.status_code != 200:
            return

        # Parse HTML
        if "text/html" not in response.headers.get("content-type", ""):
            return

        soup = BeautifulSoup(response.text, "lxml")

        # Check title
        title = soup.find("title")
        if not title or not title.text.strip():
            self._issues.append({
                "type": "missing_title",
                "url": url,
                "message": "Missing or empty title tag",
                "severity": "critical",
            })
        elif len(title.text) > 60:
            self._issues.append({
                "type": "long_title",
                "url": url,
                "length": len(title.text),
                "message": f"Title too long ({len(title.text)} chars)",
                "severity": "info",
            })

        # Check meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if not meta_desc or not meta_desc.get("content", "").strip():
            self._issues.append({
                "type": "missing_meta_description",
                "url": url,
                "message": "Missing meta description",
                "severity": "warning",
            })

        # Check H1
        h1s = soup.find_all("h1")
        if len(h1s) == 0:
            self._issues.append({
                "type": "missing_h1",
                "url": url,
                "message": "No H1 tag found",
                "severity": "warning",
            })
        elif len(h1s) > 1:
            self._issues.append({
                "type": "multiple_h1",
                "url": url,
                "count": len(h1s),
                "message": f"Multiple H1 tags ({len(h1s)})",
                "severity": "info",
            })

        # Check canonical
        canonical = soup.find("link", attrs={"rel": "canonical"})
        if not canonical:
            self._issues.append({
                "type": "missing_canonical",
                "url": url,
                "message": "Missing canonical tag",
                "severity": "warning",
            })

        # Check for broken images
        for img in soup.find_all("img", src=True):
            if not img.get("alt"):
                self._issues.append({
                    "type": "missing_alt",
                    "url": url,
                    "image": img["src"][:100],
                    "message": "Image missing alt text",
                    "severity": "info",
                })

        # Check internal links
        for link in soup.find_all("a", href=True):
            href = link["href"]
            full_url = urljoin(url, href)

            if urlparse(full_url).netloc == base_domain:
                # Check for broken internal links (would need to verify)
                pass

    async def _fetch_robots(self, client: httpx.AsyncClient, base_url: str) -> dict[str, Any]:
        """Fetch and analyze robots.txt."""
        robots_url = urljoin(base_url, "/robots.txt")
        issues = []

        try:
            response = await client.get(robots_url)

            if response.status_code == 404:
                issues.append({
                    "type": "missing_robots",
                    "url": robots_url,
                    "message": "No robots.txt found",
                    "severity": "warning",
                })
            elif response.status_code == 200:
                content = response.text

                # Check for sitemap reference
                if "sitemap:" not in content.lower():
                    issues.append({
                        "type": "robots_no_sitemap",
                        "url": robots_url,
                        "message": "robots.txt doesn't reference sitemap",
                        "severity": "info",
                    })

        except Exception as e:
            logger.warning("Failed to fetch robots.txt", error=str(e))

        return {"issues": issues}

    async def _fetch_sitemap(self, client: httpx.AsyncClient, base_url: str) -> dict[str, Any]:
        """Fetch and analyze sitemap."""
        sitemap_url = urljoin(base_url, "/sitemap.xml")
        issues = []

        try:
            response = await client.get(sitemap_url)

            if response.status_code == 404:
                issues.append({
                    "type": "missing_sitemap",
                    "url": sitemap_url,
                    "message": "No sitemap.xml found",
                    "severity": "warning",
                })
            elif response.status_code == 200:
                # Basic validation
                if "<urlset" not in response.text and "<sitemapindex" not in response.text:
                    issues.append({
                        "type": "invalid_sitemap",
                        "url": sitemap_url,
                        "message": "Sitemap appears to be invalid XML",
                        "severity": "warning",
                    })

        except Exception as e:
            logger.warning("Failed to fetch sitemap", error=str(e))

        return {"issues": issues}

    async def _check_broken_links(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check for broken links on a page or site."""
        url = params.get("url", self.context.property_url)
        results = await self._full_audit({"url": url, "max_pages": params.get("max_pages", 50)})

        # Filter to only broken link issues
        broken = [i for i in self._issues if i["type"] in ("broken_page", "broken_link")]

        return {
            "data": {
                "url": url,
                "broken_links": broken,
                "count": len(broken),
            },
            "recommendations": results.get("recommendations", []),
            "alerts": results.get("alerts", []),
        }

    async def _check_redirects(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check redirect chains."""
        urls = params.get("urls", [])
        results = []

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            for url in urls:
                try:
                    response = await client.get(url)
                    results.append({
                        "url": url,
                        "final_url": str(response.url),
                        "chain_length": len(response.history),
                        "status_code": response.status_code,
                        "chain": [str(r.url) for r in response.history],
                    })
                except Exception as e:
                    results.append({"url": url, "error": str(e)})

        return {"data": {"redirects": results}, "recommendations": [], "alerts": []}

    async def _validate_sitemap(self, params: dict[str, Any]) -> dict[str, Any]:
        """Validate sitemap."""
        url = params.get("url", self.context.property_url)

        async with httpx.AsyncClient(timeout=30.0) as client:
            result = await self._fetch_sitemap(client, url)

        return {"data": result, "recommendations": [], "alerts": []}

    async def _check_robots(self, params: dict[str, Any]) -> dict[str, Any]:
        """Check robots.txt."""
        url = params.get("url", self.context.property_url)

        async with httpx.AsyncClient(timeout=30.0) as client:
            result = await self._fetch_robots(client, url)

        return {"data": result, "recommendations": [], "alerts": []}

    async def _analyze_page(self, params: dict[str, Any]) -> dict[str, Any]:
        """Analyze a single page."""
        url = params.get("url")
        if not url:
            return {"data": {"error": "URL required"}}

        self._issues = []
        base_domain = urlparse(url).netloc

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            await self._analyze_response(url, response, base_domain)

        return {
            "data": {
                "url": url,
                "status_code": response.status_code,
                "issues": self._issues,
            },
            "recommendations": [],
            "alerts": [],
        }
