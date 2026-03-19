"""FastAPI Web-Dashboard für Zählererfassung."""
import os
import io
import csv
import secrets
import logging
from datetime import date, datetime, timedelta
from fastapi import FastAPI, Request, Query, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import func

import config
from db.database import get_session
from db.models import Gebaeude, Benutzer, Zaehler, Ablesung, ZaehlerFoto, Bericht, Ordner, ZAEHLER_INFO
from core.docx_export import generiere_bericht

logger = logging.getLogger(__name__)

app = FastAPI(title="Zählererfassung Dashboard")
security = HTTPBasic()

# Static files & templates
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)


# ─── Auth ─────────────────────────────────────────────────────────────────

def auth_pruefen(credentials: HTTPBasicCredentials = Depends(security)):
    """Prüft HTTP Basic Auth, wenn DASHBOARD_PASSWORT gesetzt ist."""
    if not config.DASHBOARD_PASSWORT:
        return True  # Kein Schutz
    
    korrekt_user = secrets.compare_digest(credentials.username, config.DASHBOARD_USER)
    korrekt_pass = secrets.compare_digest(credentials.password, config.DASHBOARD_PASSWORT)
    
    if not (korrekt_user and korrekt_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige Zugangsdaten",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


# ─── Routen ───────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, auth=Depends(auth_pruefen)):
    """Hauptseite – Gebäudeübersicht mit Statistiken, gruppiert nach Ordnern."""
    with get_session() as session:
        # Ordner laden
        ordner_liste = session.query(Ordner).order_by(Ordner.reihenfolge, Ordner.name).all()
        
        # Gebäude laden
        gebaeude_liste = session.query(Gebaeude).all()
        
        # Gebäude-Daten sammeln
        def gebaeude_zu_dict(g):
            zaehler_count = session.query(Zaehler).filter_by(gebaeude_id=g.id).count()
            letzte_ablesung = (
                session.query(Ablesung)
                .join(Zaehler)
                .filter(Zaehler.gebaeude_id == g.id)
                .order_by(Ablesung.ablesedatum.desc())
                .first()
            )
            vor_30_tagen = date.today() - timedelta(days=30)
            ablesungen_30 = (
                session.query(Ablesung)
                .join(Zaehler)
                .filter(
                    Zaehler.gebaeude_id == g.id,
                    Ablesung.ablesedatum >= vor_30_tagen,
                )
                .count()
            )
            return {
                "id": g.id,
                "name": g.name,
                "adresse": g.adresse or "–",
                "ordner_id": g.ordner_id,
                "zaehler_count": zaehler_count,
                "letzte_ablesung": letzte_ablesung.ablesedatum if letzte_ablesung else None,
                "ablesungen_30_tage": ablesungen_30,
            }
        
        gebaeude_daten = [gebaeude_zu_dict(g) for g in gebaeude_liste]
        
        # Ordner-Daten mit Gebäuden
        ordner_daten = []
        for o in ordner_liste:
            ordner_daten.append({
                "id": o.id,
                "name": o.name,
                "gebaeude": [g for g in gebaeude_daten if g["ordner_id"] == o.id],
            })
        
        # Gebäude ohne Ordner
        ohne_ordner = [g for g in gebaeude_daten if g["ordner_id"] is None]
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "titel": "Zählererfassung",
            "ordner": ordner_daten,
            "ohne_ordner": ohne_ordner,
            "gebaeude": gebaeude_daten,  # Alle Gebäude (für Kompatibilität)
            "zaehler_info": ZAEHLER_INFO,
        },
    )


