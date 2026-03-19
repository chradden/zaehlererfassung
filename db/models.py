"""SQLAlchemy Datenmodelle für Zählererfassung."""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
import enum

from db.database import Base


class ZaehlerTyp(enum.Enum):
    """Zählertypen mit Icons und Einheiten."""
    strom = "strom"
    gas = "gas"
    wasser = "wasser"
    waerme = "waerme"
    oel = "oel"
    solar = "solar"
    sonstig = "sonstig"


# Mapping für Anzeige
ZAEHLER_INFO = {
    "strom": {"icon": "⚡", "einheit": "kWh", "name": "Strom"},
    "gas": {"icon": "🔥", "einheit": "m³", "name": "Gas"},
    "wasser": {"icon": "💧", "einheit": "m³", "name": "Wasser"},
    "waerme": {"icon": "🌡️", "einheit": "kWh", "name": "Wärme"},
    "oel": {"icon": "🛢️", "einheit": "Liter", "name": "Öl"},
    "solar": {"icon": "☀️", "einheit": "kWh", "name": "Solar"},
    "sonstig": {"icon": "📊", "einheit": "", "name": "Sonstig"},
}


class Ordner(Base):
    """Ordner zur Gruppierung von Gebäuden."""
    __tablename__ = "ordner"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    reihenfolge = Column(Integer, default=0)  # Für Sortierung
    erstellt_am = Column(DateTime, default=datetime.now)

    # Relationships
    gebaeude = relationship("Gebaeude", back_populates="ordner")


class Benutzer(Base):
    """Telegram-Benutzer."""
    __tablename__ = "benutzer"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    aktives_gebaeude_id = Column(Integer, ForeignKey("gebaeude.id"), nullable=True)
    erstellt_am = Column(DateTime, default=datetime.now)

    # Relationships
    aktives_gebaeude = relationship("Gebaeude", foreign_keys=[aktives_gebaeude_id])
    ablesungen = relationship("Ablesung", back_populates="benutzer")


class Gebaeude(Base):
    """Gebäude/Standort mit Zählern."""
    __tablename__ = "gebaeude"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    adresse = Column(String(300), nullable=True)
    ordner_id = Column(Integer, ForeignKey("ordner.id"), nullable=True)  # Optional: Ordner-Zuordnung
    gps_lat = Column(Float, nullable=True)
    gps_lon = Column(Float, nullable=True)
    notizen = Column(Text, nullable=True)
    erstellt_am = Column(DateTime, default=datetime.now)

    # Relationships
    ordner = relationship("Ordner", back_populates="gebaeude")
    zaehler = relationship("Zaehler", back_populates="gebaeude", cascade="all, delete-orphan")
    berichte = relationship("Bericht", back_populates="gebaeude", cascade="all, delete-orphan")


