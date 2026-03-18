# Zählererfassung – Umsetzungsplan

## 1. Überblick

Das System ermöglicht es **Hausmeistern, Facility Managern und Objektbetreuern**, per **Telegram** Energiezähler in Gebäuden zu erfassen. Eine **KI (GPT-4o Vision)** erkennt automatisch den Zählertyp, liest den Zählerstand ab und berechnet Verbräuche. Das **Streamlit-Dashboard** bietet Auswertungen, Diagramme und Word-Berichte.

```
┌──────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│   Hausmeister    │     │    Backend-Server    │     │   Word-Bericht      │
│   (Telegram)     │────▶│  + KI (GPT-4o Vision)│────▶│   + CSV-Export      │
│                  │◀────│  + SQLite Datenbank  │     │   + Diagramme       │
│ Foto/Standort/   │     │  + Verbrauchsanalyse │     │                     │
│ Sprachnachricht  │     └──────────────────────┘     └─────────────────────┘
└──────────────────┘              │
                                  │
                    ┌─────────────▼─────────────┐
                    │   Streamlit-Dashboard     │
                    │   - Gebäudeübersicht      │
                    │   - Verbrauchsdiagramme   │
                    │   - Alarme & Anomalien    │
                    │   - Berichte generieren   │
                    └───────────────────────────┘
```

---

## 2. Tech-Stack

| Komponente        | Technologie                      | Begründung                                    |
|-------------------|----------------------------------|-----------------------------------------------|
| **Bot-Interface** | Telegram Bot API (python-telegram-bot 21.x) | Bewährt in bautagebuch & typenschild-scanner |
| **KI Vision**     | OpenAI GPT-4o                    | Zählertyp + Zählerstand per Foto erkennen    |
| **KI Reports**    | OpenAI GPT-4o-mini               | Textgenerierung für Berichte                 |
| **Sprache→Text**  | OpenAI Whisper API               | Notizen per Sprachnachricht                  |
| **Backend**       | Python 3.12                      | Einheitlich mit anderen Projekten            |
| **Dashboard**     | FastAPI + Jinja2 + Uvicorn       | Bewährt in bautagebuch & typenschild-scanner |
| **Datenbank**     | SQLite + SQLAlchemy 2.0          | Einfach, portabel, später PostgreSQL möglich |
| **Word-Export**   | python-docx                      | Professionelle Word-Berichte                 |
| **Diagramme**     | Chart.js / Plotly                | Interaktive Verbrauchsdiagramme im Browser   |
| **Geocoding**     | OpenStreetMap Nominatim          | GPS → Adresse (kostenlos)                    |
| **Deployment**    | Docker + Caddy                   | SSL, Reverse Proxy                           |

---

## 3. Datenmodell

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    Benutzer     │       │    Gebaeude     │       │     Zaehler     │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id              │       │ id              │       │ id              │
│ telegram_id     │       │ name            │       │ gebaeude_id  ───┼──┐
│ name            │       │ adresse         │       │ zaehlernummer   │  │
│ rolle           │       │ gps_lat         │       │ typ (enum)      │  │
│ aktives_geb_id ─┼──┐    │ gps_lon         │       │ einheit         │  │
│ erstellt_am     │  │    │ notizen         │       │ standort_detail │  │
└─────────────────┘  │    │ erstellt_am     │       │ foto_pfad       │  │
                     │    └─────────────────┘       │ erstellt_am     │  │
                     │             ▲                └─────────────────┘  │
                     └─────────────┘                         ▲          │
                                                             │          │
┌─────────────────┐       ┌─────────────────┐               │          │
│   Ablesung      │       │  ZaehlerFoto    │               │          │
├─────────────────┤       ├─────────────────┤               │          │
│ id              │       │ id              │               │          │
│ zaehler_id   ───┼───────┼─► (FK)          │               │          │
│ benutzer_id     │       │ ablesung_id     │               │          │
│ stand           │       │ dateipfad       │               │          │
│ einheit         │       │ ki_roh_json     │               │          │
│ ablesedatum     │       │ erstellt_am     │               │          │
│ verbrauch       │       └─────────────────┘               │          │
│ verbrauch_pro_tag│                                        │          │
│ tage_seit_letzter│                                        │          │
│ ki_erkannt      │◄───────────────────────────────────────┘          │
│ ki_vertrauen    │                                                    │
│ notizen         │◄───────────────────────────────────────────────────┘
│ erstellt_am     │
└─────────────────┘