@app.get("/gebaeude/{gebaeude_id}", response_class=HTMLResponse)
async def gebaeude_detail(
    request: Request,
    gebaeude_id: int,
    auth=Depends(auth_pruefen),
):
    """Detailansicht eines Gebäudes mit Zählern."""
    with get_session() as session:
        gebaeude = session.get(Gebaeude, gebaeude_id)
        if not gebaeude:
            raise HTTPException(status_code=404, detail="Gebäude nicht gefunden")
        
        zaehler_liste = session.query(Zaehler).filter_by(gebaeude_id=gebaeude_id).all()
        
        zaehler_daten = []
        for z in zaehler_liste:
            info = ZAEHLER_INFO.get(z.typ, ZAEHLER_INFO["sonstig"])
            
            # Letzte Ablesungen
            ablesungen = (
                session.query(Ablesung)
                .filter_by(zaehler_id=z.id)
                .order_by(Ablesung.ablesedatum.desc())
                .limit(5)
                .all()
            )
            
            letzte = ablesungen[0] if ablesungen else None
            
            # Verbrauch der letzten Ablesung
            verbrauch_letzte = None
            if letzte and letzte.verbrauch is not None:
                verbrauch_letzte = letzte.verbrauch
            
            zaehler_daten.append({
                "id": z.id,
                "typ": z.typ,
                "info": info,
                "standort": z.standort_detail or "–",
                "zaehlernummer": z.zaehlernummer or "–",
                "letzter_stand": letzte.stand if letzte else None,
                "letzte_ablesung": letzte.ablesedatum if letzte else None,
                "verbrauch_letzte": verbrauch_letzte,
                "anzahl_ablesungen": len(ablesungen),
                "eichfrist_bis": z.eichfrist_bis,
                "eichstatus": z.eichstatus,
                "eichfrist_tage": z.eichfrist_tage,
                "eichdatum": z.eichdatum,
                "eichung_hinweis": z.eichung_hinweis,
            })
        
        return templates.TemplateResponse(
            "gebaeude.html",
            {
                "request": request,
                "titel": f"Zählererfassung – {gebaeude.name}",
                "gebaeude": {
                    "id": gebaeude.id,
                    "name": gebaeude.name,
                    "adresse": gebaeude.adresse,
                },
                "zaehler": zaehler_daten,
                "zaehler_info": ZAEHLER_INFO,
            },
        )


@app.get("/zaehler/{zaehler_id}", response_class=HTMLResponse)
async def zaehler_detail(
    request: Request,
    zaehler_id: int,
    auth=Depends(auth_pruefen),
):
    """Detailansicht eines Zählers mit allen Ablesungen."""
    with get_session() as session:
        zaehler = session.get(Zaehler, zaehler_id)
        if not zaehler:
            raise HTTPException(status_code=404, detail="Zähler nicht gefunden")
        
        gebaeude = session.get(Gebaeude, zaehler.gebaeude_id)
        info = ZAEHLER_INFO.get(zaehler.typ, ZAEHLER_INFO["sonstig"])
        
        # Alle Ablesungen laden
        ablesungen = (
            session.query(Ablesung)
            .filter_by(zaehler_id=zaehler_id)
            .order_by(Ablesung.ablesedatum.desc())
            .all()
        )
        
        ablesungen_daten = []
        for a in ablesungen:
            # Foto laden
            foto = session.query(ZaehlerFoto).filter_by(ablesung_id=a.id).first()
            
            ablesungen_daten.append({
                "id": a.id,
                "datum": a.ablesedatum,
                "stand": a.stand,
                "verbrauch": a.verbrauch,
                "verbrauch_pro_tag": a.verbrauch_pro_tag,
                "tage": a.tage_seit_letzter,
                "ki_erkannt": a.ki_erkannt,
                "notizen": a.notizen,
                "foto_id": foto.id if foto else None,
            })
        
        # Daten für Diagramm (chronologisch)
        chart_labels = [a.ablesedatum.strftime("%d.%m.%Y") for a in reversed(ablesungen)]
        chart_staende = [a.stand for a in reversed(ablesungen)]
        chart_verbrauch = [a.verbrauch or 0 for a in reversed(ablesungen)]
        
        return templates.TemplateResponse(
            "zaehler.html",
            {
                "request": request,
                "titel": f"Zähler #{zaehler_id}",
                "gebaeude": {
                    "id": gebaeude.id,
                    "name": gebaeude.name,
                },
                "zaehler": {
                    "id": zaehler.id,
                    "typ": zaehler.typ,
                    "info": info,
                    "standort": zaehler.standort_detail or "–",
                    "zaehlernummer": zaehler.zaehlernummer or "–",
                    "hersteller": zaehler.hersteller,
                    "modell": zaehler.modell,
                    "eichfrist_bis": zaehler.eichfrist_bis,
                    "eichstatus": zaehler.eichstatus,
                    "eichfrist_tage": zaehler.eichfrist_tage,
                    "eichdatum": zaehler.eichdatum,
                    "eichung_hinweis": zaehler.eichung_hinweis,
                },
                "ablesungen": ablesungen_daten,
                "chart_labels": chart_labels,
                "chart_staende": chart_staende,
                "chart_verbrauch": chart_verbrauch,
            },
        )


