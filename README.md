# BFSG Accessibility Checker

AI-powered digital accessibility scanner built for the German market, in response to the **Barrierefreiheitsstärkungsgesetz (BFSG)** that took effect in June 2025. Most small and mid-sized German businesses (e-commerce, service providers) are required to comply but have no easy way to check where they stand.

## How it works

1. **Scan** – `scanner.py` loads a target URL with a real Chromium browser (Playwright) and runs the [axe-core](https://github.com/dequelabs/axe-core) engine against WCAG 2.1 A/AA rules.
2. **Explain** *(in progress)* – Raw violations get translated into plain, prioritized German explanations via the Claude API.
3. **Report** *(planned)* – Results are compiled into a client-ready PDF report.
4. **Deliver** *(planned)* – A simple Streamlit interface for non-technical users (web agencies, SME owners).

## Status

- [x] Core scanner (Playwright + axe-core), validated against a test fixture and a live production site
- [x] AI explanation layer (German output, prioritized by impact)
- [x] PDF report generation (client-ready, validated visually)
- [ ] Streamlit UI + deployment

## Setup

```bash
pip install -r requirements.txt
npm install
playwright install chromium
```

## Usage

```python
from scanner import scan_url

result = scan_url("https://example.com")
print(result["summary"])       # {'Kritisch': 2, 'Schwerwiegend': 3, ...}
print(result["violations"])    # list of detailed findings
```

To get a prioritized German-language report (requires `ANTHROPIC_API_KEY` as an environment variable):

```python
from ai_report import generate_report

report = generate_report(result)
print(report["risk_level"])         # "Hoch" | "Mittel" | "Niedrig"
print(report["executive_summary"])  # plain-German summary
print(report["issues"])             # prioritized, explained issues
```

To generate the final client-ready PDF:

```python
from pdf_report import create_pdf_report

create_pdf_report(result, report, "bericht.pdf")
```

`test_page.html` is a fixture with deliberately broken accessibility (missing alt text, low contrast, unlabeled form elements, etc.) for local testing — serve it with `python -m http.server` and scan `http://localhost:8000/test_page.html`.

## Tech stack

Python · Playwright · axe-core · Claude API · ReportLab (planned) · Streamlit (planned)

## Disclaimer

This tool provides an automated technical scan, not a legal compliance certification. Automated testing catches a meaningful subset of WCAG issues but not all of them — manual review is still recommended for full compliance.
