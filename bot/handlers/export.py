"""Handler für /export – CSV-Export der Ablesungen."""
import os
import io
import csv
import logging
from datetime import date
from telegram import Update
from telegram.ext import ContextTypes

from db.database import get_session
from db.models import Benutzer, Gebaeude, Zaehler, Ablesung, ZAEHLER_INFO

logger = logging.getLogger(__name__)


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exportiert alle Ablesungen des aktiven Gebäudes als CSV."""
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
        if not gebaeude:
            await update.message.reply_text("Gebäude nicht gefunden.")
            return

        gebaeude_name = gebaeude.name

        # Alle Zähler und Ablesungen laden
        zaehler_liste = session.query(Zaehler).filter_by(
            gebaeude_id=gebaeude.id
        ).all()

        if not zaehler_liste:
            await update.message.reply_text(
                f"🏢 {gebaeude_name}\n\n"
                f"_Keine Zähler vorhanden._",
                parse_mode="Markdown",
            )
            return

        # CSV erstellen
        rows = []
        for z in zaehler_liste:
            info = ZAEHLER_INFO.get(z.typ, ZAEHLER_INFO["sonstig"])
            
            ablesungen = (
                session.query(Ablesung)
                .filter_by(zaehler_id=z.id)
                .order_by(Ablesung.ablesedatum)
                .all()
            )

            for a in ablesungen:
                rows.append({
                    "Zähler-ID": z.id,
                    "Typ": info["name"],
                    "Standort": z.standort_detail or "",
                    "Zählernummer": z.zaehlernummer or "",
                    "Datum": a.ablesedatum.strftime("%d.%m.%Y"),
                    "Stand": f"{a.stand:.2f}",
                    "Einheit": a.einheit or info["einheit"],
                    "Verbrauch": f"{a.verbrauch:.2f}" if a.verbrauch else "",
                    "Verbrauch/Tag": f"{a.verbrauch_pro_tag:.2f}" if a.verbrauch_pro_tag else "",
                    "Tage": a.tage_seit_letzter or "",
                    "KI-erkannt": "Ja" if a.ki_erkannt else "Nein",
                    "Notizen": a.notizen or "",
                })

    if not rows:
        await update.message.reply_text(
            f"🏢 {gebaeude_name}\n\n"
            f"_Keine Ablesungen vorhanden._",
            parse_mode="Markdown",
        )
        return

    # CSV in Memory schreiben
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=rows[0].keys(),
        delimiter=";",  # Excel-freundlich
    )
    writer.writeheader()
    writer.writerows(rows)

    # Dateiname
    safe_name = gebaeude_name.replace(" ", "_").replace("/", "-")
    filename = f"Zaehler_{safe_name}_{date.today().strftime('%Y-%m-%d')}.csv"

    # Als UTF-8 mit BOM (für Excel)
    csv_bytes = output.getvalue().encode("utf-8-sig")

    await update.message.reply_document(
        document=io.BytesIO(csv_bytes),
        filename=filename,
        caption=(
            f"📊 **CSV-Export**\n"
            f"🏢 {gebaeude_name}\n"
            f"📈 {len(rows)} Ablesungen exportiert"
        ),
        parse_mode="Markdown",
    )