@app.get("/foto/{foto_id}")
async def foto_anzeigen(foto_id: int, auth=Depends(auth_pruefen)):
    """Foto anzeigen."""
    with get_session() as session:
        foto = session.get(ZaehlerFoto, foto_id)
        if not foto or not os.path.exists(foto.dateipfad):
            raise HTTPException(status_code=404, detail="Foto nicht gefunden")
        
        return FileResponse(foto.dateipfad, media_type="image/jpeg")


@app.get("/bericht/{bericht_id}/download")
async def bericht_download(bericht_id: int, auth=Depends(auth_pruefen)):
    """Word-Bericht herunterladen."""
    with get_session() as session:
        bericht = session.get(Bericht, bericht_id)
        if not bericht or not bericht.docx_pfad or not os.path.exists(bericht.docx_pfad):
            raise HTTPException(status_code=404, detail="Bericht nicht gefunden")
        
        return FileResponse(
            bericht.docx_pfad,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=os.path.basename(bericht.docx_pfad),
        )


@app.post("/gebaeude/{gebaeude_id}/bericht")
async def bericht_generieren_web(gebaeude_id: int, auth=Depends(auth_pruefen)):
    """Generiert einen Word-Bericht für ein Gebäude."""
    von_datum = date.today() - timedelta(days=30)
    bis_datum = date.today()
    
    with get_session() as session:
        gebaeude = session.get(Gebaeude, gebaeude_id)
        if not gebaeude:
            raise HTTPException(status_code=404, detail="Gebäude nicht gefunden")
        
        zaehler_liste = session.query(Zaehler).filter_by(gebaeude_id=gebaeude_id).all()
        
        zaehler_daten = []
        for z in zaehler_liste:
            info = ZAEHLER_INFO.get(z.typ, ZAEHLER_INFO["sonstig"])
            
            ablesungen = (
                session.query(Ablesung)
                .filter(
                    Ablesung.zaehler_id == z.id,
                    Ablesung.ablesedatum >= von_datum,
                    Ablesung.ablesedatum <= bis_datum,
                )
                .order_by(Ablesung.ablesedatum)
                .all()
            )
            
            verbrauch_zeitraum = None
            aktueller_stand = None
            if ablesungen:
                aktueller_stand = ablesungen[-1].stand
                if len(ablesungen) >= 2:
                    verbrauch_zeitraum = ablesungen[-1].stand - ablesungen[0].stand
            
            zaehler_daten.append({
                "id": z.id,
                "typ": z.typ,
                "info": info,
                "standort": z.standort_detail or "",
                "zaehlernummer": z.zaehlernummer or "",
                "ablesungen": [
                    {"datum": a.ablesedatum, "stand": a.stand, "verbrauch": a.verbrauch}
                    for a in ablesungen
                ],
                "verbrauch_zeitraum": verbrauch_zeitraum,
                "aktueller_stand": aktueller_stand,
            })
        
        docx_pfad = generiere_bericht(
            gebaeude_name=gebaeude.name,
            gebaeude_adresse=gebaeude.adresse,
            von_datum=von_datum,
            bis_datum=bis_datum,
            zaehler_daten=zaehler_daten,
            ersteller="Dashboard",
        )
        
        # In DB speichern
        bericht = Bericht(
            gebaeude_id=gebaeude_id,
            titel=f"Zählerbericht {gebaeude.name}",
            zeitraum_von=von_datum,
            zeitraum_bis=bis_datum,
            docx_pfad=docx_pfad,
        )
        session.add(bericht)
        session.flush()
        bericht_id = bericht.id
    
    return RedirectResponse(url=f"/bericht/{bericht_id}/download", status_code=303)


