"""Handler für /gebaeude, /wechsel, /status, /hilfe, /zaehler."""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from db.database import get_session
from db.models import Benutzer, Gebaeude, Zaehler, Ablesung, ZAEHLER_INFO
from bot.keyboards import gebaeude_auswahl_keyboard

logger = logging.getLogger(__name__)


async def gebaeude_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Neues Gebäude anlegen: /gebaeude <Name>"""
    telegram_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text(
            "Bitte gib einen Gebäudenamen an:\n"
            "/gebaeude <Name>\n\n"
            "Beispiel: /gebaeude Bürogebäude Hauptstraße 15"
        )
        return

    gebaeude_name = " ".join(context.args)

    with get_session() as session:
        benutzer = session.query(Benutzer).filter_by(telegram_id=telegram_id).first()
        if not benutzer:
            await update.message.reply_text("Bitte zuerst /start ausführen.")
            return

        gebaeude = Gebaeude(name=gebaeude_name)
        session.add(gebaeude)
        session.flush()

        benutzer.aktives_gebaeude_id = gebaeude.id

    await update.message.reply_text(
        f"✅ Gebäude \"{gebaeude_name}\" angelegt und aktiviert.\n\n"
        f"📍 **Tipp:** Teile deinen Standort (📎 → Standort), "
        f"um die Adresse automatisch zu hinterlegen!\n\n"
        f"📷 Sende jetzt ein Foto eines Zählers zum Erfassen.",
        parse_mode="Markdown",
    )


async def wechsel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Aktives Gebäude wechseln."""
    telegram_id = update.effective_user.id

    with get_session() as session:
        benutzer = session.query(Benutzer).filter_by(telegram_id=telegram_id).first()
        if not benutzer:
            await update.message.reply_text("Bitte zuerst /start ausführen.")
            return

        gebaeude_liste = session.query(Gebaeude).all()

        if not gebaeude_liste:
            await update.message.reply_text(
                "Noch keine Gebäude vorhanden.\n"
                "Erstelle eins mit /gebaeude <Name>"
            )
            return

        await update.message.reply_text(
            "🏢 Wähle ein Gebäude:",
            reply_markup=gebaeude_auswahl_keyboard(gebaeude_liste),
        )


async def gebaeude_auswahl_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback für Inline-Button Gebäudeauswahl."""
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("geb_"):
        return

    gebaeude_id = int(query.data.split("_")[1])
    telegram_id = update.effective_user.id

    with get_session() as session:
        benutzer = session.query(Benutzer).filter_by(telegram_id=telegram_id).first()
        if benutzer:
            benutzer.aktives_gebaeude_id = gebaeude_id
            gebaeude = session.get(Gebaeude, gebaeude_id)
            gebaeude_name = gebaeude.name if gebaeude else "Unbekannt"

    await query.edit_message_text(f"✅ Aktives Gebäude: {gebaeude_name}")


def get_gebaeude_callback_handler():
    """Gibt den CallbackQueryHandler für Gebäudeauswahl zurück."""
    return CallbackQueryHandler(gebaeude_auswahl_callback, pattern=r"^geb_\d+$")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt Status: aktives Gebäude & letzte Ablesungen."""
    telegram_id = update.effective_user.id

    with get_session() as session:
        benutzer = session.query(Benutzer).filter_by(telegram_id=telegram_id).first()
        if not benutzer:
            await update.message.reply_text("Bitte zuerst /start ausführen.")
            return

        if not benutzer.aktives_gebaeude_id:
            await update.message.reply_text(
                "Kein aktives Gebäude.\n"
                "Erstelle eins mit /gebaeude <Name>"
            )
            return

        gebaeude = session.get(Gebaeude, benutzer.aktives_gebaeude_id)
        if not gebaeude:
            await update.message.reply_text("Gebäude nicht gefunden.")
            return

        # Zähler und letzte Ablesungen sammeln
        zaehler_liste = session.query(Zaehler).filter_by(
            gebaeude_id=gebaeude.id
        ).all()

        text = f"🏢 **{gebaeude.name}**\n"
        if gebaeude.adresse:
            text += f"📍 {gebaeude.adresse}\n"
        text += f"\n📊 **{len(zaehler_liste)} Zähler**\n\n"

        if zaehler_liste:
            for z in zaehler_liste:
                info = ZAEHLER_INFO.get(z.typ, ZAEHLER_INFO["sonstig"])
                letzte = (
                    session.query(Ablesung)
                    .filter_by(zaehler_id=z.id)
                    .order_by(Ablesung.ablesedatum.desc())
                    .first()
                )
                
                standort = z.standort_detail or ""
                text += f"{info['icon']} **#{z.id}** {standort}\n"
                
                if letzte:
                    text += f"   Stand: {letzte.stand:,.1f} {info['einheit']}\n"
                    text += f"   Datum: {letzte.ablesedatum.strftime('%d.%m.%Y')}\n"
                else:
                    text += f"   _Noch keine Ablesung_\n"
                text += "\n"
        else:
            text += "_Noch keine Zähler erfasst._\n"
            text += "📷 Sende ein Foto eines Zählers!"

    await update.message.reply_text(text, parse_mode="Markdown")


