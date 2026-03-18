"""Verbrauchsberechnung und Anomalie-Erkennung."""
from datetime import date


def berechne_verbrauch(
    aktueller_stand: float,
    vorheriger_stand: float,
    aktuelles_datum: date,
    vorheriges_datum: date,
) -> dict:
    """
    Berechnet Verbrauch zwischen zwei Ablesungen.
    
    Returns:
        dict mit verbrauch, pro_tag, tage, hochrechnung_monat, hochrechnung_jahr
    """
    verbrauch = aktueller_stand - vorheriger_stand
    tage = (aktuelles_datum - vorheriges_datum).days
    
    pro_tag = verbrauch / tage if tage > 0 else 0
    
    return {
        "verbrauch": round(verbrauch, 2),
        "pro_tag": round(pro_tag, 2),
        "tage": tage,
        "hochrechnung_monat": round(pro_tag * 30, 2),
        "hochrechnung_jahr": round(pro_tag * 365, 2),
    }


def pruefe_anomalie(
    aktueller_verbrauch: float,
    durchschnitt_verbrauch: float,
    schwellwert_prozent: float = 50.0,
) -> dict:
    """
    Prüft ob der aktuelle Verbrauch anomal ist.
    
    Args:
        aktueller_verbrauch: Verbrauch der aktuellen Periode
        durchschnitt_verbrauch: Durchschnittsverbrauch der Vergleichsperioden
        schwellwert_prozent: Ab welcher Abweichung ist es eine Anomalie (default: 50%)
    
    Returns:
        dict mit ist_anomalie, abweichung_prozent, typ (hoch/niedrig/negativ)
    """
    if durchschnitt_verbrauch == 0:
        return {
            "ist_anomalie": False,
            "abweichung_prozent": 0,
            "typ": None,
            "meldung": None,
        }
    
    # Negativer Verbrauch ist immer anomal
    if aktueller_verbrauch < 0:
        return {
            "ist_anomalie": True,
            "abweichung_prozent": None,
            "typ": "negativ",
            "meldung": "⚠️ Negativer Verbrauch! Zählerstand prüfen oder Zählertausch.",
        }
    
    abweichung = ((aktueller_verbrauch - durchschnitt_verbrauch) / durchschnitt_verbrauch) * 100
    
    if abs(abweichung) >= schwellwert_prozent:
        if abweichung > 0:
            return {
                "ist_anomalie": True,
                "abweichung_prozent": round(abweichung, 1),
                "typ": "hoch",
                "meldung": f"📈 Verbrauch {abweichung:+.1f}% über Durchschnitt!",
            }
        else:
            return {
                "ist_anomalie": True,
                "abweichung_prozent": round(abweichung, 1),
                "typ": "niedrig",
                "meldung": f"📉 Verbrauch {abweichung:.1f}% unter Durchschnitt.",
            }
    
    return {
        "ist_anomalie": False,
        "abweichung_prozent": round(abweichung, 1),
        "typ": None,
        "meldung": None,
    }


def berechne_durchschnitt(ablesungen: list) -> float:
    """
    Berechnet den durchschnittlichen Tagesverbrauch aus einer Liste von Ablesungen.
    
    Args:
        ablesungen: Liste von Ablesung-Objekten (mit stand und ablesedatum)
    
    Returns:
        Durchschnittlicher Tagesverbrauch
    """
    if len(ablesungen) < 2:
        return 0
    
    # Sortieren nach Datum
    sorted_ablesungen = sorted(ablesungen, key=lambda a: a.ablesedatum)
    
    gesamt_verbrauch = 0
    gesamt_tage = 0
    
    for i in range(1, len(sorted_ablesungen)):
        vorher = sorted_ablesungen[i - 1]
        aktuell = sorted_ablesungen[i]
        
        verbrauch = aktuell.stand - vorher.stand
        tage = (aktuell.ablesedatum - vorher.ablesedatum).days
        
        if verbrauch >= 0 and tage > 0:  # Nur positive Werte
            gesamt_verbrauch += verbrauch
            gesamt_tage += tage
    
    return gesamt_verbrauch / gesamt_tage if gesamt_tage > 0 else 0


def formatiere_verbrauch(wert: float, einheit: str, dezimalen: int = 1) -> str:
    """Formatiert einen Verbrauchswert mit Tausender-Trennung."""
    return f"{wert:,.{dezimalen}f} {einheit}".replace(",", "X").replace(".", ",").replace("X", ".")