┌─────────────────┐
│    Bericht      │
├─────────────────┤
│ id              │
│ gebaeude_id     │
│ titel           │
│ zeitraum_von    │
│ zeitraum_bis    │
│ docx_pfad       │
│ erstellt_am     │
└─────────────────┘
```

### Zählertypen (Enum)

| Typ       | Icon | Einheit | Beschreibung              |
|-----------|------|---------|---------------------------|
| `strom`   | ⚡   | kWh     | Stromzähler               |
| `gas`     | 🔥   | m³      | Gaszähler                 |
| `wasser`  | 💧   | m³      | Wasserzähler (kalt/warm)  |
| `waerme`  | 🌡️   | kWh/MWh | Wärmemengenzähler         |
| `oel`     | 🛢️   | Liter   | Ölstandanzeige/Füllstand  |
| `solar`   | ☀️   | kWh     | PV-Einspeisezähler        |
| `sonstig` | 📊   | variabel| Andere Zähler             |

---

## 4. Telegram-Bot: Befehle & Interaktion

### 4.1 Befehle

| Befehl                  | Beschreibung                                      |
|-------------------------|--------------------------------------------------|
| `/start`                | Registrierung & Willkommensnachricht              |
| `/gebaeude <Name>`      | Neues Gebäude anlegen                             |
| `/wechsel`              | Aktives Gebäude wechseln (Inline-Buttons)         |
| `/zaehler`              | Zähler am aktiven Gebäude auflisten               |
| `/status`               | Zeigt aktives Gebäude & letzte Ablesungen         |
| `/bericht`              | Word-Bericht für aktives Gebäude generieren       |
| `/bericht <Zeitraum>`   | Bericht für bestimmten Zeitraum                   |
| `/export`               | CSV-Export aller Ablesungen                       |
| `/hilfe`                | Befehlsübersicht                                  |

### 4.2 Nachrichten-Verarbeitung (ohne Befehl)

Jede normale Nachricht wird intelligent verarbeitet:

- **Foto** → KI analysiert:
  1. Zählertyp erkennen (Strom/Gas/Wasser/Wärme...)
  2. Zählerstand ablesen (OCR)
  3. Zählernummer identifizieren (wenn lesbar)
  4. Mit vorhandenem Zähler abgleichen oder neuen anlegen
  5. Verbrauch seit letzter Ablesung berechnen
  
- **Standort teilen** → GPS wird dem aktiven Gebäude oder neuem Zähler zugeordnet
  
- **Sprachnachricht** → Whisper transkribiert → Notiz zur letzten Ablesung
  
- **Text** → Notiz oder manuelle Korrektur (`Stand: 12345.67`)

### 4.3 Beispiel-Dialog

```
Hausmeister: /start
Bot:         Willkommen bei der Zählererfassung! ⚡💧🔥
             Bitte gib deinen Namen ein.

Hausmeister: Thomas Müller
Bot:         Hallo Thomas! ✅
             Lege dein erstes Gebäude an mit /gebaeude <Name>

Hausmeister: /gebaeude Bürogebäude Hauptstraße 15
Bot:         ✅ Gebäude "Bürogebäude Hauptstraße 15" angelegt.
             📍 Teile den Standort, um die GPS-Position zu speichern.

Hausmeister: [📍 Standort geteilt]
Bot:         ✅ Adresse hinterlegt: Hauptstraße 15, 10115 Berlin

