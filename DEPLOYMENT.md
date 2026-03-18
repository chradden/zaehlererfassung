# Deployment auf Hostinger VPS

## Voraussetzungen auf dem VPS

- Docker installiert
- Docker Compose installiert
- Git installiert
- Caddy als Reverse Proxy

---

## 1. Repository klonen

```bash
# Auf dem VPS einloggen
ssh user@dein-vps-ip

# Ins gewünschte Verzeichnis wechseln (z.B. /opt oder ~/apps)
cd /opt

# Repo klonen
git clone https://github.com/chradden/zaehlererfassung.git
cd zaehlererfassung
```

---

## 2. Umgebungsvariablen konfigurieren

Erstelle die `.env` Datei:

```bash
nano .env
```

Füge folgende Werte ein (mit deinen echten Credentials):

```env
# Telegram Bot Token (von @BotFather)
TELEGRAM_BOT_TOKEN=dein-telegram-token

# OpenAI API Key (für GPT-4o Vision)
OPENAI_API_KEY=dein-openai-key

# Bot-Passwort (optional – leerlassen für offenen Zugang)
BOT_PASSWORT=

# Dashboard-Zugangsdaten
DASHBOARD_USER=admin
DASHBOARD_PASSWORT=dein-sicheres-passwort

# Datenbank (SQLite Standard)
DATABASE_URL=sqlite:///./data/zaehlererfassung.db

# Dashboard Port
DASHBOARD_PORT=8060
```

Speichern mit `Ctrl+O`, schließen mit `Ctrl+X`.

---

## 3. Docker Container starten

```bash
# Container bauen und starten
docker compose up -d --build

# Logs prüfen
docker compose logs -f
```

Der Bot und das Dashboard starten automatisch. Das Dashboard ist auf Port 8060 erreichbar.

---

## 4. Caddy Reverse Proxy konfigurieren

Füge folgenden Block zu deiner Caddyfile hinzu:

```caddyfile
zaehler.christianradden.de {
        reverse_proxy localhost:8060
        }
}
```

Falls dein Caddyfile unter `/etc/caddy/Caddyfile` liegt:

```bash
sudo nano /etc/caddy/Caddyfile
```

Nach dem Hinzufügen Caddy neu laden:

```bash
sudo systemctl reload caddy
```

Caddy kümmert sich automatisch um das SSL-Zertifikat (Let's Encrypt).

---

## 5. DNS konfigurieren

Stelle sicher, dass bei Hostinger (oder deinem DNS-Provider) ein **A-Record** existiert:

| Typ | Name    | Wert           |
|-----|---------|----------------|
| A   | zaehler | deine-vps-ip   |

---

## Nützliche Befehle

```bash
# Container-Status prüfen
docker compose ps

# Logs anzeigen
docker compose logs -f

# Container neustarten
docker compose restart

# Container stoppen
docker compose down

# Update: Code holen und neu bauen
git pull
docker compose up -d --build
```

---

## Troubleshooting

### Port bereits belegt?
```bash
# Prüfen welcher Prozess Port 8060 nutzt
sudo lsof -i :8060
```

### Container startet nicht?
```bash
# Detaillierte Logs
docker compose logs zaehlererfassung

# Container manuell starten für Debug-Output
docker compose up
```

### Caddy findet den Service nicht?
```bash
# Testen ob der Port intern erreichbar ist
curl localhost:8060
```

---

## Firewall (falls aktiv)

Falls UFW aktiv ist, Caddy-Ports freigeben:

```bash
sudo ufw allow 80
sudo ufw allow 443
```

Port 8060 muss **nicht** extern freigegeben werden – Caddy greift intern darauf zu.
