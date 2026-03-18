"""Handler für /start – Registrierung neuer Benutzer mit Passwort-Schutz."""
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, filters,
)

import config
from db.database import get_session
from db.models import Benutzer

# Conversation States
WARTE_AUF_PASSWORT = 0
WARTE_AUF_NAME = 1


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prüft ob Benutzer existiert, sonst Registrierung starten."""
    telegram_id = update.effective_user.id
    name = None

    with get_session() as session:
        benutzer = session.query(Benutzer).filter_by(telegram_id=telegram_id).first()
        if benutzer:
            name = benutzer.name

    if name:
        await update.message.reply_text(
            f"Willkommen zurück, {name}! ⚡💧🔥\n\n"
            f"Nutze /status um dein aktives Gebäude zu sehen.\n"
            f"Nutze /hilfe für alle Befehle."
        )
        return ConversationHandler.END

    # Passwort-Schutz aktiv?
    if config.BOT_PASSWORT:
        await update.message.reply_text(
            "🔒 Willkommen bei der Zählererfassung!\n\n"
            "Dieser Bot ist passwortgeschützt.\n"
            "Bitte gib das Zugangspasswort ein:"
        )
        return WARTE_AUF_PASSWORT
    else:
        await update.message.reply_text(
            "Willkommen bei der Zählererfassung! ⚡💧🔥\n\n"
            "Bitte gib deinen Namen ein:"
        )
        return WARTE_AUF_NAME


async def passwort_eingabe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prüft das eingegebene Passwort."""
    eingabe = update.message.text.strip()
    
    # Nachricht mit Passwort löschen
    try:
        await update.message.delete()
    except Exception:
        pass

    if eingabe == config.BOT_PASSWORT:
        await update.message.reply_text(
            "✅ Passwort korrekt!\n\n"
            "Bitte gib deinen Namen ein:"
        )
        context.user_data.pop("passwort_versuche", None)
        return WARTE_AUF_NAME
    else:
        versuche = context.user_data.get("passwort_versuche", 0) + 1
        context.user_data["passwort_versuche"] = versuche
        
        if versuche >= 3:
            await update.message.reply_text(
                "❌ Zu viele Fehlversuche. Zugang gesperrt."
            )
            return ConversationHandler.END
        
        await update.message.reply_text(
            f"❌ Falsches Passwort. Noch {3 - versuche} Versuche."
        )
        return WARTE_AUF_PASSWORT


async def name_eingabe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Speichert den Namen und schließt die Registrierung ab."""
    name = update.message.text.strip()
    telegram_id = update.effective_user.id

    with get_session() as session:
        benutzer = Benutzer(telegram_id=telegram_id, name=name)
        session.add(benutzer)

    context.user_data.pop("passwort_versuche", None)

    await update.message.reply_text(
        f"Hallo {name}! ✅\n\n"
        f"Dein Account wurde erstellt.\n"
        f"Lege jetzt dein erstes Gebäude an mit:\n"
        f"/gebaeude <Name>\n\n"
        f"Beispiel: /gebaeude Bürogebäude Hauptstraße 15"
    )
    return ConversationHandler.END


async def abbrechen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bricht die Registrierung ab."""
    await update.message.reply_text("Registrierung abgebrochen.")
    return ConversationHandler.END


def get_start_handler():
    """Erstellt den ConversationHandler für /start."""
    return ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            WARTE_AUF_PASSWORT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, passwort_eingabe)
            ],
            WARTE_AUF_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, name_eingabe)
            ],
        },
        fallbacks=[CommandHandler("abbrechen", abbrechen)],
    )


async def name_aendern(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ändert den Namen des Benutzers: /name <Neuer Name>"""
    telegram_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("Verwendung: /name <Neuer Name>")
        return
    
    neuer_name = " ".join(context.args)
    
    with get_session() as session:
        benutzer = session.query(Benutzer).filter_by(telegram_id=telegram_id).first()
        if benutzer:
            benutzer.name = neuer_name
            await update.message.reply_text(f"✅ Name geändert zu: {neuer_name}")
        else:
            await update.message.reply_text("Bitte zuerst /start ausführen.")
