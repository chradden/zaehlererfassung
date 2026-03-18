"""Handler für /bericht – Word-Bericht generieren."""
import os
import logging
from datetime import date, datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

from db.database import get_session
from db.models import Benutzer, Gebaeude, Zaehler, Ablesung, Bericht, ZAEHLER_INFO
from core.docx_export import generiere_bericht

logger = logging.getLogger(__name__)


async def bericht_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generiert einen Word-Bericht für das aktive Gebäude."""
    telegram_id = update.effective_user.id

    # Zeitraum bestimmen (Standard: letzter Monat)
    bis_datum = date.today()
    von_datum = bis_datum - timedelta(days=30)
    
    # Optionaler Zeitraum aus Argumenten
    if context.args:
        try:
            # Format: /bericht 01.03.2026 31.03.2026
            if len(context.args) >= 2:
                von_datum = datetime.strptime(context.args[0], "%d.%m.%Y").date()
                bis_datum = datetime.strptime(context.args[1], "%d.%m.%Y").date()
            else:
                # Format: /bericht 03.2026 (ganzer Monat)
                monat_str = context.args[0]
                if "." in monat_str:
                    parts = monat_str.split(".")
                    if len(parts) == 2:
                        monat = int(parts[0])
                        jahr = int(parts[1])
                        von_datum = date(jahr, monat, 1)
                        # Letzter Tag des Monats
                        if monat == 12:
                            bis_datum = date(jahr + 1, 1, 1) - timedelta(days=1)
                        else:
                            bis_datum = date(jahr, monat + 1, 1) - timedelta(days=1)
        except ValueError:
            await update.message.reply_text(
                "❌ Ungültiges Datumsformat.\n"
                "Beispiele:\n"
                "• /bericht (letzter Monat)\n"
                "• /bericht 03.2026 (März 2026)\n"
                "• /bericht 01.03.2026 31.03.2026"
            )
            return

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
        if not gebaeude:
            await update.message.reply_text("Gebäude nicht gefunden.")
            return

        gebaeude_id = gebaeude.id
        gebaeude_name = gebaeude.name
        gebaeude_adresse = gebaeude.adresse

        # Zähler und Ablesungen laden
        zaehler_liste = session.query(Zaehler).filter_by(gebaeude_id=gebaeude_id).all()
        
        if not zaehler_liste:
            await update.message.reply_text(
                f"🏢 {gebaeude_name}\n\n"
                f"_Keine Zähler vorhanden._\n"
                f"Sende zuerst Zählerfotos!",
                parse_mode="Markdown",
            )
            return

        # Daten für Bericht sammeln
        zaehler_daten = []
        gesamt_ablesungen = 0

        for z in zaehler_liste:
            info = ZAEHLER_INFO.get(z.typ, ZAEHLER_INFO["sonstig"])
            
            ablesungen = (
                session.query(Ablesung)
                .filter(
                    Ablesung.zaehler_id == z.id,
                    Ablesung.ablesedatum >= von_datum,
                    Ablesung.ablesedatum <= bis_datum,
                )
                .order_by(Ablesung.ablesedatum)
                .all()
            )

            # Auch letzte Ablesung vor dem Zeitraum (für Verbrauchsberechnung)
            letzte_vor_zeitraum = (
                session.query(Ablesung)
                .filter(
                    Ablesung.zaehler_id == z.id,
                    Ablesung.ablesedatum < von_datum,
                )
                .order_by(Ablesung.ablesedatum.desc())
                .first()
            )

            gesamt_ablesungen += len(ablesungen)

            # Verbrauch im Zeitraum berechnen
            verbrauch_zeitraum = None
            if ablesungen:
                erste = ablesungen[0]
                letzte = ablesungen[-1]
                
                # Startstand: entweder letzte vor Zeitraum oder erste im Zeitraum
                start_stand = letzte_vor_zeitraum.stand if letzte_vor_zeitraum else erste.stand
                end_stand = letzte.stand
                verbrauch_zeitraum = end_stand - start_stand

            zaehler_daten.append({
                "id": z.id,
                "typ": z.typ,
                "info": info,
                "standort": z.standort_detail or "",
                "zaehlernummer": z.zaehlernummer or "",
                "ablesungen": [
                    {
                        "datum": a.ablesedatum,
                        "stand": a.stand,
                        "verbrauch": a.verbrauch,
                    }
                    for a in ablesungen
                ],
                "verbrauch_zeitraum": verbrauch_zeitraum,
                "aktueller_stand": ablesungen[-1].stand if ablesungen else None,
            })

    await update.message.reply_text(
        f"📄 Bericht wird erstellt...\n"
        f"🏢 {gebaeude_name}\n"
        f"📅 {von_datum.strftime('%d.%m.%Y')} – {bis_datum.strftime('%d.%m.%Y')}"
    )

    # Word-Bericht generieren
    try:
        docx_pfad = generiere_bericht(
            gebaeude_name=gebaeude_name,
            gebaeude_adresse=gebaeude_adresse,
            von_datum=von_datum,
            bis_datum=bis_datum,
            zaehler_daten=zaehler_daten,
            ersteller=benutzer.name,
        )
    except Exception as e:
        logger.error(f"Bericht-Erstellung fehlgeschlagen: {e}")
        await update.message.reply_text(f"❌ Fehler bei Berichterstellung: {e}")
        return

    # Bericht in DB speichern
    with get_session() as session:
        bericht = Bericht(
            gebaeude_id=gebaeude_id,
            titel=f"Zählerbericht {gebaeude_name}",
            zeitraum_von=von_datum,
            zeitraum_bis=bis_datum,
            docx_pfad=docx_pfad,
        )
        session.add(bericht)

    # Bericht senden
    with open(docx_pfad, "rb") as docx_file:
        await update.message.reply_document(
            document=docx_file,
            filename=os.path.basename(docx_pfad),
            caption=(
                f"📊 **Zählerbericht**\n"
                f"🏢 {gebaeude_name}\n"
                f"📅 {von_datum.strftime('%d.%m.%Y')} – {bis_datum.strftime('%d.%m.%Y')}\n"
                f"📈 {len(zaehler_daten)} Zähler, {gesamt_ablesungen} Ablesungen"
            ),
            parse_mode="Markdown",
        )
