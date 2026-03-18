"""Inline-Keyboards für den Telegram Bot."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def gebaeude_auswahl_keyboard(gebaeude_liste):
    """Erstellt Inline-Keyboard zur Gebäudeauswahl."""
    buttons = []
    for g in gebaeude_liste:
        buttons.append([
            InlineKeyboardButton(
                f"🏢 {g.name}",
                callback_data=f"geb_{g.id}"
            )
        ])
    return InlineKeyboardMarkup(buttons)


def zaehler_auswahl_keyboard(zaehler_liste):
    """Erstellt Inline-Keyboard zur Zählerauswahl."""
    buttons = []
    for z in zaehler_liste:
        info = z.info
        buttons.append([
            InlineKeyboardButton(
                f"{info['icon']} #{z.id} – {z.standort_detail or z.typ}",
                callback_data=f"zaehler_{z.id}"
            )
        ])
    # Option für neuen Zähler
    buttons.append([
        InlineKeyboardButton("🆕 Neuer Zähler", callback_data="zaehler_neu")
    ])
    return InlineKeyboardMarkup(buttons)


def neuer_oder_ablesung_keyboard(zaehler_liste):
    """Fragt ob neuer Zähler oder Ablesung für bestehenden."""
    buttons = [
        [InlineKeyboardButton("🆕 Neuer Zähler anlegen", callback_data="zaehler_neu")]
    ]
    
    # Bestehende Zähler als Optionen
    for z in zaehler_liste[:5]:  # Max 5 Zähler anzeigen
        info = z.info
        label = z.standort_detail or z.zaehlernummer or f"#{z.id}"
        buttons.append([
            InlineKeyboardButton(
                f"📖 Ablesung für {info['icon']} {label}",
                callback_data=f"ablesung_{z.id}"
            )
        ])
    
    return InlineKeyboardMarkup(buttons)


def standort_keyboard():
    """Inline-Keyboard für Zähler-Standort."""
    buttons = [
        [
            InlineKeyboardButton("🏠 Keller", callback_data="standort_Keller"),
            InlineKeyboardButton("🚪 EG", callback_data="standort_EG"),
        ],
        [
            InlineKeyboardButton("⬆️ 1.OG", callback_data="standort_1.OG"),
            InlineKeyboardButton("⬆️ 2.OG", callback_data="standort_2.OG"),
        ],
        [
            InlineKeyboardButton("🔧 Technikraum", callback_data="standort_Technikraum"),
            InlineKeyboardButton("🏭 Heizraum", callback_data="standort_Heizraum"),
        ],
        [
            InlineKeyboardButton("📝 Anderer Ort...", callback_data="standort_custom"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def bestaetigung_keyboard(prefix="bestaetigen"):
    """Ja/Nein Bestätigung."""
    buttons = [
        [
            InlineKeyboardButton("✅ Ja", callback_data=f"{prefix}_ja"),
            InlineKeyboardButton("❌ Nein", callback_data=f"{prefix}_nein"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def zaehlertyp_keyboard():
    """Keyboard zur Zählertyp-Auswahl (falls KI unsicher)."""
    buttons = [
        [
            InlineKeyboardButton("⚡ Strom", callback_data="typ_strom"),
            InlineKeyboardButton("🔥 Gas", callback_data="typ_gas"),
        ],
        [
            InlineKeyboardButton("💧 Wasser", callback_data="typ_wasser"),
            InlineKeyboardButton("🌡️ Wärme", callback_data="typ_waerme"),
        ],
        [
            InlineKeyboardButton("🛢️ Öl", callback_data="typ_oel"),
            InlineKeyboardButton("☀️ Solar", callback_data="typ_solar"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)
