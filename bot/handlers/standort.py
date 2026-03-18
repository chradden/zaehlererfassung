"""Handler für GPS-Standort → Gebäude-Adresse."""
import logging
import requests
from telegram import Update
from telegram.ext import ContextTypes

from db.database import get_session
from db.models import Benutzer, Gebaeude

logger = logging.getLogger(__name__)


def reverse_geocode(lat: float, lon: float) -> str | None:
    """Wandelt GPS-Koordinaten in eine Adresse um (OpenStreetMap Nominatim)."""
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "addressdetails": 1,
        }
        headers = {"User-Agent": "Zaehlererfassung-Bot/1.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if "address" in data:
            addr = data["address"]
            teile = []
            
            # Straße + Hausnummer
            if "road" in addr:
                strasse = addr["road"]
                if "house_number" in addr:
                    strasse += " " + addr["house_number"]
                teile.append(strasse)
            
            # PLZ + Ort
            if "postcode" in addr or "city" in addr or "town" in addr:
                plz = addr.get("postcode", "")
                ort = addr.get("city") or addr.get("town") or addr.get("village", "")
                teile.append(f"{plz} {ort}".strip())
            
            return ", ".join(teile) if teile else data.get("display_name")
        
        return data.get("display_name")
    
    except Exception as e:
        logger.error(f"Geocoding-Fehler: {e}")
        return None


async def standort_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Erklärt wie man den Standort teilt."""
    await update.message.reply_text(
        "📍 *Standort teilen*\n\n"
        "Um die Adresse deines aktiven Gebäudes zu hinterlegen:\n\n"
        "1. Tippe auf das Büroklammer-Symbol\n"
        "2. Wähle 'Standort'\n"
        "3. Sende deinen aktuellen Standort\n\n"
        "Die Adresse wird automatisch ermittelt und gespeichert.",
        parse_mode="Markdown",
    )


async def standort_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verarbeitet geteilten GPS-Standort."""
    telegram_id = update.effective_user.id
    location = update.message.location
    
    lat = location.latitude
    lon = location.longitude

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

        # GPS speichern
        gebaeude.gps_lat = lat
        gebaeude.gps_lon = lon
        
        # Adresse ermitteln
        adresse = reverse_geocode(lat, lon)
        if adresse:
            gebaeude.adresse = adresse
            await update.message.reply_text(
                f"✅ Standort für **{gebaeude.name}** gespeichert:\n\n"
                f"📍 {adresse}\n"
                f"🌐 {lat:.6f}, {lon:.6f}",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                f"✅ GPS-Koordinaten für **{gebaeude.name}** gespeichert:\n\n"
                f"🌐 {lat:.6f}, {lon:.6f}\n\n"
                f"⚠️ Adresse konnte nicht ermittelt werden.",
                parse_mode="Markdown",
            )
