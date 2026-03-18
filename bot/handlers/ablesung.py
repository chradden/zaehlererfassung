"""Handler für Zählerfotos – KI-Erkennung und Ablesungen."""
import os
import json
import logging
from datetime import datetime, date
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

import config
from db.database import get_session
from db.models import Benutzer, Gebaeude, Zaehler, Ablesung, ZaehlerFoto, ZAEHLER_INFO
from core.ki import analysiere_zaehler
from core.verbrauch import berechne_verbrauch
from bot.keyboards import neuer_oder_ablesung_keyboard, standort_keyboard, zaehlertyp_keyboard

logger = logging.getLogger(__name__)


async def foto_ablesung(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verarbeitet eingehende Fotos als Zählerablesung."""
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

        gebaeude_id = benutzer.aktives_gebaeude_id
        benutzer_id = benutzer.id
        gebaeude_name = session.get(Gebaeude, gebaeude_id).name

    jetzt = datetime.now()
    
    # Foto herunterladen
    photo = update.message.photo[-1]  # Höchste Auflösung
    file = await photo.get_file()

    foto_dir = os.path.join(
        config.UPLOAD_DIR,
        str(gebaeude_id),
        jetzt.strftime("%Y-%m-%d"),
    )
    os.makedirs(foto_dir, exist_ok=True)

    dateipfad = os.path.join(
        foto_dir,
        f"zaehler_{jetzt.strftime('%H%M%S')}_{photo.file_unique_id}.jpg",
    )
    await file.download_to_drive(dateipfad)

    # KI-Analyse
    await update.message.reply_text("🔍 Analysiere Zählerfoto...")

    ki_result = analysiere_zaehler(dateipfad)
    
    if not ki_result:
        await update.message.reply_text(
            "❌ Konnte keinen Zähler auf dem Foto erkennen.\n"
            "Bitte ein deutliches Foto der Zähleranzeige senden."
        )
        return

    # Ergebnis speichern
    context.user_data["ki_result"] = ki_result
    context.user_data["foto_pfad"] = dateipfad
    context.user_data["gebaeude_id"] = gebaeude_id
    context.user_data["benutzer_id"] = benutzer_id

    # Zählertyp und Stand aus KI-Ergebnis
    typ = ki_result.get("typ", "sonstig")
    stand = ki_result.get("stand")
    einheit = ki_result.get("einheit", "")
    zaehlernummer = ki_result.get("zaehlernummer")
    vertrauen = ki_result.get("vertrauen", 0)
    info = ZAEHLER_INFO.get(typ, ZAEHLER_INFO["sonstig"])

    # Qualitäts-Indikator
    if vertrauen >= 0.8:
        qual = "🟢 Gut erkannt"
    elif vertrauen >= 0.5:
        qual = "🟡 Teilweise erkannt"
    else:
        qual = "🔴 Unsicher"

    # Antwort formatieren
    text = f"{info['icon']} **{info['name']}zähler erkannt**\n{qual}\n\n"
    
    if stand is not None:
        text += f"📊 Zählerstand: **{stand:,.1f} {einheit or info['einheit']}**\n"
    else:
        text += f"⚠️ Zählerstand nicht erkannt\n"
    
    if zaehlernummer:
        text += f"🔢 Zählernummer: {zaehlernummer}\n"

    await update.message.reply_text(text, parse_mode="Markdown")

    # Prüfen ob Zähler bereits existiert
    with get_session() as session:
        zaehler_liste = session.query(Zaehler).filter_by(
            gebaeude_id=gebaeude_id
        ).all()

        # Versuchen, Zähler zu identifizieren
        gefundener_zaehler = None
        
        if zaehlernummer:
            for z in zaehler_liste:
                if z.zaehlernummer and z.zaehlernummer == zaehlernummer:
                    gefundener_zaehler = z
                    break
        
        # Wenn nur ein Zähler des gleichen Typs existiert, diesen verwenden
        if not gefundener_zaehler:
            gleicher_typ = [z for z in zaehler_liste if z.typ == typ]
            if len(gleicher_typ) == 1:
                gefundener_zaehler = gleicher_typ[0]

        if gefundener_zaehler and stand is not None:
            # Direkt als Ablesung speichern
            context.user_data["zaehler_id"] = gefundener_zaehler.id
            await _speichere_ablesung(update, context)
        elif stand is not None:
            # Fragen: Neuer Zähler oder bestehender?
            await update.message.reply_text(
                "❓ Was möchtest du tun?",
                reply_markup=neuer_oder_ablesung_keyboard(zaehler_liste),
            )
        else:
            await update.message.reply_text(
                "⚠️ Zählerstand konnte nicht erkannt werden.\n"
                "Du kannst ihn manuell eingeben:\n"
                "`Stand: 12345.67`",
                parse_mode="Markdown",
            )


async def _speichere_ablesung(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Speichert eine Ablesung für einen bestehenden Zähler."""
    ki_result = context.user_data.get("ki_result", {})
    foto_pfad = context.user_data.get("foto_pfad")
    zaehler_id = context.user_data.get("zaehler_id")
    benutzer_id = context.user_data.get("benutzer_id")
    
    stand = ki_result.get("stand")
    vertrauen = ki_result.get("vertrauen", 0)

    with get_session() as session:
        zaehler = session.get(Zaehler, zaehler_id)
        if not zaehler:
            await update.message.reply_text("Zähler nicht gefunden.")
            return

        info = ZAEHLER_INFO.get(zaehler.typ, ZAEHLER_INFO["sonstig"])

        # Letzte Ablesung für Verbrauchsberechnung
        letzte_ablesung = (
            session.query(Ablesung)
            .filter_by(zaehler_id=zaehler_id)
            .order_by(Ablesung.ablesedatum.desc())
            .first()
        )

        # Neue Ablesung erstellen
        ablesung = Ablesung(
            zaehler_id=zaehler_id,
            benutzer_id=benutzer_id,
            stand=stand,
            einheit=zaehler.einheit or info["einheit"],
            ablesedatum=date.today(),
            ki_erkannt=1,
            ki_vertrauen=vertrauen,
        )

        # Verbrauch berechnen
        if letzte_ablesung:
            verbrauch_data = berechne_verbrauch(
                aktueller_stand=stand,
                vorheriger_stand=letzte_ablesung.stand,
                aktuelles_datum=date.today(),
                vorheriges_datum=letzte_ablesung.ablesedatum,
            )
            ablesung.verbrauch = verbrauch_data["verbrauch"]
            ablesung.verbrauch_pro_tag = verbrauch_data["pro_tag"]
            ablesung.tage_seit_letzter = verbrauch_data["tage"]

        session.add(ablesung)
        session.flush()

        # Foto speichern
        if foto_pfad:
            foto = ZaehlerFoto(
                ablesung_id=ablesung.id,
                dateipfad=foto_pfad,
                ki_roh_json=json.dumps(ki_result),
            )
            session.add(foto)

        # Antwort formatieren
        standort = zaehler.standort_detail or f"#{zaehler.id}"
        text = f"✅ **Ablesung gespeichert!**\n\n"
        text += f"{info['icon']} {info['name']}zähler ({standort})\n"
        text += f"📊 Stand: {stand:,.1f} {info['einheit']}\n"
        text += f"📅 Datum: {date.today().strftime('%d.%m.%Y')}\n"

        if letzte_ablesung and ablesung.verbrauch is not None:
            text += f"\n📈 **Verbrauch:**\n"
            text += f"• Seit letzter Ablesung: **{ablesung.verbrauch:,.1f} {info['einheit']}**\n"
            text += f"• Zeitraum: {ablesung.tage_seit_letzter} Tage\n"
            if ablesung.verbrauch_pro_tag:
                text += f"• Durchschnitt: {ablesung.verbrauch_pro_tag:,.1f} {info['einheit']}/Tag\n"
            
            # Warnung bei negativem Verbrauch
            if ablesung.verbrauch < 0:
                text += f"\n⚠️ **Achtung:** Negativer Verbrauch! Zählerstand prüfen."

    await update.message.reply_text(text, parse_mode="Markdown")
    
    # User-Data aufräumen
    context.user_data.pop("ki_result", None)
    context.user_data.pop("foto_pfad", None)
    context.user_data.pop("zaehler_id", None)


async def neuer_zaehler_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback für 'Neuer Zähler'-Button."""
    query = update.callback_query
    await query.answer()

    if query.data == "zaehler_neu":
        context.user_data["aktion"] = "neuer_zaehler"
        await query.edit_message_text(
            "📍 Wo befindet sich der Zähler?",
            reply_markup=standort_keyboard(),
        )
    elif query.data.startswith("ablesung_"):
        zaehler_id = int(query.data.split("_")[1])
        context.user_data["zaehler_id"] = zaehler_id
        
        # Ablesung speichern
        # Wir müssen hier eine Nachricht simulieren
        await query.edit_message_text("📖 Speichere Ablesung...")
        await _speichere_ablesung_from_callback(query, context)


async def _speichere_ablesung_from_callback(query, context: ContextTypes.DEFAULT_TYPE):
    """Speichert Ablesung nach Callback-Auswahl."""
    ki_result = context.user_data.get("ki_result", {})
    foto_pfad = context.user_data.get("foto_pfad")
    zaehler_id = context.user_data.get("zaehler_id")
    benutzer_id = context.user_data.get("benutzer_id")
    
    stand = ki_result.get("stand")
    vertrauen = ki_result.get("vertrauen", 0)

    with get_session() as session:
        zaehler = session.get(Zaehler, zaehler_id)
        if not zaehler:
            await query.edit_message_text("Zähler nicht gefunden.")
            return

        info = ZAEHLER_INFO.get(zaehler.typ, ZAEHLER_INFO["sonstig"])

        letzte_ablesung = (
            session.query(Ablesung)
            .filter_by(zaehler_id=zaehler_id)
            .order_by(Ablesung.ablesedatum.desc())
            .first()
        )

        ablesung = Ablesung(
            zaehler_id=zaehler_id,
            benutzer_id=benutzer_id,
            stand=stand,
            einheit=zaehler.einheit or info["einheit"],
            ablesedatum=date.today(),
            ki_erkannt=1,
            ki_vertrauen=vertrauen,
        )

        if letzte_ablesung:
            verbrauch_data = berechne_verbrauch(
                aktueller_stand=stand,
                vorheriger_stand=letzte_ablesung.stand,
                aktuelles_datum=date.today(),
                vorheriges_datum=letzte_ablesung.ablesedatum,
            )
            ablesung.verbrauch = verbrauch_data["verbrauch"]
            ablesung.verbrauch_pro_tag = verbrauch_data["pro_tag"]
            ablesung.tage_seit_letzter = verbrauch_data["tage"]

        session.add(ablesung)
        session.flush()

        if foto_pfad:
            foto = ZaehlerFoto(
                ablesung_id=ablesung.id,
                dateipfad=foto_pfad,
                ki_roh_json=json.dumps(ki_result),
            )
            session.add(foto)

        standort = zaehler.standort_detail or f"#{zaehler.id}"
        text = f"✅ **Ablesung gespeichert!**\n\n"
        text += f"{info['icon']} {info['name']}zähler ({standort})\n"
        text += f"📊 Stand: {stand:,.1f} {info['einheit']}\n"

        if letzte_ablesung and ablesung.verbrauch is not None:
            text += f"\n📈 Verbrauch: **{ablesung.verbrauch:,.1f} {info['einheit']}**"
            text += f" ({ablesung.tage_seit_letzter} Tage)"

    await query.edit_message_text(text, parse_mode="Markdown")
    
    context.user_data.pop("ki_result", None)
    context.user_data.pop("foto_pfad", None)
    context.user_data.pop("zaehler_id", None)


async def standort_auswahl_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback für Standort-Auswahl bei neuem Zähler."""
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("standort_"):
        return

    standort = query.data.replace("standort_", "")
    
    if standort == "custom":
        await query.edit_message_text(
            "📝 Bitte sende den Standort als Text\n"
            "(z.B. `Keller links`, `Heizraum UG`)",
            parse_mode="Markdown",
        )
        context.user_data["warte_auf_standort"] = True
        return

    # Zähler anlegen
    await _lege_zaehler_an(query, context, standort)


async def _lege_zaehler_an(query, context: ContextTypes.DEFAULT_TYPE, standort: str):
    """Legt einen neuen Zähler an."""
    ki_result = context.user_data.get("ki_result", {})
    foto_pfad = context.user_data.get("foto_pfad")
    gebaeude_id = context.user_data.get("gebaeude_id")
    benutzer_id = context.user_data.get("benutzer_id")

    typ = ki_result.get("typ", "sonstig")
    stand = ki_result.get("stand")
    zaehlernummer = ki_result.get("zaehlernummer")
    hersteller = ki_result.get("hersteller")
    modell = ki_result.get("modell")
    vertrauen = ki_result.get("vertrauen", 0)
    
    info = ZAEHLER_INFO.get(typ, ZAEHLER_INFO["sonstig"])

    with get_session() as session:
        # Zähler anlegen
        zaehler = Zaehler(
            gebaeude_id=gebaeude_id,
            zaehlernummer=zaehlernummer,
            typ=typ,
            einheit=info["einheit"],
            standort_detail=standort,
            hersteller=hersteller,
            modell=modell,
        )
        session.add(zaehler)
        session.flush()

        zaehler_id = zaehler.id

        # Erste Ablesung anlegen
        if stand is not None:
            ablesung = Ablesung(
                zaehler_id=zaehler_id,
                benutzer_id=benutzer_id,
                stand=stand,
                einheit=info["einheit"],
                ablesedatum=date.today(),
                ki_erkannt=1,
                ki_vertrauen=vertrauen,
            )
            session.add(ablesung)
            session.flush()

            if foto_pfad:
                foto = ZaehlerFoto(
                    ablesung_id=ablesung.id,
                    dateipfad=foto_pfad,
                    ki_roh_json=json.dumps(ki_result),
                )
                session.add(foto)

    # Bestätigung
    text = f"✅ **{info['name']}zähler #{zaehler_id} angelegt**\n\n"
    text += f"📍 Standort: {standort}\n"
    if zaehlernummer:
        text += f"🔢 Nummer: {zaehlernummer}\n"
    if stand is not None:
        text += f"\n📊 Erste Ablesung: {stand:,.1f} {info['einheit']}\n"
        text += f"➡️ Verbrauchsberechnung ab nächster Ablesung möglich."

    await query.edit_message_text(text, parse_mode="Markdown")
    
    # Aufräumen
    context.user_data.pop("ki_result", None)
    context.user_data.pop("foto_pfad", None)
    context.user_data.pop("aktion", None)


async def text_notiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verarbeitet Textnachrichten – Standort oder manuelle Eingabe."""
    text = update.message.text.strip()
    
    # Warten auf Standort-Eingabe?
    if context.user_data.get("warte_auf_standort"):
        context.user_data.pop("warte_auf_standort")
        # Simuliere Callback
        class FakeQuery:
            async def edit_message_text(self, *args, **kwargs):
                await update.message.reply_text(*args, **kwargs)
            async def answer(self):
                pass
            data = f"standort_{text}"
        
        await _lege_zaehler_an(FakeQuery(), context, text)
        return

    # Manuelle Standeingabe: "Stand: 12345.67"
    if text.lower().startswith("stand:"):
        try:
            stand_str = text.split(":", 1)[1].strip()
            stand = float(stand_str.replace(",", ".").replace(" ", ""))
            
            if "ki_result" in context.user_data:
                context.user_data["ki_result"]["stand"] = stand
                await update.message.reply_text(
                    f"✅ Zählerstand auf {stand:,.1f} gesetzt.\n"
                    f"Wähle jetzt den Zähler oder lege einen neuen an."
                )
            else:
                await update.message.reply_text(
                    "ℹ️ Bitte zuerst ein Zählerfoto senden."
                )
        except ValueError:
            await update.message.reply_text(
                "❌ Ungültiger Zählerstand.\n"
                "Beispiel: `Stand: 12345.67`",
                parse_mode="Markdown",
            )
        return

    # Sonst: Als Notiz zur letzten Ablesung?
    # (Kann später erweitert werden)


def get_ablesung_callback_handler():
    """Gibt den CallbackQueryHandler für Ablesung/Neuer Zähler zurück."""
    return CallbackQueryHandler(neuer_zaehler_callback, pattern=r"^(zaehler_neu|ablesung_\d+)$")


def get_standort_callback_handler():
    """Gibt den CallbackQueryHandler für Standort-Auswahl zurück."""
    return CallbackQueryHandler(standort_auswahl_callback, pattern=r"^standort_")
