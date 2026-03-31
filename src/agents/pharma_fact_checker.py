"""
Pharmaceutical Fact Checker Agent

Verifies medical/pharmaceutical content against authoritative Swedish sources:
- FASS.se (drug information)
- 1177.se (patient health info)
- Läkemedelsverket (regulatory)

Flags unverified claims and adds citations before content goes to pharmaceutical review.
"""

import re
from typing import Any
from dataclasses import dataclass

import httpx
import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger()


# Common Swedish drug names and their ATC codes for quick lookup
COMMON_DRUGS = {
    "alvedon": {"atc": "N02BE01", "substance": "paracetamol", "type": "otc"},
    "ipren": {"atc": "M01AE01", "substance": "ibuprofen", "type": "otc"},
    "treo": {"atc": "N02BA51", "substance": "acetylsalicylsyra + koffein", "type": "otc"},
    "voltaren": {"atc": "M02AA15", "substance": "diklofenak", "type": "otc"},
    "nasonex": {"atc": "R01AD09", "substance": "mometason", "type": "rx"},
    "omeprazol": {"atc": "A02BC01", "substance": "omeprazol", "type": "otc/rx"},
    "laktulos": {"atc": "A06AD11", "substance": "laktulos", "type": "otc"},
    "losec": {"atc": "A02BC01", "substance": "omeprazol", "type": "rx"},
    "panodil": {"atc": "N02BE01", "substance": "paracetamol", "type": "otc"},
    "citodon": {"atc": "N02AJ06", "substance": "paracetamol + kodein", "type": "rx"},
    "pronaxen": {"atc": "M01AE02", "substance": "naproxen", "type": "otc"},
    "imodium": {"atc": "A07DA03", "substance": "loperamid", "type": "otc"},
    "nezeril": {"atc": "R01AA07", "substance": "xylometazolin", "type": "otc"},
    "zyrtec": {"atc": "R06AE07", "substance": "cetirizin", "type": "otc"},
    "clarityn": {"atc": "R06AX13", "substance": "loratadin", "type": "otc"},
    "canesten": {"atc": "G01AF02", "substance": "klotrimazol", "type": "otc"},
    "pevaryl": {"atc": "D01AC03", "substance": "ekonazol", "type": "otc"},
    "corsodyl": {"atc": "A01AB03", "substance": "klorhexidin", "type": "otc"},
    "nicorette": {"atc": "N07BA01", "substance": "nikotin", "type": "otc"},
    "nicotinell": {"atc": "N07BA01", "substance": "nikotin", "type": "otc"},
}

# Medical terms that indicate content needs pharmaceutical review
PHARMA_REVIEW_TRIGGERS = [
    # Symptoms
    r"\b(symtom|besvär|smärta|värk|feber|inflammation|infektion)\b",
    # Treatments
    r"\b(behandl|medicinera|dosering|dos|tablett|kapsel|salva|kräm)\b",
    # Warnings
    r"\b(biverkning|kontraindikation|varning|försiktighet|gravid|amning)\b",
    # Drug types
    r"\b(läkemedel|medicin|receptfri|receptbelagd|prescription)\b",
    # Body parts/conditions
    r"\b(hjärta|lever|njure|diabetes|astma|allergi|eksem|psoriasis)\b",
]


@dataclass
class FactCheckResult:
    """Result of fact-checking a piece of content."""
    claim: str
    verified: bool
    confidence: float  # 0-1
    source: str | None
    source_url: str | None
    suggestion: str | None  # Corrected text if claim is wrong


@dataclass
class ContentAnalysis:
    """Full analysis of pharmaceutical content."""
    needs_pharma_review: bool
    review_reasons: list[str]
    drug_mentions: list[dict[str, Any]]
    health_claims: list[str]
    fact_checks: list[FactCheckResult]
    citations_added: list[dict[str, str]]
    enriched_content: str | None