@app.get("/export/{gebaeude_id}/csv")
async def export_csv(gebaeude_id: int, auth=Depends(auth_pruefen)):
    """Exportiert Ablesungen als CSV."""
    with get_session() as session:
        gebaeude = session.get(Gebaeude, gebaeude_id)
        if not gebaeude:
            raise HTTPException(status_code=404, detail="Gebäude nicht gefunden")
        
        zaehler_liste = session.query(Zaehler).filter_by(gebaeude_id=gebaeude_id).all()
        
        rows = []
        for z in zaehler_liste:
            info = ZAEHLER_INFO.get(z.typ, ZAEHLER_INFO["sonstig"])
            
            ablesungen = (
                session.query(Ablesung)
                .filter_by(zaehler_id=z.id)
                .order_by(Ablesung.ablesedatum)
                .all()
            )
            
            for a in ablesungen:
                rows.append({
                    "Zähler-ID": z.id,
                    "Typ": info["name"],
                    "Standort": z.standort_detail or "",
                    "Zählernummer": z.zaehlernummer or "",
                    "Datum": a.ablesedatum.strftime("%d.%m.%Y"),
                    "Stand": f"{a.stand:.2f}",
                    "Einheit": info["einheit"],
                    "Verbrauch": f"{a.verbrauch:.2f}" if a.verbrauch else "",
                })
        
        if not rows:
            raise HTTPException(status_code=404, detail="Keine Ablesungen vorhanden")
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=rows[0].keys(), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
        
        safe_name = gebaeude.name.replace(" ", "_")
        filename = f"Zaehler_{safe_name}_{date.today().strftime('%Y-%m-%d')}.csv"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


@app.get("/api/stats/{gebaeude_id}")
async def api_stats(gebaeude_id: int, auth=Depends(auth_pruefen)):
    """JSON-API: Statistiken für Diagramme."""
    with get_session() as session:
        gebaeude = session.get(Gebaeude, gebaeude_id)
        if not gebaeude:
            raise HTTPException(status_code=404, detail="Gebäude nicht gefunden")
        
        # Zähler nach Typ zählen
        zaehler_count = session.query(Zaehler).filter_by(gebaeude_id=gebaeude_id).count()
        
        # Verbrauch nach Typ
        verbrauch_nach_typ = {}
        zaehler_liste = session.query(Zaehler).filter_by(gebaeude_id=gebaeude_id).all()
        
        for z in zaehler_liste:
            info = ZAEHLER_INFO.get(z.typ, ZAEHLER_INFO["sonstig"])
            
            # Letzten Verbrauch
            letzte = (
                session.query(Ablesung)
                .filter_by(zaehler_id=z.id)
                .order_by(Ablesung.ablesedatum.desc())
                .first()
            )
            
            if letzte and letzte.verbrauch:
                if z.typ not in verbrauch_nach_typ:
                    verbrauch_nach_typ[z.typ] = {
                        "name": info["name"],
                        "einheit": info["einheit"],
                        "verbrauch": 0,
                    }
                verbrauch_nach_typ[z.typ]["verbrauch"] += letzte.verbrauch
        
        return {
            "gebaeude_id": gebaeude_id,
            "zaehler_count": zaehler_count,
            "verbrauch_nach_typ": verbrauch_nach_typ,
        }


# ─── Ordner-Verwaltung ───────────────────────────────────────────────────

@app.post("/api/ordner")
async def ordner_erstellen(request: Request, auth=Depends(auth_pruefen)):
    """Neuen Ordner erstellen."""
    data = await request.json()
    name = data.get("name", "").strip()
    
    if not name:
        raise HTTPException(status_code=400, detail="Name erforderlich")
    
    with get_session() as session:
        ordner = Ordner(name=name)
        session.add(ordner)
        session.flush()
        return {"id": ordner.id, "name": ordner.name}


@app.put("/api/ordner/{ordner_id}")
async def ordner_umbenennen(ordner_id: int, request: Request, auth=Depends(auth_pruefen)):
    """Ordner umbenennen."""
    data = await request.json()
    name = data.get("name", "").strip()
    
    if not name:
        raise HTTPException(status_code=400, detail="Name erforderlich")
    
    with get_session() as session:
        ordner = session.get(Ordner, ordner_id)
        if not ordner:
            raise HTTPException(status_code=404, detail="Ordner nicht gefunden")
        ordner.name = name
        return {"id": ordner.id, "name": ordner.name}


@app.delete("/api/ordner/{ordner_id}")
async def ordner_loeschen(ordner_id: int, auth=Depends(auth_pruefen)):
    """Ordner löschen (Gebäude bleiben erhalten, werden aus Ordner entfernt)."""
    with get_session() as session:
        ordner = session.get(Ordner, ordner_id)
        if not ordner:
            raise HTTPException(status_code=404, detail="Ordner nicht gefunden")
        
        # Gebäude aus Ordner entfernen
        session.query(Gebaeude).filter_by(ordner_id=ordner_id).update({"ordner_id": None})
        session.delete(ordner)
        return {"success": True}


