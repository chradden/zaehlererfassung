"""Zählererfassung Telegram Bot – Hauptmodul."""
import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

import config
from db.database import init_db
from bot.handlers.start import get_start_handler, name_aendern
from bot.handlers.gebaeude import (
    gebaeude_command,
    wechsel_command,
    status_command,
    zaehler_command,
    hilfe_command,
    get_gebaeude_callback_handler,
)
from bot.handlers.standort import standort_command, standort_location
from bot.handlers.ablesung import (
    foto_ablesung,
    text_notiz,
    get_ablesung_callback_handler,
    get_standort_callback_handler,
)
from bot.handlers.bericht import bericht_command
from bot.handlers.export import export_command

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _build_app():
    """Erstellt und konfiguriert die Bot-Application."""
    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Handler registrieren (Reihenfolge wichtig!)
    
    # 1. Conversation Handler für /start (hat Priorität)
    app.add_handler(get_start_handler())

    # 2. Befehle
    app.add_handler(CommandHandler("gebaeude", gebaeude_command))
    app.add_handler(CommandHandler("wechsel", wechsel_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("zaehler", zaehler_command))
    app.add_handler(CommandHandler("bericht", bericht_command))
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CommandHandler("standort", standort_command))
    app.add_handler(CommandHandler("name", name_aendern))
    app.add_handler(CommandHandler("hilfe", hilfe_command))
    app.add_handler(CommandHandler("help", hilfe_command))

    # 3. Callback für Inline-Buttons
    app.add_handler(get_gebaeude_callback_handler())
    app.add_handler(get_ablesung_callback_handler())
    app.add_handler(get_standort_callback_handler())

    # 4. Nachrichten-Handler (Fotos, Standort, Text)
    app.add_handler(MessageHandler(filters.PHOTO, foto_ablesung))
    app.add_handler(MessageHandler(filters.LOCATION, standort_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_notiz))

    return app


def create_application():
    """Erstellt und konfiguriert die Bot-Application (ohne Polling)."""
    return _build_app()


def main():
    """Bot starten mit Polling."""
    logger.info("Initialisiere Datenbank...")
    init_db()

    logger.info("Starte Zählererfassung-Bot...")
    app = _build_app()

    logger.info("Bot läuft! Drücke Ctrl+C zum Beenden.")
    app.run_polling()


if __name__ == "__main__":
    main()
