# Dockerfile fuer HuggingFace Spaces (Docker SDK)
# Wird benoetigt, weil diese App einen echten Chromium-Browser (Playwright)
# serverseitig ausfuehrt - das unterstuetzt der normale "Streamlit SDK" Space nicht.

FROM python:3.12-slim

# Gemeinsamer Browser-Pfad, unabhaengig vom ausfuehrenden User (wichtig fuer
# den User-Wechsel weiter unten - sonst findet der nicht-root User den
# Chromium-Browser nicht, der waehrend des Builds als root installiert wird)
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Python-Abhaengigkeiten installieren (muss als root passieren, da
# "playwright install --with-deps" Systempakete per apt-get nachinstalliert)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Chromium-Browser + alle benoetigten Systembibliotheken installieren
RUN playwright install --with-deps chromium

# HuggingFace Spaces fuehrt Container mit User-ID 1000 aus.
# Eigenen User anlegen, um Berechtigungsproblemen vorzubeugen.
RUN useradd -m -u 1000 user && \
    chown -R user:user /ms-playwright

# App-Code mit korrektem Besitzer kopieren
COPY --chown=user . .

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# HuggingFace Spaces (Docker SDK) erwartet Port 7860
EXPOSE 7860

CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0", "--server.headless=true"]