@app.put("/api/gebaeude/{gebaeude_id}/ordner")
async def gebaeude_in_ordner(gebaeude_id: int, request: Request, auth=Depends(auth_pruefen)):
    """Gebäude einem Ordner zuweisen oder aus Ordner entfernen."""
    data = await request.json()
    ordner_id = data.get("ordner_id")  # None = aus Ordner entfernen
    
    with get_session() as session:
        gebaeude = session.get(Gebaeude, gebaeude_id)
        if not gebaeude:
            raise HTTPException(status_code=404, detail="Gebäude nicht gefunden")
        
        if ordner_id is not None:
            ordner = session.get(Ordner, ordner_id)
            if not ordner:
                raise HTTPException(status_code=404, detail="Ordner nicht gefunden")
        
        gebaeude.ordner_id = ordner_id
        return {"success": True, "ordner_id": ordner_id}


# ─── Eichfrist-Verwaltung ────────────────────────────────────────────────

@app.put("/api/zaehler/{zaehler_id}/eichung")
async def eichung_aktualisieren(zaehler_id: int, request: Request, auth=Depends(auth_pruefen)):
    """Eichfrist eines Zählers manuell setzen oder aktualisieren."""
    data = await request.json()
    
    with get_session() as session:
        zaehler = session.get(Zaehler, zaehler_id)
        if not zaehler:
            raise HTTPException(status_code=404, detail="Zähler nicht gefunden")
        
        eichdatum_str = data.get("eichdatum")
        eichfrist_bis_str = data.get("eichfrist_bis")
        eichung_hinweis = data.get("eichung_hinweis")
        
        if eichdatum_str:
            try:
                zaehler.eichdatum = date.fromisoformat(eichdatum_str)
            except ValueError:
                raise HTTPException(status_code=400, detail="Ungültiges Eichdatum (Format: YYYY-MM-DD)")
        
        if eichfrist_bis_str:
            try:
                zaehler.eichfrist_bis = date.fromisoformat(eichfrist_bis_str)
            except ValueError:
                raise HTTPException(status_code=400, detail="Ungültiges Eichfrist-Datum (Format: YYYY-MM-DD)")
        
        if eichung_hinweis is not None:
            zaehler.eichung_hinweis = eichung_hinweis
        
        return {
            "success": True,
            "zaehler_id": zaehler.id,
            "eichdatum": str(zaehler.eichdatum) if zaehler.eichdatum else None,
            "eichfrist_bis": str(zaehler.eichfrist_bis) if zaehler.eichfrist_bis else None,
            "eichstatus": zaehler.eichstatus,
        }


@app.get("/api/eichfristen", response_class=HTMLResponse)
async def eichfristen_uebersicht(request: Request, auth=Depends(auth_pruefen)):
    """Übersicht aller Zähler mit Eichfrist-Status."""
    with get_session() as session:
        zaehler_liste = session.query(Zaehler).all()
        
        ergebnis = []
        for z in zaehler_liste:
            gebaeude = session.get(Gebaeude, z.gebaeude_id)
            info = ZAEHLER_INFO.get(z.typ, ZAEHLER_INFO["sonstig"])
            ergebnis.append({
                "zaehler_id": z.id,
                "gebaeude_name": gebaeude.name if gebaeude else "–",
                "gebaeude_id": z.gebaeude_id,
                "typ": info["name"],
                "icon": info["icon"],
                "zaehlernummer": z.zaehlernummer or "–",
                "standort": z.standort_detail or "–",
                "eichdatum": str(z.eichdatum) if z.eichdatum else None,
                "eichfrist_bis": str(z.eichfrist_bis) if z.eichfrist_bis else None,
                "eichstatus": z.eichstatus,
                "eichfrist_tage": z.eichfrist_tage,
                "eichung_hinweis": z.eichung_hinweis,
            })
        
        # Sortieren: abgelaufen zuerst, dann warnung, dann ok, dann unbekannt
        status_order = {"abgelaufen": 0, "warnung": 1, "ok": 2, "unbekannt": 3}
        ergebnis.sort(key=lambda x: (status_order.get(x["eichstatus"], 4), x.get("eichfrist_tage") or 99999))
        
        return templates.TemplateResponse(
            "eichfristen.html",
            {
                "request": request,
                "titel": "Eichfristen-Übersicht (DIN ISO 50001)",
                "zaehler": ergebnis,
            },
        )
