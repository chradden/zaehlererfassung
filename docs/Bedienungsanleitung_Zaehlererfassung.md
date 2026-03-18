# Zählererfassung – Bedienungsanleitung

## Willkommen

Die Zählererfassung ist eine Kombination aus Telegram-Bot und Web-Dashboard zur automatischen Erfassung von Energiezählern. Sie fotografieren Ihre Zähler, die KI erkennt automatisch Typ und Stand, und das System berechnet Ihre Verbräuche über beliebige Zeiträume.

Die App ist für den einfachen Einsatz im Alltag gedacht:

- Zählerstand per Foto erfassen
- KI erkennt Zählertyp und -stand automatisch
- Verbrauchsberechnung seit der letzten Ablesung
- Gebäudeadresse per GPS-Standort hinterlegen
- Berichte als Word-Dokument erstellen
- Alle Daten im Web-Dashboard einsehen

---

## Inhaltsverzeichnis

1. [Was Sie brauchen](#1-was-sie-brauchen)
2. [Erste Schritte und Registrierung](#2-erste-schritte-und-registrierung)
3. [Ihr erstes Gebäude anlegen](#3-ihr-erstes-gebäude-anlegen)
4. [Adresse per Standort setzen](#4-adresse-per-standort-setzen)
5. [Zähler erfassen](#5-zähler-erfassen)
6. [KI-Erkennung und Verbrauchsberechnung](#6-ki-erkennung-und-verbrauchsberechnung)
7. [Gebäude wechseln und Status prüfen](#7-gebäude-wechseln-und-status-prüfen)
8. [Berichte und Exporte](#8-berichte-und-exporte)
9. [Das Web-Dashboard](#9-das-web-dashboard)
10. [Tipps für die Praxis](#10-tipps-für-die-praxis)
11. [Befehlsübersicht](#11-befehlsübersicht)
12. [Häufige Fragen](#12-häufige-fragen)

---

## 1. Was Sie brauchen

- **Telegram** auf Ihrem Smartphone (kostenlos für Android und iOS)
- Den **Link zum Bot** oder den Bot-Namen in der Telegram-Suche
- Das **Bot-Passwort**, falls der Zugang geschützt ist
- Optional: Zugangsdaten für das Web-Dashboard

Sie brauchen keine zusätzliche App. Die Erfassung läuft direkt über Telegram.

---

## 2. Erste Schritte und Registrierung

### So starten Sie:

1. Öffnen Sie den Bot in Telegram.
2. Tippen Sie auf **Start** oder senden Sie:

```
/start
```

3. Falls ein Passwortschutz aktiv ist, fragt der Bot zuerst das Zugangspasswort ab.
4. Danach geben Sie Ihren Namen ein.
5. Anschließend ist Ihr Benutzerkonto angelegt.

### Wichtig zum Passwortschutz

- Wenn ein Passwort eingerichtet ist, wird Ihre Passwort-Nachricht nach Möglichkeit direkt aus dem Chat gelöscht.
- Nach drei falschen Versuchen beendet der Bot den Vorgang und verweist auf den Administrator.

### Namen später ändern

Falls Ihr Name in Berichten angepasst werden soll, senden Sie:

```
/name Vorname Nachname
```

Beispiel:

```
/name Max Mustermann
```

---

## 3. Ihr erstes Gebäude anlegen

Bevor Sie Zähler erfassen, legen Sie ein Gebäude an. Alle Ablesungen werden immer dem aktuell aktiven Gebäude zugeordnet.

### Befehl:

```
/gebaeude Mein Haus
```

Der Bot legt das Gebäude an und aktiviert es sofort.

### Geeignete Gebäudenamen

- Einfamilienhaus Musterstraße 12
- Wohnung Berlin
- Bürogebäude Zentrale
- Ferienhaus Ostsee
- Mietobjekt Gartenweg 5

Nach der Anlage können Sie direkt loslegen und Fotos von Zählern senden.

---

## 4. Adresse per Standort setzen

Sie können die Gebäudeadresse automatisch aus Ihrem GPS-Standort übernehmen lassen. Das ist besonders praktisch, wenn Sie vor Ort sind.

### Schrittfolge:

1. Aktivieren Sie zuerst das gewünschte Gebäude.
2. Tippen Sie in Telegram auf das **Büroklammer-Symbol** (📎).
3. Wählen Sie **Standort**.
4. Senden Sie Ihren aktuellen Standort.
5. Der Bot übernimmt die Adresse automatisch per GPS.

### Alternative:

Senden Sie den Befehl:

```
/standort
```

Der Bot erklärt Ihnen dann die Schritte zum Teilen des Standorts.

Die Adresse wird später in Berichten und im Dashboard angezeigt.

---

## 5. Zähler erfassen

Das Herzstück der App: Fotografieren Sie einfach Ihre Zähler, und die KI erledigt den Rest.

### So funktioniert es:

1. Stellen Sie sicher, dass Sie das richtige Gebäude aktiv haben (`/status`).
2. Fotografieren Sie den Zähler – achten Sie darauf, dass der **Zählerstand gut lesbar** ist.
3. Senden Sie das Foto im Telegram-Chat.
4. Die KI analysiert das Bild und erkennt:
   - **Zählertyp** (Strom, Gas, Wasser, Wärme, Öl, Solar)
   - **Zählerstand**
   - **Zählernummer** (falls sichtbar)

### Beispiel-Ablauf:

```
Sie:    [📷 Foto vom Stromzähler]

Bot:    📷 Foto wird analysiert... 🤖

Bot:    ⚡ Stromzähler
        Stand: 12.345,67 kWh
        Zählernummer: 1EMH0012345678
        
        📊 Verbrauch seit letzter Ablesung:
        +234,5 kWh in 31 Tagen
        Ø 7,6 kWh/Tag
```

### Tipps für gute Fotos:

- **Gute Beleuchtung** – vermeiden Sie Schatten auf dem Display
- **Gerade fotografieren** – nicht schräg von der Seite
- **Nah genug** – der Zählerstand sollte den Großteil des Bildes einnehmen
- **Scharf** – warten Sie kurz, bis der Autofokus gegriffen hat

---

## 6. KI-Erkennung und Verbrauchsberechnung

### Was die KI erkennt:

| Zählertyp | Symbol | Einheit |
|-----------|--------|---------|
| Strom | ⚡ | kWh |
| Gas | 🔥 | m³ |
| Wasser | 💧 | m³ |
| Wärme/Fernwärme | ♨️ | kWh oder MWh |
| Öl | 🛢️ | Liter |
| Solar/PV | ☀️ | kWh |

### Verbrauchsberechnung

Sobald Sie einen Zähler zum zweiten Mal fotografieren, berechnet der Bot automatisch:

- **Verbrauch** seit der letzten Ablesung
- **Tage** zwischen den Ablesungen
- **Durchschnittsverbrauch** pro Tag

### Beispiel:

```
📊 Verbrauch berechnet:
   +156,3 kWh in 28 Tagen
   Ø 5,58 kWh/Tag
```

### Anomalie-Erkennung

Der Bot warnt Sie, wenn der Verbrauch ungewöhnlich hoch oder niedrig erscheint:

```
⚠️ Hinweis: Der Verbrauch ist deutlich höher als üblich.
   Bitte prüfen Sie den Zählerstand.
```

---

## 7. Gebäude wechseln und Status prüfen

### Zwischen Gebäuden wechseln

Wenn Sie mehrere Gebäude verwalten, können Sie einfach wechseln:

```
/wechsel
```

Der Bot zeigt Ihnen Buttons mit allen Ihren Gebäuden. Tippen Sie auf das gewünschte Gebäude, um es zu aktivieren.

### Status prüfen

Um zu sehen, welches Gebäude aktiv ist und welche Zähler erfasst wurden:

```
/status
```

Der Bot zeigt:
- Aktives Gebäude
- Anzahl der Zähler
- Übersicht der letzten Ablesungen

### Alle Zähler eines Gebäudes anzeigen

```
/zaehler
```

Listet alle Zähler des aktiven Gebäudes mit:
- Zählertyp und -nummer
- Letzter Stand und Datum
- Letzter Verbrauch

---

## 8. Berichte und Exporte

### Word-Bericht erstellen

Mit einem Befehl erhalten Sie einen professionellen Zählerbericht als Word-Dokument:

```
/bericht
```

Der Bericht enthält:
- Gebäudedaten und Zeitraum
- Übersicht aller Zähler
- Aktuelle Stände
- Verbrauchswerte
- Tabellarische Auflistung aller Ablesungen

Das Word-Dokument (.docx) wird direkt im Chat gesendet und kann auf dem Smartphone geöffnet oder weitergeleitet werden.

### CSV-Export

Für die Weiterverarbeitung in Excel:

```
/export
```

Der Bot sendet eine CSV-Datei mit allen Ablesungen:
- Zähler-ID, Typ, Standort
- Datum, Stand, Verbrauch
- Semikolon-getrennt (Excel-kompatibel)

---

## 9. Das Web-Dashboard

Neben dem Bot gibt es ein Web-Dashboard für die Übersicht am Computer.

### Anmeldung

Falls ein Passwort konfiguriert ist, fragt der Browser nach:
- **Benutzername:** (Standard: `admin`)
- **Passwort:** (vom Administrator festgelegt)

### Startseite – Gebäudeübersicht

Hier sehen Sie alle erfassten Gebäude mit:
- Anzahl der Zähler
- Letzte Ablesung
- Anzahl Ablesungen der letzten 30 Tage

Klicken Sie auf ein Gebäude, um die Details zu sehen.

### Gebäude-Detailseite

Zeigt alle Zähler des Gebäudes:
- Aktuelle Stände
- Letzter Verbrauch
- Zählertyp mit Farbcodierung

### Zähler-Detailseite

Für jeden Zähler gibt es eine eigene Seite mit:
- **Verlaufsdiagramm** – Zählerstand über Zeit
- **Verbrauchsdiagramm** – Verbrauch je Ablesung
- **Tabelle** aller Ablesungen
- Link zum Foto (falls vorhanden)

### Funktionen im Dashboard

- **Word-Bericht erstellen** – Button auf der Gebäudeseite
- **CSV-Export** – Download-Button
- **Fotos ansehen** – Klick auf das Kamera-Symbol in der Tabelle

---

## 10. Tipps für die Praxis

### Regelmäßig ablesen

- **Monatlich** ist ideal für aussagekräftige Verbrauchswerte
- Immer am gleichen Tag im Monat erleichtert Vergleiche
- Der Bot erinnert Sie nicht automatisch – setzen Sie sich selbst eine Erinnerung

### Mehrere Gebäude verwalten

1. Legen Sie für jedes Gebäude einen eigenen Eintrag an
2. Wechseln Sie mit `/wechsel` vor dem Fotografieren
3. Prüfen Sie mit `/status`, ob das richtige Gebäude aktiv ist

### Empfohlener Ablauf für einen Rundgang:

```
1. /wechsel → Gebäude auswählen
2. 📍 Standort teilen (einmalig pro Gebäude)
3. 📷 Fotos aller Zähler senden
4. /status → Prüfen, ob alles erfasst ist
5. /bericht → Dokumentation erstellen
```

### Bei der Erfassung vor Ort:

- Fotografieren Sie **alle** Zähler nacheinander
- Der Bot ordnet sie automatisch zu
- Notizen können Sie als Textnachricht ergänzen

---

## 11. Befehlsübersicht

| Befehl | Funktion |
|--------|----------|
| `/start` | Registrierung starten |
| `/name <Name>` | Eigenen Namen ändern |
| `/gebaeude <Name>` | Neues Gebäude anlegen und aktivieren |
| `/wechsel` | Aktives Gebäude wechseln |
| `/standort` | Anleitung zum Standort teilen |
| `/status` | Status des aktiven Gebäudes anzeigen |
| `/zaehler` | Alle Zähler des Gebäudes auflisten |
| `/bericht` | Word-Bericht erstellen |
| `/export` | CSV-Export erstellen |
| `/hilfe` | Befehlsübersicht anzeigen |

### Nachrichten ohne Befehl:

| Eingabe | Wirkung |
|---------|---------|
| 📷 Foto senden | Zähler erfassen |
| 📍 Standort teilen | Adresse hinterlegen |
| Text senden | Notiz zur letzten Ablesung |

---

## 12. Häufige Fragen

### Der Bot erkennt meinen Zähler nicht richtig.

Versuchen Sie es mit einem besseren Foto:
- Mehr Licht
- Näher ran
- Gerade fotografieren
- Warten bis das Bild scharf ist

Falls es trotzdem nicht klappt, können Sie den Stand manuell nachtragen, indem Sie eine Textnachricht mit dem Stand senden.

### Kann ich einen falschen Zählerstand korrigieren?

Im Moment nur über das Löschen und erneute Erfassen. Diese Funktion wird in einer späteren Version ergänzt.

### Ich habe ein Gebäude doppelt angelegt.

Nutzen Sie das Dashboard, um Gebäude zu verwalten. Im Bot selbst können Gebäude derzeit nicht gelöscht werden.

### Warum zeigt der Bot keinen Verbrauch an?

Der Verbrauch wird erst ab der **zweiten Ablesung** desselben Zählers berechnet. Bei der ersten Erfassung fehlt der Vergleichswert.

### Kann ich mehrere Gebäude gleichzeitig verwalten?

Ja. Sie wechseln einfach mit `/wechsel` zwischen den Gebäuden.

### Wer sieht das Dashboard?

Wenn ein Dashboard-Passwort gesetzt ist, nur Benutzer mit den Zugangsdaten. Ohne Passwortschutz ist das Dashboard offen erreichbar.

### Was passiert, wenn ich den Bot lösche?

Ihre Daten bleiben auf dem Server erhalten. Wenn Sie den Bot erneut starten, können Sie mit `/start` weitermachen – die KI erkennt Sie anhand Ihrer Telegram-ID.

### Unterstützt der Bot Fernwärmezähler?

Ja, die KI erkennt Wärmezähler automatisch und zeigt den Verbrauch in kWh oder MWh an.

### Kann ich auch Wasserzähler mit digitaler Anzeige erfassen?

Ja, die KI ist darauf trainiert, sowohl analoge Rollenzähler als auch digitale Displays zu erkennen.

---

## Kurz gesagt

Der einfachste Arbeitsablauf ist:

1. Mit `/start` anmelden
2. Mit `/gebaeude` ein Objekt anlegen
3. 📍 Standort teilen für die Adresse
4. 📷 Fotos der Zähler senden
5. Mit `/bericht` die Dokumentation erstellen
6. Im Dashboard Verläufe und Exporte abrufen

Damit haben Sie eine vollständige, automatisierte Zählererfassung direkt aus Telegram heraus.

---

## Noch Fragen?

Geben Sie im Bot jederzeit `/hilfe` ein, um eine Kurzübersicht aller Befehle zu erhalten. Bei technischen Problemen wenden Sie sich an Ihren Administrator.

**Viel Erfolg bei der Zählererfassung!** ⚡📊
