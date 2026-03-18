#!/usr/bin/env python3
"""
Zählererfassung – Launcher für Bot und Dashboard.

Startet sowohl den Telegram-Bot als auch das FastAPI-Dashboard.
"""
import asyncio
import logging
import signal
import sys
import threading
from contextlib import suppress

import uvicorn

import config
from db.database import init_db

# ─── Logging ──────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# ─── Dashboard in Thread ──────────────────────────────────────────────────

def start_dashboard():
    """Startet das FastAPI-Dashboard in einem separaten Thread."""
    from web.app import app
    
    uvicorn_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=config.DASHBOARD_PORT,
        log_level="info",
        access_log=True,
    )
    server = uvicorn.Server(uvicorn_config)
    
    # Uvicorn im Thread starten
    logger.info(f"📊 Dashboard wird gestartet auf Port {config.DASHBOARD_PORT}...")
    server.run()


# ─── Hauptfunktion ────────────────────────────────────────────────────────

async def main():
    """Haupteinstiegspunkt."""
    logger.info("=" * 50)
    logger.info("⚡ ZÄHLERERFASSUNG – Telegram Bot + Dashboard")
    logger.info("=" * 50)
    
    # Datenbank initialisieren
    logger.info("📦 Initialisiere Datenbank...")
    init_db()
    logger.info("✅ Datenbank bereit.")
    
    # Dashboard in separatem Thread starten
    dashboard_thread = threading.Thread(target=start_dashboard, daemon=True)
    dashboard_thread.start()
    logger.info(f"✅ Dashboard gestartet: http://localhost:{config.DASHBOARD_PORT}")
    
    # Telegram-Bot starten
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN nicht gesetzt!")
        logger.error("   Bitte in .env-Datei konfigurieren.")
        sys.exit(1)
    
    logger.info("🤖 Starte Telegram-Bot...")
    
    from bot.main import create_application
    
    app = create_application()
    
    # Signal-Handler für sauberes Beenden
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("⏹️ Beenden angefordert...")
        loop.stop()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, signal_handler)
    
    try:
        await app.initialize()
        await app.start()
        logger.info("✅ Telegram-Bot erfolgreich gestartet.")
        logger.info("")
        logger.info("🚀 Zählererfassung ist bereit!")
        logger.info(f"   📱 Telegram-Bot: @{(await app.bot.get_me()).username}")
        logger.info(f"   📊 Dashboard: http://localhost:{config.DASHBOARD_PORT}")
        logger.info("")
        logger.info("Drücken Sie Strg+C zum Beenden.")
        
        await app.updater.start_polling(drop_pending_updates=True)
        
        # Warten bis beendet
        while True:
            await asyncio.sleep(1)
            
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"❌ Fehler: {e}")
        raise
    finally:
        logger.info("⏹️ Fahre herunter...")
        with suppress(Exception):
            await app.updater.stop()
        with suppress(Exception):
            await app.stop()
        with suppress(Exception):
            await app.shutdown()
        logger.info("👋 Auf Wiedersehen!")


def run_bot_only():
    """Startet nur den Telegram-Bot (ohne Dashboard)."""
    import asyncio
    from bot.main import create_application
    
    logger.info("🤖 Starte nur Telegram-Bot...")
    init_db()
    
    app = create_application()
    app.run_polling(drop_pending_updates=True)


def run_dashboard_only():
    """Startet nur das Dashboard (ohne Bot)."""
    from web.app import app
    
    logger.info(f"📊 Starte nur Dashboard auf Port {config.DASHBOARD_PORT}...")
    init_db()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.DASHBOARD_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "bot":
            run_bot_only()
        elif command == "dashboard":
            run_dashboard_only()
        elif command == "help":
            print("Zählererfassung – Befehle:")
            print("")
            print("  python run.py          # Bot + Dashboard zusammen")
            print("  python run.py bot      # Nur Telegram-Bot")
            print("  python run.py dashboard # Nur Web-Dashboard")
        else:
            print(f"Unbekannter Befehl: {command}")
            print("Verwende 'python run.py help' für Hilfe.")
            sys.exit(1)
    else:
        # Beides starten
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.info("👋 Auf Wiedersehen!")
