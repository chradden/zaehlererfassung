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
from db.models import Gebaeude, Benutzer, Zaehler, Ablesung, ZaehlerFoto, Bericht, ZAEHLER_INFO
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
    """Hauptseite – Gebäudeübersicht mit Statistiken."""
    with get_session() as session:
        gebaeude_liste = session.query(Gebaeude).all()
        
        gebaeude_daten = []
        for g in gebaeude_liste:
            # Zähler zählen
            zaehler_count = session.query(Zaehler).filter_by(gebaeude_id=g.id).count()
            
            # Letzte Ablesung
            letzte_ablesung = (
                session.query(Ablesung)
                .join(Zaehler)
                .filter(Zaehler.gebaeude_id == g.id)
                .order_by(Ablesung.ablesedatum.desc())
                .first()
            )
            
            # Verbrauch letzter 30 Tage (vereinfacht)
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
            
            gebaeude_daten.append({
                "id": g.id,
                "name": g.name,
                "adresse": g.adresse or "–",
                "zaehler_count": zaehler_count,
                "letzte_ablesung": letzte_ablesung.ablesedatum if letzte_ablesung else None,
                "ablesungen_30_tage": ablesungen_30,
            })
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "titel": "Zählererfassung",
            "gebaeude": gebaeude_daten,
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