class Zaehler(Base):
    """Einzelner Zähler in einem Gebäude."""
    __tablename__ = "zaehler"

    id = Column(Integer, primary_key=True)
    gebaeude_id = Column(Integer, ForeignKey("gebaeude.id"), nullable=False)
    zaehlernummer = Column(String(100), nullable=True)  # Vom Typenschild
    typ = Column(String(20), nullable=False, default="strom")  # strom, gas, wasser, etc.
    einheit = Column(String(20), nullable=True)  # kWh, m³, etc.
    standort_detail = Column(String(200), nullable=True)  # z.B. "Keller", "Technikraum"
    hersteller = Column(String(100), nullable=True)
    modell = Column(String(100), nullable=True)
    eichdatum = Column(Date, nullable=True)  # Datum der letzten Eichung
    eichfrist_bis = Column(Date, nullable=True)  # Eichfrist gültig bis
    eichung_hinweis = Column(String(300), nullable=True)  # KI-Hinweis oder manueller Kommentar
    notizen = Column(Text, nullable=True)
    erstellt_am = Column(DateTime, default=datetime.now)

    # Relationships
    gebaeude = relationship("Gebaeude", back_populates="zaehler")
    ablesungen = relationship("Ablesung", back_populates="zaehler", cascade="all, delete-orphan")

    @property
    def info(self):
        """Gibt Icon, Einheit und Name für den Zählertyp zurück."""
        return ZAEHLER_INFO.get(self.typ, ZAEHLER_INFO["sonstig"])

    @property
    def letzte_ablesung(self):
        """Gibt die letzte Ablesung zurück."""
        if self.ablesungen:
            return max(self.ablesungen, key=lambda a: a.ablesedatum)
        return None

    @property
    def eichstatus(self):
        """Gibt den Eichstatus zurück: 'ok', 'warnung', 'abgelaufen', 'unbekannt'."""
        if not self.eichfrist_bis:
            return "unbekannt"
        from datetime import timedelta
        heute = date.today()
        if self.eichfrist_bis < heute:
            return "abgelaufen"
        elif self.eichfrist_bis <= heute + timedelta(days=365):
            return "warnung"
        return "ok"

    @property
    def eichfrist_tage(self):
        """Gibt die Anzahl der Tage bis zum Ablauf der Eichfrist zurück (negativ = abgelaufen)."""
        if not self.eichfrist_bis:
            return None
        return (self.eichfrist_bis - date.today()).days


class Ablesung(Base):
    """Einzelne Zählerablesung."""
    __tablename__ = "ablesung"

    id = Column(Integer, primary_key=True)
    zaehler_id = Column(Integer, ForeignKey("zaehler.id"), nullable=False)
    benutzer_id = Column(Integer, ForeignKey("benutzer.id"), nullable=False)
    
    # Messwerte
    stand = Column(Float, nullable=False)
    einheit = Column(String(20), nullable=True)
    ablesedatum = Column(Date, nullable=False, default=date.today)
    
    # Berechnete Werte (werden beim Speichern berechnet)
    verbrauch = Column(Float, nullable=True)  # Differenz zur vorherigen Ablesung
    verbrauch_pro_tag = Column(Float, nullable=True)  # Verbrauch / Tage
    tage_seit_letzter = Column(Integer, nullable=True)  # Tage seit letzter Ablesung
    
    # KI-Erkennung
    ki_erkannt = Column(Integer, default=0)  # 1 = per KI erkannt, 0 = manuell
    ki_vertrauen = Column(Float, nullable=True)  # 0.0 - 1.0
    
    notizen = Column(Text, nullable=True)
    erstellt_am = Column(DateTime, default=datetime.now)

    # Relationships
    zaehler = relationship("Zaehler", back_populates="ablesungen")
    benutzer = relationship("Benutzer", back_populates="ablesungen")
    fotos = relationship("ZaehlerFoto", back_populates="ablesung", cascade="all, delete-orphan")


class ZaehlerFoto(Base):
    """Foto einer Zählerablesung."""
    __tablename__ = "zaehler_foto"

    id = Column(Integer, primary_key=True)
    ablesung_id = Column(Integer, ForeignKey("ablesung.id"), nullable=False)
    dateipfad = Column(String(500), nullable=False)
    ki_roh_json = Column(Text, nullable=True)  # Rohe KI-Antwort
    erstellt_am = Column(DateTime, default=datetime.now)

    # Relationships
    ablesung = relationship("Ablesung", back_populates="fotos")


class Bericht(Base):
    """Generierter Word-Bericht."""
    __tablename__ = "bericht"

    id = Column(Integer, primary_key=True)
    gebaeude_id = Column(Integer, ForeignKey("gebaeude.id"), nullable=False)
    titel = Column(String(200), nullable=False)
    zeitraum_von = Column(Date, nullable=True)
    zeitraum_bis = Column(Date, nullable=True)
    docx_pfad = Column(String(500), nullable=True)
    erstellt_am = Column(DateTime, default=datetime.now)

    # Relationships
    gebaeude = relationship("Gebaeude", back_populates="berichte")
