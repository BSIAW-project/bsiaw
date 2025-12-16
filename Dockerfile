FROM python:3.11-slim

# Ustawienia środowiska
ENV PYTHONDONTWRITEBYTECODE=1         PYTHONUNBUFFERED=1         FLASK_ENV=production         PORT=8000         APP_HOME=/app

WORKDIR ${APP_HOME}

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        && rm -rf /var/lib/apt/lists/*

# Zainstaluj zależności Pythona
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj app
COPY . .

# --- HARDENING: Uruchom jako non-root user (Zadanie L7) ---
# Tworzymy grupę i użytkownika 'appuser'
RUN addgroup --system appuser && adduser --system --group appuser

# Zmieniamy właściciela plików aplikacji na tego użytkownika
RUN chown -R appuser:appuser /app

# Przełączamy się z roota na appuser
USER appuser
# ---------------------------------------------

EXPOSE 8000
CMD ["python", "app.py"]