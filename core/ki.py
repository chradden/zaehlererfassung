"""KI-Modul – OpenAI GPT-4o Vision für Zähler-Erkennung."""
import json
import base64
import logging
from openai import OpenAI

import config

logger = logging.getLogger(__name__)

client = OpenAI(api_key=config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None


# ─── Zähler-Analyse (GPT-4o Vision) ─────────────────────────────────────

ZAEHLER_PROMPT = """Du bist ein Experte für Energiezähler und Messgeräte.
Analysiere dieses Foto eines Zählers und extrahiere ALLE lesbaren Daten.

WICHTIG:
1. Erkenne den ZÄHLERTYP anhand des Aussehens:
   - strom: Stromzähler (digital oder Drehscheibe, zeigt kWh)
   - gas: Gaszähler (mechanische Rollen, zeigt m³)
   - wasser: Wasserzähler (oft blau/grau, zeigt m³ oder Liter)
   - waerme: Wärmemengenzähler (zeigt kWh oder MWh, oft mit Temperaturanzeige)
   - oel: Ölstandanzeige/Füllstandsmesser (zeigt Liter oder %)
   - solar: PV-Einspeisezähler (oft mit Pfeil-Symbol, zeigt kWh)
   - sonstig: Falls unklar

2. Lies den ZÄHLERSTAND ab – achte auf:
   - Alle Ziffern VOR dem Komma
   - Nachkommastellen (oft rot markiert oder kleiner)
   - Einheit (kWh, m³, MWh, Liter)

3. Lies die ZÄHLERNUMMER ab (Kennzeichen, Eigentumsnummer, Seriennummer)

Antworte NUR mit validem JSON (kein Markdown, keine Erklärung):
{
    "typ": "strom|gas|wasser|waerme|oel|solar|sonstig",
    "stand": 12345.67,
    "einheit": "kWh|m³|MWh|Liter",
    "zaehlernummer": "Nummer oder null",
    "hersteller": "Name oder null",
    "modell": "Modell oder null",
    "vertrauen": 0.95,
    "hinweise": "Kurze Notiz zur Erkennungsqualität"
}

REGELN:
- stand MUSS eine Zahl sein (nicht String)
- vertrauen: 0.0-1.0 (wie sicher bist du?)
- Bei unlesbarem Stand: stand = null
- Bei unklarem Typ: typ = "sonstig"
"""


def analysiere_zaehler(dateipfad: str) -> dict | None:
    """Analysiert ein Zählerfoto per GPT-4o Vision."""
    if not client:
        logger.warning("OpenAI API Key nicht konfiguriert – verwende Demo-Modus")
        return _demo_analyse(dateipfad)

    try:
        with open(dateipfad, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": ZAEHLER_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            max_tokens=500,
            temperature=0.1,
        )

        content = response.choices[0].message.content
        
        # JSON aus Antwort extrahieren (falls Markdown-Wrapper)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        result = json.loads(content.strip())
        logger.info(f"Zähler erkannt: {result.get('typ')} – Stand: {result.get('stand')}")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON-Parsing-Fehler: {e}\nAntwort: {content}")
        return None
    except Exception as e:
        logger.error(f"KI-Analyse fehlgeschlagen: {e}")
        return None


def _demo_analyse(dateipfad: str) -> dict:
    """Demo-Modus ohne API-Key – gibt Testdaten zurück."""
    import random
    
    typen = ["strom", "gas", "wasser"]
    typ = random.choice(typen)
    
    demo_daten = {
        "strom": {"stand": 45678.3, "einheit": "kWh"},
        "gas": {"stand": 12345.67, "einheit": "m³"},
        "wasser": {"stand": 1234.56, "einheit": "m³"},
    }
    
    return {
        "typ": typ,
        "stand": demo_daten[typ]["stand"],
        "einheit": demo_daten[typ]["einheit"],
        "zaehlernummer": f"DEMO-{random.randint(1000, 9999)}",
        "hersteller": "Demo-Hersteller",
        "modell": None,
        "vertrauen": 0.85,
        "hinweise": "DEMO-MODUS: Kein OpenAI API Key konfiguriert",
    }


# ─── Whisper Transkription ─────────────────────────────────────────────

def transkribiere_audio(dateipfad: str) -> str | None:
    """Transkribiert eine Audiodatei per Whisper."""
    if not client:
        logger.warning("OpenAI API Key nicht konfiguriert")
        return None

    try:
        with open(dateipfad, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="de",
            )
        return response.text
    except Exception as e:
        logger.error(f"Whisper-Transkription fehlgeschlagen: {e}")
        return None


# ─── Berichtstext generieren ───────────────────────────────────────────

BERICHT_PROMPT = """Du bist ein Assistent für Gebäudeverwaltung und Energiemanagement.
Analysiere die folgenden Zählerablesungen und erstelle eine kurze Zusammenfassung.

Zähler-Daten:
{zaehler_json}

Erstelle eine Zusammenfassung mit:
1. Übersicht der Verbräuche
2. Auffälligkeiten (hohe Verbräuche, Anomalien)
3. Empfehlungen (falls relevant)

Schreibe professionell, aber verständlich. Maximal 200 Wörter."""


def generiere_zusammenfassung(zaehler_daten: list) -> str | None:
    """Generiert eine KI-Zusammenfassung für den Bericht."""
    if not client:
        return None

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": BERICHT_PROMPT.format(
                        zaehler_json=json.dumps(zaehler_daten, indent=2, ensure_ascii=False)
                    ),
                }
            ],
            max_tokens=500,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Zusammenfassung fehlgeschlagen: {e}")
        return None
