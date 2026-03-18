# Zählererfassung – Telegram Bot + Web-Dashboard ⚡💧🔥

Intelligente Erfassung von Energiezählern per Telegram. Fotografiere Zähler, KI erkennt **Typ & Stand automatisch**, berechnet **Verbräuche** und erstellt **Word-Berichte** auf Knopfdruck.

📋 Ausführlicher Umsetzungsplan: [PLAN.md](PLAN.md)
📖 Bedienungsanleitung: [docs/Bedienungsanleitung_Zaehlererfassung.md](docs/Bedienungsanleitung_Zaehlererfassung.md)

---

## Features

### Telegram-Bot
- 📷 **Foto → KI-Erkennung** (GPT-4o Vision): Zählertyp, Stand, Nummer
- ⚡💧🔥 **Alle Zählerarten**: Strom, Gas, Wasser, Wärme, Öl, Solar
- 📈 **Automatische Verbrauchsberechnung** seit letzter Ablesung
- 🔄 **Zähler-Wiedererkennung** bei Folge-Ablesungen
- 📍 **GPS-Standort** → Gebäude-Adresse automatisch
- 🎤 **Sprachnotizen** per Whisper transkribiert
- 📄 **Word-Berichte** direkt im Chat generieren

### Web-Dashboard
- 🏠 **Gebäudeübersicht** mit allen Zählern & Statistiken
- 📊 **Interaktive Verbrauchsdiagramme** (Chart.js)
- 📈 **Zähler-Detailseiten** mit Ablesungshistorie
- 🚨 **Anomalie-Hinweise** bei ungewöhnlichen Verbräuchen
- 📄 **Bericht-Generator** (Word/CSV)
- 📷 **Fotogalerie** der Zählerablesungen

---

## Tech-Stack

| Komponente | Technologie |
|---|---|
| Bot | Telegram API (python-telegram-bot 21.x) |
| KI Vision | OpenAI GPT-4o |
| KI Reports | OpenAI GPT-4o-mini |
| Sprache→Text | OpenAI Whisper |
| Dashboard | FastAPI + Jinja2 + Uvicorn |
| Datenbank | SQLite + SQLAlchemy 2.0 |
| Word-Export | python-docx |
| Diagramme | Chart.js |
| Geocoding | OpenStreetMap Nominatim |
| Deployment | Docker + Caddy |

---

## Schnellstart

### 1. Voraussetzungen

- Python 3.10+
- Telegram-Account
- Telegram Bot Token (von [@BotFather](https://t.me/botfather))
- OpenAI API Key

### 2. Installation

```bash
git clone https://github.com/chradden/zaehlererfassung.git
cd zaehlererfassung
pip install -r requirements.txt
```

### 3. Konfiguration

Erstelle eine `.env`-Datei:

```env
TELEGRAM_BOT_TOKEN=dein-bot-token
OPENAI_API_KEY=sk-xxx
DATABASE_URL=sqlite:///zaehler.db

# Optional: Passwort-Schutz
BOT_PASSWORT=
DASHBOARD_PASSWORT=
```

### 4. Starten

```bash
python run.py
```

Startet gleichzeitig:
- **Telegram Bot** (Polling)
- **Web-Dashboard** auf http://localhost:8094

---

## Telegram-Bot Befehle

| Befehl | Funktion |
|---|---|
| `/start` | Registrierung |
| `/gebaeude <Name>` | Neues Gebäude anlegen |
| `/wechsel` | Gebäude wechseln |
| `/zaehler` | Zähler am Gebäude auflisten |
| `/status` | Aktives Gebäude & letzte Ablesungen |
| `/bericht` | Word-Bericht generieren |
| `/export` | CSV-Export |
| `/hilfe` | Alle Befehle |

### Eingaben nach Foto

| Eingabe | Wirkung |
|---|---|
| 📷 Foto senden | Zähler scannen & Stand erfassen |
| 📍 Standort teilen | Gebäude-Adresse hinterlegen |
| 🎤 Sprachnachricht | Notiz zur letzten Ablesung |
| `Stand: 12345.67` | Manueller Zählerstand |

---

## Beispiel-Workflow

```
Du:   /start
Bot:  Willkommen bei der Zählererfassung! ⚡💧🔥
      Bitte gib deinen Namen ein:

Du:   Thomas Müller
Bot:  Hallo Thomas! ✅ Lege dein erstes Gebäude an mit /gebaeude <Name>

Du:   /gebaeude Bürogebäude Hauptstraße 15
Bot:  ✅ Gebäude "Bürogebäude Hauptstraße 15" angelegt.

Du:   [📷 Foto vom Stromzähler]
Bot:  🔍 Analysiere Zählerfoto...
      
      ⚡ **Stromzähler erkannt**
      📊 Zählerstand: 45.678,3 kWh
      🔢 Zählernummer: 1EMH0012345678
      
      ✅ Neuer Zähler #1 angelegt – Erste Ablesung erfasst!

--- 1 Monat später ---

Du:   [📷 Foto vom gleichen Zähler]
Bot:  🔍 Analysiere Zählerfoto...
      
      ⚡ **Stromzähler #1** (Keller)
      📊 Zählerstand: 46.234,1 kWh
      
      📈 **Verbrauch:**
      • Seit letzter Ablesung: 555,8 kWh
      • Zeitraum: 31 Tage
      • Durchschnitt: 17,9 kWh/Tag
      
      ✅ Ablesung gespeichert!

Du:   /bericht
Bot:  📄 Bericht wird erstellt...
      [📎 Zählerbericht_Hauptstrasse_15_2026-03.docx]
```

---

## Roadmap

- [ ] **Phase 1:** Bot-Grundgerüst, KI-Erkennung, Basis-Dashboard
- [ ] **Phase 2:** Alle Zählertypen, GPS, Sprachnotizen, Word-Berichte
- [ ] **Phase 3:** Anomalie-Erkennung, Jahresvergleiche, Mehrbenutzer
- [ ] **Phase 4:** Docker-Deployment, VPS, Dokumentation

---

## Lizenz

MIT