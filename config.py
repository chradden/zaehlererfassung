"""Konfiguration – Lädt Umgebungsvariablen aus .env"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Datenbank
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///zaehler.db")

# Verzeichnisse
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")

# Passwort-Schutz
BOT_PASSWORT = os.getenv("BOT_PASSWORT", "")  # Leer = kein Schutz
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORT = os.getenv("DASHBOARD_PASSWORT", "")  # Leer = kein Schutz

# Bot-Steuerung: false = nur Dashboard starten (z.B. im Codespace)
BOT_AKTIV = os.getenv("BOT_AKTIV", "true").lower() == "true"

# Dashboard
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8094"))
