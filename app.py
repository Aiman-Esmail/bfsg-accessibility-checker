"""
app.py
Streamlit-Oberflaeche fuer den BFSG Accessibility Checker.

Verbindet scanner.py, ai_report.py und pdf_report.py zu einer
benutzerfreundlichen Web-Anwendung: URL eingeben -> scannen ->
Ergebnisse ansehen -> PDF-Bericht herunterladen.
"""

import os
import tempfile
import streamlit as st

from scanner import scan_url
from ai_report import generate_report
from pdf_report import create_pdf_report

st.set_page_config(
    page_title="BFSG Barrierefreiheits-Checker", page_icon="\u267f", layout="centered"
)

st.title("BFSG Barrierefreiheits-Checker")
st.write(
    "Pruefen Sie automatisiert, ob Ihre Webseite die Anforderungen des "
    "Barrierefreiheitsstaerkungsgesetzes (BFSG) erfuellt, und erhalten Sie "
    "einen priorisierten Massnahmenplan auf Deutsch."
)

url = st.text_input("Webseiten-URL", placeholder="https://www.ihre-webseite.de")
scan_clicked = st.button("Webseite scannen", type="primary")

if scan_clicked:
    if not url.strip():
        st.error("Bitte geben Sie eine gueltige URL ein.")
    elif not os.environ.get("ANTHROPIC_API_KEY"):
        st.error(
            "ANTHROPIC_API_KEY ist nicht konfiguriert. Bitte in den "
            "Space-Einstellungen unter 'Variables and secrets' hinterlegen."
        )
    else:
        target_url = url.strip()
        if not target_url.startswith(("http://", "https://")):
            target_url = "https://" + target_url

        with st.spinner("Webseite wird gescannt..."):
            scan_result = scan_url(target_url)

        if scan_result.get("error"):
            st.error(f"Fehler beim Scannen: {scan_result['error']}")
            st.session_state.pop("ai_report", None)
        else:
            with st.spinner("KI erstellt priorisierten Bericht..."):
                ai = generate_report(scan_result)

            with st.spinner("PDF-Bericht wird erstellt..."):
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    create_pdf_report(scan_result, ai, tmp.name)
                    with open(tmp.name, "rb") as f:
                        pdf_bytes = f.read()

            st.session_state["scan_result"] = scan_result
            st.session_state["ai_report"] = ai
            st.session_state["pdf_bytes"] = pdf_bytes

if "ai_report" in st.session_state:
    scan_result = st.session_state["scan_result"]
    ai = st.session_state["ai_report"]

    risk = ai.get("risk_level", "Unbekannt")
    risk_icons = {"Hoch": "\U0001F534", "Mittel": "\U0001F7E0", "Niedrig": "\U0001F7E2", "Unbekannt": "\u26AA"}
    st.subheader(f"{risk_icons.get(risk, '')} Risikostufe: {risk}")

    st.write(ai.get("executive_summary", ""))
    if ai.get("estimated_effort"):
        st.caption(f"Geschaetzter Aufwand: {ai['estimated_effort']}")

    summary = scan_result.get("summary", {})
    cols = st.columns(4)
    for col, level in zip(cols, ["Kritisch", "Schwerwiegend", "Mittel", "Gering"]):
        col.metric(level, summary.get(level, 0))

    issues = ai.get("issues", [])
    if issues:
        st.subheader("Detaillierte Befunde")
        for issue in issues:
            header = f"{issue.get('priority', '-')}. {issue.get('title_de', issue.get('id', ''))}"
            with st.expander(header):
                st.write(issue.get("why_it_matters_de", ""))
                st.info(f"**Empfohlene Massnahme:** {issue.get('fix_suggestion_de', '')}")

    if "pdf_bytes" in st.session_state:
        st.download_button(
            "\U0001F4C4 PDF-Bericht herunterladen",
            data=st.session_state["pdf_bytes"],
            file_name="barrierefreiheits_bericht.pdf",
            mime="application/pdf",
        )

    st.caption(
        "Hinweis: Dieser Bericht basiert auf einem automatisierten technischen Scan "
        "und stellt keine rechtliche Bestaetigung der vollstaendigen BFSG-Konformitaet dar."
    )