async def zaehler_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Listet alle Zähler am aktiven Gebäude auf."""
    telegram_id = update.effective_user.id

    with get_session() as session:
        benutzer = session.query(Benutzer).filter_by(telegram_id=telegram_id).first()
        if not benutzer:
            await update.message.reply_text("Bitte zuerst /start ausführen.")
            return

        if not benutzer.aktives_gebaeude_id:
            await update.message.reply_text(
                "Kein aktives Gebäude. Erstelle eins mit /gebaeude <Name>"
            )
            return

        gebaeude = session.get(Gebaeude, benutzer.aktives_gebaeude_id)
        zaehler_liste = session.query(Zaehler).filter_by(
            gebaeude_id=gebaeude.id
        ).all()

        if not zaehler_liste:
            await update.message.reply_text(
                f"🏢 {gebaeude.name}\n\n"
                f"_Noch keine Zähler erfasst._\n"
                f"📷 Sende ein Foto eines Zählers!",
                parse_mode="Markdown",
            )
            return

        text = f"🏢 **{gebaeude.name}**\n"
        text += f"📊 {len(zaehler_liste)} Zähler:\n\n"

        for z in zaehler_liste:
            info = ZAEHLER_INFO.get(z.typ, ZAEHLER_INFO["sonstig"])
            
            text += f"{info['icon']} **#{z.id}** – {info['name']}\n"
            if z.standort_detail:
                text += f"   📍 {z.standort_detail}\n"
            if z.zaehlernummer:
                text += f"   🔢 {z.zaehlernummer}\n"
            
            # Letzte Ablesung
            letzte = (
                session.query(Ablesung)
                .filter_by(zaehler_id=z.id)
                .order_by(Ablesung.ablesedatum.desc())
                .first()
            )
            if letzte:
                text += f"   📖 {letzte.stand:,.1f} {info['einheit']} ({letzte.ablesedatum.strftime('%d.%m.%Y')})\n"
            
            text += "\n"

    await update.message.reply_text(text, parse_mode="Markdown")


async def hilfe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Zeigt alle verfügbaren Befehle."""
    text = """⚡💧🔥 **Zählererfassung – Hilfe**

**Gebäude verwalten:**
/gebaeude <Name> – Neues Gebäude anlegen
/wechsel – Aktives Gebäude wechseln
/status – Aktuelles Gebäude & Zähler anzeigen
/zaehler – Alle Zähler am Gebäude auflisten

**Zähler erfassen:**
📷 Foto senden – Zähler automatisch erkennen
📍 Standort teilen – Adresse hinterlegen
🎤 Sprachnachricht – Notiz zur Ablesung

**Eichfristen (DIN ISO 50001):**
/eichung – Eichstatus aller Zähler prüfen
`Eichfrist: DD.MM.YYYY` – Eichfrist manuell setzen
(Die KI versucht den Eichstempel automatisch vom Foto zu lesen)

**Berichte & Export:**
/bericht – Word-Bericht erstellen
/export – CSV-Export aller Ablesungen

**Sonstiges:**
/name <Name> – Eigenen Namen ändern
/hilfe – Diese Hilfe anzeigen

**Tipp:** Einfach Zählerfotos senden – die KI erkennt Typ, Stand und Eichstempel automatisch!"""

    await update.message.reply_text(text, parse_mode="Markdown")
