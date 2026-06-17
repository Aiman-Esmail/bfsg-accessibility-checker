"""
scanner.py
Kern-Scanner-Modul fuer den BFSG Accessibility Checker.

Laedt eine Webseite per Playwright (echter Chromium-Browser), injiziert die
axe-core Bibliothek und fuehrt einen WCAG 2.1 AA Scan durch.

Verwendung:
    from scanner import scan_url
    result = scan_url("https://example.com")
"""

import json
import os
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

# Pfad zur lokal installierten axe-core Bibliothek (via npm install axe-core)
AXE_CORE_PATH = os.path.join(
    os.path.dirname(__file__), "node_modules", "axe-core", "axe.min.js"
)

# Mapping der axe-core "impact" Stufen auf deutsche Bezeichnungen
IMPACT_LABELS_DE = {
    "critical": "Kritisch",
    "serious": "Schwerwiegend",
    "moderate": "Mittel",
    "minor": "Gering",
}


def _load_axe_script() -> str:
    """Liest den Inhalt der lokalen axe.min.js Datei ein."""
    if not os.path.exists(AXE_CORE_PATH):
        raise FileNotFoundError(
            f"axe-core wurde nicht gefunden unter {AXE_CORE_PATH}. "
            "Bitte 'npm install axe-core' im Projektverzeichnis ausfuehren."
        )
    with open(AXE_CORE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def scan_url(url: str, timeout_ms: int = 30000, wcag_tags: list[str] | None = None) -> dict:
    """
    Scannt eine URL mit axe-core und gibt ein strukturiertes Ergebnis zurueck.

    Args:
        url: Die zu scannende Webseiten-URL (z.B. "https://example.com")
        timeout_ms: Timeout fuer das Laden der Seite in Millisekunden
        wcag_tags: Optionale Liste von axe-core Tags zur Einschraenkung des Scans,
                   z.B. ["wcag2a", "wcag2aa", "wcag21aa"]. Standard: WCAG 2.1 AA Set.

    Returns:
        dict mit Keys: url, scanned_at, violations, passes_count,
        incomplete_count, summary (Zaehlung nach Schweregrad)
    """
    if wcag_tags is None:
        wcag_tags = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]

    axe_script = _load_axe_script()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        try:
            page.goto(url, timeout=timeout_ms, wait_until="networkidle")
        except Exception as e:
            browser.close()
            return {
                "url": url,
                "scanned_at": datetime.now(timezone.utc).isoformat(),
                "error": f"Seite konnte nicht geladen werden: {str(e)}",
                "violations": [],
                "summary": {},
            }

        # axe-core per Runtime-Evaluate injizieren (umgeht strikte CSP script-src
        # Regeln, die add_script_tag auf vielen Produktionsseiten blockieren wuerden,
        # z.B. github.com). Das ist dieselbe Technik, die Lighthouse/axe-cli nutzen.
        page.evaluate(axe_script)

        # axe.run() ausfuehren, eingeschraenkt auf die gewuenschten WCAG-Tags
        raw_result = page.evaluate(
            """async (tags) => {
                return await axe.run(document, { runOnly: { type: 'tag', values: tags } });
            }""",
            wcag_tags,
        )

        browser.close()

    violations = raw_result.get("violations", [])

    # Zusammenfassung nach Schweregrad zaehlen
    summary = {label: 0 for label in IMPACT_LABELS_DE.values()}
    for v in violations:
        impact = v.get("impact", "minor")
        label = IMPACT_LABELS_DE.get(impact, "Gering")
        summary[label] = summary.get(label, 0) + len(v.get("nodes", []))

    # Vereinfachte, fuer die naechste Verarbeitungsstufe (KI-Erklaerung) optimierte Struktur
    simplified_violations = []
    for v in violations:
        simplified_violations.append({
            "id": v.get("id"),
            "impact": v.get("impact"),
            "impact_de": IMPACT_LABELS_DE.get(v.get("impact"), "Gering"),
            "description": v.get("description"),
            "help": v.get("help"),
            "help_url": v.get("helpUrl"),
            "affected_elements_count": len(v.get("nodes", [])),
            "example_html": v.get("nodes", [{}])[0].get("html", "") if v.get("nodes") else "",
        })

    return {
        "url": url,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "violations": simplified_violations,
        "violations_count": len(simplified_violations),
        "passes_count": len(raw_result.get("passes", [])),
        "incomplete_count": len(raw_result.get("incomplete", [])),
        "summary": summary,
    }


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/test_page.html"
    result = scan_url(target)
    print(json.dumps(result, indent=2, ensure_ascii=False))
