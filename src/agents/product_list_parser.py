"""
Product List Parser Agent

Parses product lists from various formats (Excel, CSV, email text) and:
- Extracts product information
- Suggests category mappings
- Prepares data for CMS import
- Validates against existing product catalog

Designed to reduce manual work when Emma Falk sends product lists.
"""

import re
import csv
import io
from typing import Any
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class ParsedProduct:
    """A product extracted from a list."""
    name: str
    sku: str | None
    ean: str | None
    brand: str | None
    category_suggestion: str | None
    price: float | None
    attributes: dict[str, Any]


# Category mapping based on common product patterns
CATEGORY_PATTERNS = {
    "Receptfria läkemedel": [
        r"(alvedon|ipren|treo|panodil|voltaren|nasonex)",
        r"(tablett|kapsel|brustablett|oral lösning)",
        r"(smärtstillande|febernedsättande|antiinflammatorisk)",
    ],
    "Hudvård": [
        r"(kräm|lotion|salva|gel|serum)",
        r"(ansikt|kropp|händer|fötter)",
        r"(återfuktande|renande|vårdande)",
        r"(cerave|la roche|eucerin|aco)",
    ],
    "Hårvård": [
        r"(schampo|balsam|hårinpackning|hårolja)",
        r"(torrschampo|färgschampo)",
    ],
    "Kosttillskott": [
        r"(vitamin|mineral|omega|probiotika)",
        r"(d-vitamin|b-vitamin|c-vitamin|zink|magnesium)",
        r"(kosttillskott|supplement)",
    ],
    "Munvård": [
        r"(tandkräm|tandborste|tandtråd|munskölj)",
        r"(sensodyne|colgate|oral-b|zendium)",
    ],
    "Barn & Baby": [
        r"(barn|baby|spädbarn|blöj)",
        r"(barnmat|välling|ersättning)",
        r"(pampers|libero)",
    ],
    "Intim": [
        r"(intim|mens|tampong|binda)",
        r"(libresse|always|ob)",
    ],
    "Solskydd": [
        r"(solskydd|spf|solkräm|after sun)",
        r"(sollotion|solspray)",
    ],
    "Makeup": [
        r"(mascara|läppstift|foundation|concealer|puder)",
        r"(ögonskugga|eyeliner|rouge|bronzer)",
        r"(isadora|max factor|maybelline|lumene)",
    ],
    "Doft": [
        r"(parfym|eau de|doft|body mist)",
        r"(deodorant|antiperspirant|roll-on)",
    ],
}