Hausmeister: [📷 Foto vom Stromzähler]
Bot:         🔍 Analysiere Zählerfoto...
             
             ⚡ **Stromzähler erkannt**
             📊 Zählerstand: 45.678,3 kWh
             🔢 Zählernummer: 1EMH0012345678
             
             ❓ Ist dies ein neuer Zähler oder eine Ablesung?
             [🆕 Neuer Zähler] [📖 Ablesung für #1]

Hausmeister: [Klickt: 🆕 Neuer Zähler]
Bot:         ✅ Stromzähler #1 angelegt
             📍 Wo befindet sich der Zähler?
             [Keller] [EG] [1.OG] [Technikraum] [Freitext]

Hausmeister: [Klickt: Keller]
Bot:         ✅ Zähler #1 im Keller gespeichert.
             
             📊 Erste Ablesung erfasst: 45.678,3 kWh
             ➡️ Verbrauchsberechnung ab nächster Ablesung möglich.

--- Einen Monat später ---

Hausmeister: [📷 Foto vom gleichen Stromzähler]
Bot:         🔍 Analysiere Zählerfoto...
             
             ⚡ **Stromzähler erkannt** (Zähler #1 – Keller)
             📊 Zählerstand: 46.234,1 kWh
             
             📈 **Verbrauch:**
             • Seit letzter Ablesung: 555,8 kWh
             • Zeitraum: 31 Tage
             • Durchschnitt: 17,9 kWh/Tag
             
             ✅ Ablesung gespeichert!

Hausmeister: War der Verbrauch normal?
Bot:         📊 Vergleich mit Vorperioden:
             • Vormonat: 520 kWh → +6,9% 📈
             • Vorjahr gleicher Monat: 490 kWh → +13,4% ⚠️
             
             💡 Der Verbrauch liegt über dem Vorjahr.
             Mögliche Ursachen: Mehr Heiztage, neue Verbraucher.

Hausmeister: /bericht
Bot:         📄 Bericht wird erstellt...
             [📎 Zählerbericht_Hauptstrasse_15_2026-03.docx]
```

---

## 5. KI-Verarbeitung

### 5.1 Zählerfoto-Analyse (GPT-4o Vision)

**Prompt-Konzept:**

```
Du bist ein Experte für Energiezähler und Messgeräte.
Analysiere dieses Foto eines Zählers und extrahiere:

1. ZÄHLERTYP (strom/gas/wasser/waerme/oel/solar/sonstig)
2. ZÄHLERSTAND (exakte Zahl mit Nachkommastellen)
3. EINHEIT (kWh, m³, MWh, Liter, etc.)
4. ZÄHLERNUMMER (wenn lesbar)
5. HERSTELLER/MODELL (wenn erkennbar)
6. QUALITÄT der Erkennung (0.0-1.0)

Antworte NUR mit validem JSON:
{
    "typ": "strom",
    "stand": 45678.3,
    "einheit": "kWh",
    "zaehlernummer": "1EMH0012345678",
    "hersteller": "EMH",
    "modell": "eHZ-K",
    "vertrauen": 0.95,
    "hinweise": "Gut lesbar, digitale Anzeige"
}
```

### 5.2 Verbrauchsberechnung

```python
def berechne_verbrauch(aktueller_stand, vorheriger_stand, tage_differenz):
    """Berechnet Verbrauch und Tagesdurchschnitt."""
    verbrauch = aktueller_stand - vorheriger_stand
    pro_tag = verbrauch / tage_differenz if tage_differenz > 0 else 0
    
    return {
        "verbrauch": verbrauch,
        "pro_tag": pro_tag,
        "hochrechnung_monat": pro_tag * 30,
        "hochrechnung_jahr": pro_tag * 365,
    }
```

### 5.3 Anomalie-Erkennung

- **Negativer Verbrauch** → Zähler rückwärts? Falsche Ablesung? ⚠️
- **Extremer Anstieg** (>50% über Durchschnitt) → Leck? Defekt? 🚨
- **Keine Bewegung** (Verbrauch = 0 über längeren Zeitraum) → Zähler defekt? 🔍
- **Plausibilitätsprüfung** → KI-Einschätzung ob Wert realistisch

---

## 6. Web-Dashboard (FastAPI + Jinja2)

### 6.1 Routen

| Route                     | Methode | Beschreibung                              |
|---------------------------|---------|-------------------------------------------|
| `/`                       | GET     | Gebäude-Übersicht mit Statistiken         |
| `/gebaeude/{id}`          | GET     | Gebäude-Detailseite mit Zählern           |
| `/zaehler/{id}`           | GET     | Zähler-Detailseite mit Ablesungen         |
| `/zaehler/{id}/diagramm`  | GET     | Verbrauchsdiagramm (JSON für Chart.js)    |
| `/bericht/{geb_id}/generieren` | POST | Word-Bericht erstellen                |
| `/bericht/{id}/download`  | GET     | Bericht herunterladen (DOCX)              |
| `/export/{geb_id}/csv`    | GET     | CSV-Export aller Ablesungen               |
| `/foto/{id}`              | GET     | Zählerfoto anzeigen                       |
| `/api/stats/{geb_id}`     | GET     | JSON-API: Statistiken für Diagramme       |

### 6.2 Dashboard-Features

- **Gebäude-Übersicht**
  - Alle Gebäude als Karten mit Statistiken
  - Anzahl Zähler, letzte Ablesung, Gesamtverbrauch
  
- **Gebäude-Detailseite**
  - Zähler-Tabelle mit Typ, Stand, letzter Ablesung
  - Verbrauchsdiagramm (Chart.js)
  - Filter nach Zählertyp, Zeitraum
  
- **Zähler-Detailseite**
  - Ablesungs-Historie als Tabelle
  - Verbrauchsverlauf als Liniendiagramm
  - Fotos der Ablesungen
  - Anomalie-Hinweise

- **Berichte & Export**
  - Word-Bericht auf Knopfdruck
  - CSV-Export für Excel

### 6.3 Template-Struktur

```
web/
├── app.py                 # FastAPI Routen
├── templates/
│   ├── base.html          # Basis-Template mit Navigation
│   ├── dashboard.html     # Gebäude-Übersicht
│   ├── gebaeude.html      # Gebäude-Detailseite
│   └── zaehler.html       # Zähler-Detailseite
└── static/
    ├── style.css          # Dashboard-Styling
    └── charts.js          # Chart.js Diagramm-Logik
```

---

## 7. Word-Berichte (python-docx)

### 7.1 Berichtstypen

| Bericht               | Inhalt                                          |
|-----------------------|------------------------------------------------|
| **Monats-Ablesung**   | Alle Ablesungen eines Monats mit Verbräuchen   |
| **Jahresbericht**     | Jahresverbrauch pro Zähler + Vergleich Vorjahr |
| **Gebäudebericht**    | Alle Zähler eines Gebäudes mit Historie        |
| **Anomalie-Report**   | Auffälligkeiten und Handlungsempfehlungen      |

### 7.2 Bericht-Struktur

```
┌─────────────────────────────────────────────────────────┐
│  ZÄHLERBERICHT                                          │
│  Gebäude: Hauptstraße 15                                │
│  Zeitraum: 01.03.2026 – 31.03.2026                      │
├─────────────────────────────────────────────────────────┤
│  ZUSAMMENFASSUNG                                        │
│  • 5 Zähler erfasst                                     │
│  • 12 Ablesungen im Zeitraum                            │
│  • Gesamtverbrauch Strom: 1.234 kWh                     │
│  • Gesamtverbrauch Gas: 456 m³                          │
├─────────────────────────────────────────────────────────┤
│  ZÄHLERÜBERSICHT                                        │
│  ┌─────────┬──────────┬───────────┬──────────┬────────┐ │
│  │ Zähler  │ Typ      │ Standort  │ Stand    │ Verbr. │ │
│  ├─────────┼──────────┼───────────┼──────────┼────────┤ │
│  │ #1      │ ⚡ Strom  │ Keller    │ 46.234   │ 556 kWh│ │
│  │ #2      │ 🔥 Gas    │ Heizraum  │ 12.345   │ 234 m³ │ │
│  │ ...     │ ...      │ ...       │ ...      │ ...    │ │
│  └─────────┴──────────┴───────────┴──────────┴────────┘ │
├─────────────────────────────────────────────────────────┤
│  VERBRAUCHSENTWICKLUNG                                  │
│  [Diagramm: Monatlicher Verbrauch der letzten 12 Monate]│
├─────────────────────────────────────────────────────────┤
│  AUFFÄLLIGKEITEN                                        │
│  ⚠️ Stromzähler #1: +13% gegenüber Vorjahr             │
│  ✅ Gaszähler #2: Im Normalbereich                      │
├─────────────────────────────────────────────────────────┤
│  FOTOS DER ABLESUNGEN                                   │
│  [Foto 1] [Foto 2] [Foto 3] ...                         │
└─────────────────────────────────────────────────────────┘
```

---

## 8. Projektstruktur

```
zaehlererfassung/
├── bot/
│   ├── __init__.py
│   ├── main.py              # Bot-Start & Handler-Registrierung
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py         # /start, Registrierung
│   │   ├── gebaeude.py      # /gebaeude, /wechsel, /status
│   │   ├── ablesung.py      # Foto-Verarbeitung, Zähler-Erkennung
│   │   ├── standort.py      # GPS-Standort verarbeiten
│   │   ├── bericht.py       # /bericht → Word generieren
│   │   └── export.py        # /export → CSV
│   └── keyboards.py         # Inline-Buttons & Menüs
├── core/
│   ├── __init__.py
│   ├── ki.py                # OpenAI API (Vision + Whisper)
│   ├── verbrauch.py         # Verbrauchsberechnung & Anomalien
│   ├── docx_export.py       # Word-Bericht-Generierung
│   └── geocoding.py         # GPS → Adresse (OpenStreetMap)
├── db/
│   ├── __init__.py
│   ├── database.py          # SQLAlchemy Session & Engine
│   └── models.py            # Datenmodell (Gebäude, Zähler, Ablesung)
├── web/
│   ├── app.py               # FastAPI Routen & Logik
│   ├── templates/
│   │   ├── base.html        # Basis-Template (Navigation, CSS)
│   │   ├── dashboard.html   # Gebäude-Übersicht
│   │   ├── gebaeude.html    # Gebäude-Detail mit Zählern
│   │   └── zaehler.html     # Zähler-Detail mit Ablesungen
│   └── static/
│       ├── style.css        # Dashboard-Styling
│       └── charts.js        # Diagramm-Logik (Chart.js)
├── templates/
│   └── bericht_template.docx  # Word-Vorlage (optional mit docxtpl)
├── uploads/                 # Zählerfotos
├── output/                  # Generierte Berichte
├── config.py                # Konfiguration aus .env
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── run.py                   # Launcher (Bot + Dashboard)
└── README.md
```

---

## 9. Umsetzungsplan (Phasen)

### Phase 1: MVP (Woche 1-2)
- [x] Projektplanung & Schema
- [ ] Telegram-Bot Grundgerüst (`/start`, `/hilfe`, `/gebaeude`)
- [ ] SQLite-Datenbank mit SQLAlchemy
- [ ] Foto-Upload & GPT-4o Vision Integration
- [ ] Zählerstand-Erkennung (Strom/Gas/Wasser)
- [ ] Einfache Verbrauchsberechnung
- [ ] Basis-Streamlit-Dashboard (Übersicht)

### Phase 2: Kernfunktionen (Woche 3-4)
- [ ] Alle Zählertypen unterstützen
- [ ] Automatischer Zähler-Abgleich (Wiedererkennung)
- [ ] GPS-Standort → Adresse
- [ ] Sprachnotizen (Whisper)
- [ ] Verbrauchshistorie & Diagramme im Dashboard
- [ ] Word-Bericht-Generierung

### Phase 3: Erweiterte Features (Woche 5-6)
- [ ] Anomalie-Erkennung & Alarme
- [ ] Jahresvergleiche & Trends
- [ ] Kartenansicht im Dashboard
- [ ] Mehrbenutzer-Unterstützung
- [ ] Passwort-Schutz (Bot + Dashboard)
- [ ] CSV/Excel-Export

### Phase 4: Optimierung & Deployment (Woche 7-8)
- [ ] Docker-Container & docker-compose
- [ ] Caddy Reverse Proxy mit SSL
- [ ] Automatische Backup-Strategie
- [ ] Performance-Optimierung
- [ ] Dokumentation für Endnutzer
- [ ] VPS-Deployment

---

## 10. Konfiguration & Secrets

```env
# .env
TELEGRAM_BOT_TOKEN=xxx              # von @BotFather
OPENAI_API_KEY=sk-xxx               # OpenAI API Key

# Datenbank
DATABASE_URL=sqlite:///zaehler.db

# Verzeichnisse
UPLOAD_DIR=./uploads
OUTPUT_DIR=./output

# Sicherheit
BOT_PASSWORT=                       # Leer = kein Schutz
DASHBOARD_PASSWORT=                 # Leer = kein Schutz

# Steuerung
BOT_AKTIV=true                      # false = nur Dashboard starten
DASHBOARD_PORT=8094                 # Web-Dashboard Port
```

---

## 11. Zusatz-Features (Nice-to-have)

### 11.1 Automatische Erinnerungen
- Telegram-Nachricht wenn Ablesung überfällig (z.B. >35 Tage)
- Monatsende-Erinnerung: "Vergiss nicht die Zähler abzulesen!"

### 11.2 QR-Code-System
- Jeder Zähler bekommt einen QR-Code-Aufkleber
- Scannen → Bot weiß sofort welcher Zähler → Foto-Aufforderung
- Eindeutige Zuordnung ohne KI-Erkennung

### 11.3 Benchmark-Vergleich
- Verbrauch pro m² Gebäudefläche
- Vergleich mit Durchschnittswerten (z.B. Heizung: 120 kWh/m²/Jahr)
- "Ihr Gebäude verbraucht 15% mehr Strom als vergleichbare Objekte"

### 11.4 Abrechnungs-Unterstützung
- Verbrauchsanteile für Nebenkostenabrechnung
- Export im DATEV-Format (für Steuerberater)

### 11.5 Multi-Mandanten
- Mehrere Hausverwaltungen mit getrennten Daten
- Admin-Dashboard zur Verwaltung

### 11.6 Push-Alarme
- Telegram-Benachrichtigung bei Anomalien
- E-Mail-Versand von Berichten

### 11.7 Offline-Modus (Zukunft)
- PWA-Dashboard für Offline-Nutzung
- Synchronisation wenn wieder online

---

## 12. Kosten-Schätzung (monatlich)

| Komponente       | Kosten        | Annahme                          |
|------------------|---------------|----------------------------------|
| OpenAI API       | ~10-30 €      | ~500 Foto-Analysen á 0.02-0.05 € |
| VPS (Hetzner)    | ~5-10 €       | CX22 oder höher                  |
| Domain + SSL     | ~0-1 €        | Subdomain, Caddy = gratis SSL    |
| **Gesamt**       | **~15-40 €**  |                                  |

---

## 13. Vorteile gegenüber manueller Erfassung

| Manuell (Excel)            | Zählererfassung Bot+Dashboard    |
|----------------------------|----------------------------------|
| Handschriftliche Notizen   | Foto → automatische Erkennung    |
| Tippfehler häufig          | KI-Plausibilitätsprüfung         |
| Kein Verbrauchsverlauf     | Automatische Diagramme           |
| Vergessene Ablesungen      | Erinnerungen per Telegram        |
| Excel-Chaos                | Strukturierte Datenbank          |
| Keine Historien            | Jahresvergleiche möglich         |
| Aufwändige Berichte        | Word-Bericht auf Knopfdruck      |

---

## Nächster Schritt

Soll ich mit **Phase 1 (MVP)** beginnen? Dafür benötige ich:

1. Einen **Telegram Bot Token** (erstellen via [@BotFather](https://t.me/botfather))
2. Einen **OpenAI API Key** (für Zähler-Erkennung)

Ich kann die Grundstruktur auch schon ohne Keys aufbauen – die Verbindung erfolgt dann später.
