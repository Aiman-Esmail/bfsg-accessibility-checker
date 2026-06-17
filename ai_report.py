"""
ai_report.py
KI-Erklaerungsschicht fuer den BFSG Accessibility Checker.

Nimmt die rohen axe-core Scan-Ergebnisse aus scanner.py und nutzt die
Claude API, um daraus einen verstaendlichen, priorisierten deutschen
Bericht zu erstellen.

Verwendung:
    from scanner import scan_url
    from ai_report import generate_report

    scan_result = scan_url("https://example.com")
    report = generate_report(scan_result)
"""

import os
import json
import anthropic

MODEL = "claude-sonnet-4-6"
MAX_VIOLATIONS_TO_EXPLAIN = 20  # Kostenschutz bei sehr vielen Verstoessen


def _build_prompt(scan_result: dict) -> str:
    violations = scan_result.get("violations", [])
    impact_order = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
    sorted_violations = sorted(
        violations, key=lambda v: impact_order.get(v.get("impact"), 4)
    )[:MAX_VIOLATIONS_TO_EXPLAIN]

    violations_text = "\n".join(
        f"- ID: {v['id']} | Schweregrad: {v['impact_de']} | "
        f"Betroffene Elemente: {v['affected_elements_count']} | "
        f"Technische Beschreibung: {v['description']} | "
        f"Beispiel-HTML: {v['example_html'][:150]}"
        for v in sorted_violations
    )

    return f"""Du bist ein Experte fuer digitale Barrierefreiheit (WCAG 2.1 AA / BFSG) und erstellst einen Bericht fuer den Inhaber eines kleinen oder mittleren Unternehmens in Deutschland, der KEIN technisches Hintergrundwissen hat.

Hier sind die automatisiert gefundenen Verstoesse fuer die Webseite {scan_result.get('url')}:

{violations_text if violations_text else "Keine Verstoesse gefunden."}

Erstelle daraus einen Bericht. Antworte AUSSCHLIESSLICH mit einem JSON-Objekt (keine Einleitung, kein Markdown, kein Codeblock) mit genau dieser Struktur:

{{
  "risk_level": "Hoch" | "Mittel" | "Niedrig",
  "executive_summary": "2-3 Saetze auf Deutsch: Gesamtbild der Barrierefreiheit dieser Seite, in einfacher Sprache",
  "estimated_effort": "Kurze Einschaetzung des Aufwands zur Behebung",
  "issues": [
    {{
      "id": "axe-core id aus den Daten oben",
      "priority": 1,
      "title_de": "Kurzer, verstaendlicher Titel auf Deutsch",
      "why_it_matters_de": "1-2 Saetze: warum das ein Problem fuer Nutzer mit Behinderung ist",
      "fix_suggestion_de": "1-2 konkrete, umsetzbare Saetze, wie ein Entwickler das beheben kann",
      "affected_elements_count": 1
    }}
  ]
}}

Sortiere "issues" nach Priorität (1 = am dringendsten, zuerst). Schreibe in klarem, professionellem Deutsch ohne Fachjargon, wo es vermeidbar ist."""


def generate_report(scan_result: dict, api_key: str = None) -> dict:
    """
    Erstellt einen priorisierten, deutschsprachigen Erklaerungsbericht
    aus den rohen Scan-Ergebnissen von scanner.scan_url().

    Args:
        scan_result: Das dict, das von scanner.scan_url() zurueckgegeben wird
        api_key: Optionaler Anthropic API-Key. Falls None, wird die
                 Umgebungsvariable ANTHROPIC_API_KEY verwendet.

    Returns:
        dict mit Keys: risk_level, executive_summary, estimated_effort, issues
    """
    if scan_result.get("error"):
        return {
            "risk_level": "Unbekannt",
            "executive_summary": f"Die Seite konnte nicht gescannt werden: {scan_result['error']}",
            "estimated_effort": "",
            "issues": [],
        }

    if not scan_result.get("violations"):
        return {
            "risk_level": "Niedrig",
            "executive_summary": (
                "Bei diesem automatisierten Scan wurden keine Barrierefreiheits-"
                "Verstoesse gefunden. Eine manuelle Pruefung wird trotzdem "
                "empfohlen, da automatisierte Tools nicht alle WCAG-Kriterien "
                "abdecken koennen."
            ),
            "estimated_effort": "Keine Korrekturen notwendig",
            "issues": [],
        }

    client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
    prompt = _build_prompt(scan_result)

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text.strip()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "risk_level": "Unbekannt",
            "executive_summary": "Der KI-Bericht konnte nicht korrekt verarbeitet werden.",
            "estimated_effort": "",
            "issues": [],
            "_raw_response": raw_text,
        }


if __name__ == "__main__":
    import sys
    from scanner import scan_url

    target = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/test_page.html"
    scan = scan_url(target)
    report = generate_report(scan)
    print(json.dumps(report, indent=2, ensure_ascii=False))