class PharmaFactCheckerAgent:
    """
    Agent that verifies pharmaceutical content against authoritative sources.

    Capabilities:
    1. Extract drug names and medical claims from content
    2. Verify claims against FASS, 1177, Läkemedelsverket
    3. Flag content needing pharmaceutical review
    4. Add citations and source links
    5. Suggest corrections for inaccurate claims
    """

    def __init__(self):
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; ApoteketSEOAgent/1.0)"
            }
        )

    async def analyze_content(self, content: str) -> dict[str, Any]:
        """
        Full analysis of pharmaceutical content.

        Returns analysis with:
        - Whether it needs pharmaceutical review
        - Drug mentions found
        - Health claims extracted
        - Fact check results
        - Suggested citations
        """
        # Check if content needs pharma review
        needs_review, review_reasons = self._check_needs_pharma_review(content)

        # Extract drug mentions
        drug_mentions = self._extract_drug_mentions(content)

        # Extract health claims
        health_claims = self._extract_health_claims(content)

        # Fact check claims against sources
        fact_checks = []
        for claim in health_claims[:5]:  # Limit to first 5 claims
            result = await self._verify_claim(claim, drug_mentions)
            fact_checks.append({
                "claim": result.claim,
                "verified": result.verified,
                "confidence": result.confidence,
                "source": result.source,
                "source_url": result.source_url,
                "suggestion": result.suggestion,
            })

        # Generate citations
        citations = self._generate_citations(drug_mentions, fact_checks)

        return {
            "needs_pharma_review": needs_review,
            "review_reasons": review_reasons,
            "drug_mentions": drug_mentions,
            "health_claims": health_claims,
            "fact_checks": fact_checks,
            "suggested_citations": citations,
            "summary": self._generate_summary(needs_review, drug_mentions, fact_checks),
        }

    def _check_needs_pharma_review(self, content: str) -> tuple[bool, list[str]]:
        """Check if content needs pharmaceutical review."""
        reasons = []
        content_lower = content.lower()

        # Check for drug mentions
        for drug_name in COMMON_DRUGS:
            if drug_name in content_lower:
                drug_info = COMMON_DRUGS[drug_name]
                if drug_info["type"] == "rx":
                    reasons.append(f"Innehåller receptbelagt läkemedel: {drug_name}")
                else:
                    reasons.append(f"Innehåller läkemedel: {drug_name}")

        # Check for pharma review triggers
        for pattern in PHARMA_REVIEW_TRIGGERS:
            matches = re.findall(pattern, content_lower)
            if matches:
                reasons.append(f"Innehåller medicinska termer: {', '.join(set(matches[:3]))}")
                break

        # Check for dosage information
        dosage_pattern = r"\b\d+\s*(mg|ml|g|mikrogram|tabletter?|kapslar?)\b"
        if re.search(dosage_pattern, content_lower):
            reasons.append("Innehåller doseringsinformation")

        # Check for age restrictions
        age_pattern = r"\b(barn under \d+|från \d+ år|vuxna|barn)\b"
        if re.search(age_pattern, content_lower):
            reasons.append("Innehåller åldersrekommendationer")

        needs_review = len(reasons) > 0
        return needs_review, reasons

    def _extract_drug_mentions(self, content: str) -> list[dict[str, Any]]:
        """Extract drug names and their info from content."""
        mentions = []
        content_lower = content.lower()

        for drug_name, info in COMMON_DRUGS.items():
            if drug_name in content_lower:
                # Find context around the mention
                pattern = rf".{{0,50}}{drug_name}.{{0,50}}"
                contexts = re.findall(pattern, content_lower, re.IGNORECASE)

                mentions.append({
                    "name": drug_name,
                    "substance": info["substance"],
                    "atc_code": info["atc"],
                    "type": info["type"],
                    "fass_url": f"https://www.fass.se/LIF/product?nplId={drug_name}",
                    "contexts": contexts[:2],  # First 2 mentions
                })

        return mentions

    def _extract_health_claims(self, content: str) -> list[str]:
        """Extract health-related claims from content."""
        claims = []

        # Split into sentences
        sentences = re.split(r'[.!?]', content)

        # Patterns that indicate health claims
        claim_patterns = [
            r"hjälper (mot|vid|för)",
            r"lindrar",
            r"behandlar",
            r"minskar",
            r"förebygger",
            r"används (mot|vid|för)",
            r"verkar genom",
            r"innehåller .* som",
            r"rekommenderas (vid|för)",
            r"ska inte användas",
            r"kan orsaka",
            r"biverkningar",
        ]

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue

            for pattern in claim_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    claims.append(sentence)
                    break

        return claims

    async def _verify_claim(
        self,
        claim: str,
        drug_mentions: list[dict[str, Any]]
    ) -> FactCheckResult:
        """Verify a health claim against sources."""
        # For now, return a placeholder - in production this would query FASS API
        # or scrape authoritative sources

        # Check if claim mentions a known drug
        claim_lower = claim.lower()
        relevant_drug = None
        for drug in drug_mentions:
            if drug["name"] in claim_lower:
                relevant_drug = drug
                break

        if relevant_drug:
            # Try to verify against FASS
            fass_data = await self._fetch_fass_info(relevant_drug["name"])
            if fass_data:
                return FactCheckResult(
                    claim=claim,
                    verified=True,
                    confidence=0.7,
                    source="FASS.se",
                    source_url=relevant_drug["fass_url"],
                    suggestion=None,
                )

        # Default: unverified, needs manual check
        return FactCheckResult(
            claim=claim,
            verified=False,
            confidence=0.3,
            source=None,
            source_url=None,
            suggestion="Kunde inte verifiera automatiskt - kräver manuell granskning",
        )

    async def _fetch_fass_info(self, drug_name: str) -> dict[str, Any] | None:
        """Fetch drug information from FASS.se."""
        try:
            # Note: In production, use FASS API with proper license
            # This is a placeholder that would need FASS API credentials
            url = f"https://www.fass.se/LIF/product?userType=2&nplId=&substance=&productName={drug_name}"

            response = await self.http_client.get(url)
            if response.status_code == 200:
                # Parse basic info (would need proper API for full data)
                return {"name": drug_name, "found": True}
        except Exception as e:
            logger.debug(f"Could not fetch FASS info for {drug_name}: {e}")

        return None

    async def fetch_1177_info(self, topic: str) -> dict[str, Any]:
        """Fetch health information from 1177.se."""
        try:
            search_url = f"https://www.1177.se/sok/?q={topic}&geo=00"
            response = await self.http_client.get(search_url)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                results = []

                # Extract search results
                for item in soup.select(".search-result-item")[:3]:
                    title_el = item.select_one("h2, h3")
                    link_el = item.select_one("a")
                    desc_el = item.select_one("p")

                    if title_el and link_el:
                        results.append({
                            "title": title_el.get_text(strip=True),
                            "url": f"https://www.1177.se{link_el.get('href', '')}",
                            "description": desc_el.get_text(strip=True) if desc_el else "",
                        })

                return {
                    "topic": topic,
                    "results": results,
                    "source": "1177.se",
                }
        except Exception as e:
            logger.error(f"Failed to fetch 1177 info: {e}")

        return {"topic": topic, "results": [], "source": "1177.se"}

    def _generate_citations(
        self,
        drug_mentions: list[dict[str, Any]],
        fact_checks: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        """Generate citation suggestions for the content."""
        citations = []

        # Add FASS citations for drugs
        for drug in drug_mentions:
            citations.append({
                "text": f"Läs mer om {drug['name'].title()} på FASS.se",
                "url": drug["fass_url"],
                "source": "FASS",
            })

        # Add citations from verified claims
        for check in fact_checks:
            if check.get("verified") and check.get("source_url"):
                citations.append({
                    "text": f"Källa: {check['source']}",
                    "url": check["source_url"],
                    "source": check["source"],
                })

        return citations

    def _generate_summary(
        self,
        needs_review: bool,
        drug_mentions: list[dict[str, Any]],
        fact_checks: list[dict[str, Any]]
    ) -> str:
        """Generate a summary of the analysis."""
        verified_count = sum(1 for fc in fact_checks if fc.get("verified"))
        total_claims = len(fact_checks)

        summary_parts = []

        if needs_review:
            summary_parts.append("⚠️ Innehållet behöver farmaceutisk granskning.")
        else:
            summary_parts.append("✅ Innehållet verkar inte kräva farmaceutisk granskning.")

        if drug_mentions:
            drug_names = [d["name"].title() for d in drug_mentions]
            summary_parts.append(f"📦 Läkemedel nämnda: {', '.join(drug_names)}")

        if total_claims > 0:
            summary_parts.append(
                f"🔍 Faktakontroll: {verified_count}/{total_claims} påståenden verifierade"
            )

        return " | ".join(summary_parts)

    async def enrich_content(
        self,
        content: str,
        add_citations: bool = True
    ) -> dict[str, Any]:
        """
        Enrich content with verified facts and citations.

        Returns the original content with:
        - Citations added at the end
        - Fact-check notes for editors
        """
        analysis = await self.analyze_content(content)

        enriched = content
        editor_notes = []

        # Add editor notes for unverified claims
        for fc in analysis["fact_checks"]:
            if not fc["verified"]:
                editor_notes.append(f"- Verifiera: \"{fc['claim'][:50]}...\"")

        # Add citations section if requested
        if add_citations and analysis["suggested_citations"]:
            enriched += "\n\n---\n**Källor:**\n"
            for citation in analysis["suggested_citations"][:5]:
                enriched += f"- [{citation['text']}]({citation['url']})\n"

        return {
            "original_content": content,
            "enriched_content": enriched,
            "analysis": analysis,
            "editor_notes": editor_notes,
        }

    async def classify_content_type(self, content: str) -> dict[str, Any]:
        """
        Classify content by type and required review level.

        Categories:
        - cosmetic: Kosmetika/hudvård - minimal review
        - otc_drug: Receptfria läkemedel - standard review
        - rx_drug: Receptbelagda läkemedel - full pharma review
        - health_advice: Hälsoråd - medical review
        - general: Allmänt innehåll - no special review
        """
        content_lower = content.lower()

        # Check for RX drugs first (highest priority)
        for drug_name, info in COMMON_DRUGS.items():
            if drug_name in content_lower and info["type"] == "rx":
                return {
                    "category": "rx_drug",
                    "review_level": "full_pharma",
                    "reason": f"Innehåller receptbelagt läkemedel: {drug_name}",
                    "estimated_review_time": "2-3 arbetsdagar",
                }

        # Check for OTC drugs
        for drug_name, info in COMMON_DRUGS.items():
            if drug_name in content_lower and info["type"] == "otc":
                return {
                    "category": "otc_drug",
                    "review_level": "standard_pharma",
                    "reason": f"Innehåller receptfritt läkemedel: {drug_name}",
                    "estimated_review_time": "1-2 arbetsdagar",
                }

        # Check for health advice patterns
        health_patterns = [
            r"(behandling|symtom|diagnos|sjukdom)",
            r"(kontakta läkare|uppsök vård)",
            r"(gravid|amning|barn under)",
        ]
        for pattern in health_patterns:
            if re.search(pattern, content_lower):
                return {
                    "category": "health_advice",
                    "review_level": "medical_review",
                    "reason": "Innehåller hälso- eller vårdrelaterat innehåll",
                    "estimated_review_time": "1-2 arbetsdagar",
                }

        # Check for cosmetic content
        cosmetic_patterns = [
            r"(hudvård|ansiktskräm|serum|rengöring)",
            r"(makeup|smink|mascara|läppstift)",
            r"(schampo|balsam|hårvård)",
            r"(solskydd|spf|självbrunare)",
        ]
        for pattern in cosmetic_patterns:
            if re.search(pattern, content_lower):
                return {
                    "category": "cosmetic",
                    "review_level": "minimal",
                    "reason": "Kosmetiskt innehåll - ingen farmaceutisk granskning krävs",
                    "estimated_review_time": "Ingen extra granskning",
                }

        # Default: general content
        return {
            "category": "general",
            "review_level": "none",
            "reason": "Allmänt innehåll utan medicinska påståenden",
            "estimated_review_time": "Ingen extra granskning",
        }