class ProductListParserAgent:
    """
    Agent that parses product lists and prepares them for CMS import.

    Capabilities:
    1. Parse CSV/Excel product lists
    2. Extract structured product data
    3. Suggest category mappings
    4. Validate product data
    5. Generate import-ready format
    """

    def __init__(self):
        pass

    async def parse_csv(self, csv_content: str) -> dict[str, Any]:
        """
        Parse a CSV product list.

        Expected columns (flexible matching):
        - Product name / Produktnamn / Namn
        - SKU / Artikelnummer / Art.nr
        - EAN / Streckkod
        - Brand / Varumärke
        - Price / Pris
        """
        products = []
        errors = []

        try:
            # Try to detect delimiter
            dialect = csv.Sniffer().sniff(csv_content[:1024])
            reader = csv.DictReader(io.StringIO(csv_content), dialect=dialect)
        except csv.Error:
            # Fall back to standard CSV
            reader = csv.DictReader(io.StringIO(csv_content))

        # Column name mappings (Swedish and English)
        name_cols = ["name", "namn", "produktnamn", "product name", "product", "produkt"]
        sku_cols = ["sku", "artikelnummer", "art.nr", "artnr", "article number"]
        ean_cols = ["ean", "streckkod", "barcode", "gtin"]
        brand_cols = ["brand", "varumärke", "märke", "manufacturer"]
        price_cols = ["price", "pris", "price_sek", "pris_sek"]

        def find_column(row: dict, candidates: list[str]) -> str | None:
            row_lower = {k.lower().strip(): v for k, v in row.items()}
            for col in candidates:
                if col in row_lower:
                    return row_lower[col]
            return None

        for i, row in enumerate(reader):
            try:
                name = find_column(row, name_cols)
                if not name:
                    errors.append(f"Rad {i+1}: Kunde inte hitta produktnamn")
                    continue

                product = ParsedProduct(
                    name=name.strip(),
                    sku=find_column(row, sku_cols),
                    ean=find_column(row, ean_cols),
                    brand=find_column(row, brand_cols),
                    category_suggestion=self._suggest_category(name),
                    price=self._parse_price(find_column(row, price_cols)),
                    attributes={k: v for k, v in row.items() if v},
                )
                products.append(product)

            except Exception as e:
                errors.append(f"Rad {i+1}: {str(e)}")

        # Group by suggested category
        by_category = {}
        for product in products:
            cat = product.category_suggestion or "Okategoriserad"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append({
                "name": product.name,
                "sku": product.sku,
                "ean": product.ean,
                "brand": product.brand,
                "price": product.price,
            })

        return {
            "total_products": len(products),
            "products": [
                {
                    "name": p.name,
                    "sku": p.sku,
                    "ean": p.ean,
                    "brand": p.brand,
                    "category_suggestion": p.category_suggestion,
                    "price": p.price,
                }
                for p in products
            ],
            "by_category": by_category,
            "errors": errors,
            "summary": self._generate_summary(products, errors),
        }

    async def parse_email_text(self, email_text: str) -> dict[str, Any]:
        """
        Parse product information from email text.

        Handles common formats like:
        - Bullet lists
        - Numbered lists
        - Product tables in plain text
        """
        products = []
        lines = email_text.strip().split("\n")

        # Patterns for extracting product info
        ean_pattern = r"\b(\d{13}|\d{8})\b"  # EAN-13 or EAN-8
        sku_pattern = r"\b([A-Z]{2,3}[-]?\d{4,8})\b"  # Common SKU patterns
        price_pattern = r"(\d+[,.]?\d*)\s*(kr|sek|:-)"

        for line in lines:
            line = line.strip()

            # Skip empty lines and headers
            if not line or len(line) < 3:
                continue
            if any(header in line.lower() for header in ["produktlista", "produkt:", "---", "==="]):
                continue

            # Remove bullet points and numbers
            cleaned = re.sub(r"^[\d\.\-\*\•]\s*", "", line)
            if not cleaned:
                continue

            # Extract EAN if present
            ean_match = re.search(ean_pattern, line)
            ean = ean_match.group(1) if ean_match else None

            # Extract SKU if present
            sku_match = re.search(sku_pattern, line)
            sku = sku_match.group(1) if sku_match else None

            # Extract price if present
            price_match = re.search(price_pattern, line, re.IGNORECASE)
            price = self._parse_price(price_match.group(1)) if price_match else None

            # Clean the product name (remove extracted parts)
            name = cleaned
            if ean:
                name = name.replace(ean, "")
            if sku:
                name = name.replace(sku, "")
            if price_match:
                name = name.replace(price_match.group(0), "")

            # Clean up remaining noise
            name = re.sub(r"\s+", " ", name).strip(" -,;:")

            if len(name) > 2:
                products.append(ParsedProduct(
                    name=name,
                    sku=sku,
                    ean=ean,
                    brand=self._detect_brand(name),
                    category_suggestion=self._suggest_category(name),
                    price=price,
                    attributes={},
                ))

        # Group by suggested category
        by_category = {}
        for product in products:
            cat = product.category_suggestion or "Okategoriserad"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append({
                "name": product.name,
                "sku": product.sku,
                "ean": product.ean,
                "brand": product.brand,
            })

        return {
            "total_products": len(products),
            "products": [
                {
                    "name": p.name,
                    "sku": p.sku,
                    "ean": p.ean,
                    "brand": p.brand,
                    "category_suggestion": p.category_suggestion,
                    "price": p.price,
                }
                for p in products
            ],
            "by_category": by_category,
            "summary": self._generate_summary(products, []),
        }

    def _suggest_category(self, product_name: str) -> str | None:
        """Suggest a category based on product name."""
        name_lower = product_name.lower()

        for category, patterns in CATEGORY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, name_lower, re.IGNORECASE):
                    return category

        return None

    def _detect_brand(self, product_name: str) -> str | None:
        """Detect brand from product name."""
        known_brands = [
            "CeraVe", "La Roche-Posay", "Eucerin", "ACO", "Decubal",
            "Vichy", "Bioderma", "Avène", "Clinique", "Neutrogena",
            "L'Oréal", "Maybelline", "Max Factor", "IsaDora", "Lumene",
            "Sensodyne", "Colgate", "Oral-B", "Zendium", "Parodontax",
            "Pampers", "Libero", "Libresse", "Always", "OB",
            "Voltaren", "Alvedon", "Ipren", "Nasonex", "Nicorette",
        ]

        name_lower = product_name.lower()
        for brand in known_brands:
            if brand.lower() in name_lower:
                return brand

        return None

    def _parse_price(self, price_str: str | None) -> float | None:
        """Parse price string to float."""
        if not price_str:
            return None

        try:
            # Remove everything except digits and decimal separators
            cleaned = re.sub(r"[^\d,.]", "", price_str)
            # Handle Swedish decimal comma
            cleaned = cleaned.replace(",", ".")
            return float(cleaned)
        except ValueError:
            return None

    def _generate_summary(
        self,
        products: list[ParsedProduct],
        errors: list[str]
    ) -> str:
        """Generate a summary of parsed products."""
        if not products:
            return "Inga produkter kunde hittas i listan."

        # Count by category
        categories = {}
        for p in products:
            cat = p.category_suggestion or "Okategoriserad"
            categories[cat] = categories.get(cat, 0) + 1

        # Count with/without EAN
        with_ean = sum(1 for p in products if p.ean)

        summary = f"✅ Hittade {len(products)} produkter.\n\n"
        summary += "**Per kategori:**\n"
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            summary += f"- {cat}: {count} produkter\n"

        summary += f"\n**Produktdata:**\n"
        summary += f"- Med EAN-kod: {with_ean}/{len(products)}\n"
        summary += f"- Med varumärke: {sum(1 for p in products if p.brand)}/{len(products)}\n"

        if errors:
            summary += f"\n⚠️ {len(errors)} rader kunde inte tolkas."

        return summary

    async def generate_import_format(
        self,
        products: list[dict[str, Any]],
        format_type: str = "optimizely"
    ) -> dict[str, Any]:
        """
        Generate CMS import-ready format.

        Formats:
        - optimizely: Optimizely Commerce format
        - generic: Generic CSV format
        """
        if format_type == "optimizely":
            return self._format_for_optimizely(products)
        else:
            return self._format_generic(products)

    def _format_for_optimizely(
        self,
        products: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Format products for Optimizely Commerce import."""
        rows = []
        for p in products:
            rows.append({
                "Code": p.get("sku") or "",
                "Name": p.get("name", ""),
                "DisplayName": p.get("name", ""),
                "Brand": p.get("brand") or "",
                "GTIN": p.get("ean") or "",
                "DefaultCategory": p.get("category_suggestion") or "",
                "ListPrice": p.get("price") or "",
                "IsActive": "True",
            })

        # Generate CSV
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        return {
            "format": "optimizely",
            "row_count": len(rows),
            "csv_content": output.getvalue(),
            "columns": list(rows[0].keys()) if rows else [],
        }

    def _format_generic(
        self,
        products: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Format products as generic CSV."""
        rows = []
        for p in products:
            rows.append({
                "Produktnamn": p.get("name", ""),
                "Artikelnummer": p.get("sku") or "",
                "EAN": p.get("ean") or "",
                "Varumärke": p.get("brand") or "",
                "Kategori": p.get("category_suggestion") or "",
                "Pris": p.get("price") or "",
            })

        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        return {
            "format": "generic",
            "row_count": len(rows),
            "csv_content": output.getvalue(),
            "columns": list(rows[0].keys()) if rows else [],
        }

    async def validate_products(
        self,
        products: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Validate product data for completeness and issues.

        Checks:
        - Missing required fields
        - Invalid EAN codes
        - Duplicate entries
        - Category suggestions
        """
        issues = []
        warnings = []

        # Check for duplicates
        seen_names = {}
        seen_eans = {}

        for i, p in enumerate(products):
            name = p.get("name", "")
            ean = p.get("ean")

            # Check required fields
            if not name:
                issues.append(f"Produkt {i+1}: Saknar produktnamn")

            # Check for duplicates
            if name in seen_names:
                warnings.append(f"Duplicerat namn: '{name}' (rad {seen_names[name]+1} och {i+1})")
            seen_names[name] = i

            if ean:
                if ean in seen_eans:
                    issues.append(f"Duplicerad EAN: {ean} (rad {seen_eans[ean]+1} och {i+1})")
                seen_eans[ean] = i

                # Validate EAN format
                if not self._validate_ean(ean):
                    warnings.append(f"Ogiltig EAN-kod: {ean} för '{name}'")

            # Check category
            if not p.get("category_suggestion"):
                warnings.append(f"Ingen kategorimatchning för: '{name}'")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "summary": f"{'✅ Validering OK' if len(issues) == 0 else '❌ Validering misslyckades'} | "
                       f"{len(issues)} fel, {len(warnings)} varningar",
        }

    def _validate_ean(self, ean: str) -> bool:
        """Validate EAN-8 or EAN-13 checksum."""
        if not ean or not ean.isdigit():
            return False

        if len(ean) not in [8, 13]:
            return False

        # Calculate checksum
        digits = [int(d) for d in ean]
        if len(ean) == 13:
            checksum = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:-1]))
            check_digit = (10 - (checksum % 10)) % 10
            return check_digit == digits[-1]
        elif len(ean) == 8:
            checksum = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(digits[:-1]))
            check_digit = (10 - (checksum % 10)) % 10
            return check_digit == digits[-1]

        return False
