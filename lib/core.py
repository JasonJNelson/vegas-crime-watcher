"""Shared crime data + ArcGIS helpers (stdlib only)."""
from __future__ import annotations

import json
import random
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

ARCGIS_QUERY_URL = (
    "https://services.arcgis.com/jjSk6t82vIntwDbs/ArcGIS/rest/services/"
    "LVMPD_Calls_For_Service_All/FeatureServer/0/query"
)

POLL_INTERVAL_SEC = 600
POLL_LIMIT = 150

SEED_CRIMES: list[dict] = [
    {"id": 1, "type": "homicide", "title": "Good Samaritan fatally shot trying to stop flower robbery", "address": "100 block Upland Blvd near Jones Blvd", "lat": 36.1595, "lng": -115.2238, "time": "2026-07-30 17:00", "description": "Man intervened when suspect robbed a woman selling flowers.", "source": "seed"},
    {"id": 2, "type": "shooting", "title": "Officer-involved shooting at Walmart — Boulder Hwy", "address": "5100 block Boulder Highway", "lat": 36.1002, "lng": -115.0615, "time": "2026-07-21 06:00", "description": "Physical altercation escalated; officer discharged.", "source": "seed"},
    {"id": 3, "type": "homicide", "title": "Gang-related shooting near Hollywood Regional Park", "address": "1500 block S Hollywood Blvd", "lat": 36.1520, "lng": -115.0450, "time": "2026-07-18 14:30", "description": "Fatal shooting; suspects arrested.", "source": "seed"},
    {"id": 4, "type": "robbery", "title": "Deadly parking-garage robbery spree (Strip area)", "address": "Fashion Show mall / Strip parking structures", "lat": 36.1275, "lng": -115.1715, "time": "2026-07-30 (court)", "description": "Robbery spree court case.", "source": "seed"},
    {"id": 5, "type": "homicide", "title": "Murder-suicide investigated", "address": "Las Vegas valley (LVMPD)", "lat": 36.1699, "lng": -115.1398, "time": "2026-07-21", "description": "LVMPD investigating murder-suicide.", "source": "seed"},
    {"id": 6, "type": "assault", "title": "Shooting leaves one dead — additional suspect arrested", "address": "West Las Vegas area", "lat": 36.1750, "lng": -115.2100, "time": "2026-07-27", "description": "Additional suspect arrested.", "source": "seed"},
    {"id": 7, "type": "theft", "title": "Vehicle theft cluster — Boulder Falls area", "address": "5800 Boulder Falls St", "lat": 36.0550, "lng": -115.0800, "time": "2026-07-28", "description": "Multiple vehicle theft reports.", "source": "seed"},
    {"id": 8, "type": "burglary", "title": "Residential burglary — N Buffalo Dr", "address": "2600 N Buffalo Dr", "lat": 36.1950, "lng": -115.2600, "time": "2026-07-25", "description": "Breaking & entering reported.", "source": "seed"},
    {"id": 9, "type": "robbery", "title": "Attempted business robbery — Flamingo / Jones area", "address": "Near Jones & Flamingo", "lat": 36.1150, "lng": -115.2250, "time": "2026-07-22", "description": "Suspect fled after attempted robbery.", "source": "seed"},
    {"id": 10, "type": "shooting", "title": "Shooting investigation — NE Las Vegas business", "address": "4900 block E Craig Rd near Nellis", "lat": 36.2400, "lng": -115.0600, "time": "2026-06-19 (still active case)", "description": "Man killed, woman injured.", "source": "seed"},
    {"id": 11, "type": "vandalism", "title": "Property damage / vandalism", "address": "7500 Hickam Ave", "lat": 36.0800, "lng": -115.2700, "time": "2026-07-15", "description": "Destruction/damage of property reported.", "source": "seed"},
    {"id": 12, "type": "theft", "title": "Larceny — Tropicana corridor", "address": "6100 W Tropicana Ave", "lat": 36.1000, "lng": -115.2300, "time": "2026-07-14", "description": "All other larceny reported.", "source": "seed"},
    {"id": 13, "type": "assault", "title": "Aggravated assault — Downtown area", "address": "Near Fremont St / Downtown", "lat": 36.1699, "lng": -115.1398, "time": "2026-07-26", "description": "Assault reported.", "source": "seed"},
    {"id": 14, "type": "burglary", "title": "Burglary — S Maryland Pkwy", "address": "4000 S Maryland Pkwy", "lat": 36.1200, "lng": -115.1400, "time": "2026-07-12", "description": "Commercial burglary under investigation.", "source": "seed"},
    {"id": 15, "type": "other", "title": "Vehicle vs pedestrian — fatal collision", "address": "W Sahara Ave at S Torrey Pines", "lat": 36.1440, "lng": -115.2700, "time": "2026-07-23", "description": "Fatal traffic collision.", "source": "seed"},
]

NEW_CRIME_POOL: list[dict] = [
    {"type": "theft", "title": "Catalytic converter theft reported", "address": "3200 block E Tropicana Ave", "lat": 36.1005, "lng": -115.1050, "description": "Vehicle parts theft."},
    {"type": "assault", "title": "Simple assault outside casino", "address": "Near Las Vegas Blvd / Flamingo", "lat": 36.1147, "lng": -115.1728, "description": "Altercation outside property."},
    {"type": "robbery", "title": "Strong-arm robbery — pedestrian", "address": "1600 block E Charleston Blvd", "lat": 36.1590, "lng": -115.1300, "description": "Phone and wallet taken."},
    {"type": "burglary", "title": "Garage burglary — Summerlin area", "address": "Near Far Hills / Town Center", "lat": 36.1650, "lng": -115.3200, "description": "Tools taken from open garage."},
    {"type": "shooting", "title": "Shots fired call — no victims located", "address": "2800 block N Las Vegas Blvd", "lat": 36.2050, "lng": -115.1200, "description": "Shell casings recovered."},
]

TYPE_MAP = [
    ("HOMICIDE", "homicide"), ("MURDER", "homicide"), ("SHOOTING", "shooting"), ("GUNSHOT", "shooting"),
    ("ROBBERY", "robbery"), ("ASSAULT", "assault"), ("BATTERY", "assault"), ("FIGHT", "assault"),
    ("BURGLARY", "burglary"), ("B&E", "burglary"), ("LARCENY", "theft"), ("THEFT", "theft"),
    ("STOLEN", "theft"), ("VEHICLE THEFT", "theft"), ("VANDALISM", "vandalism"), ("GRAFFITI", "vandalism"),
]


def classify_type(raw: str) -> str:
    upper = (raw or "").upper()
    for key, mapped in TYPE_MAP:
        if key in upper:
            return mapped
    return "other"


def fetch_lvmpd_cfs(limit: int = POLL_LIMIT) -> list[dict]:
    params = {
        "where": "1=1", "outFields": "*", "returnGeometry": "true",
        "orderByFields": "OBJECTID DESC", "resultRecordCount": str(limit), "f": "geojson",
    }
    url = ARCGIS_QUERY_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "VegasCrimeWatcher/1.0 (educational demo)"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    crimes: list[dict] = []
    for feat in payload.get("features") or []:
        props = feat.get("properties") or {}
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or [None, None]
        lng, lat = (coords + [None, None])[:2]
        incident_id = props.get("incidentnumber") or props.get("IncidentNumber") or props.get("EVENT_NUMBER") or props.get("OBJECTID")
        classification = props.get("Classification") or props.get("classification") or props.get("Type") or props.get("type") or props.get("CallType") or props.get("FinalType") or ""
        address = props.get("address") or props.get("Address") or props.get("LOCATION") or props.get("Location") or props.get("BlockAddress") or ""
        time_raw = props.get("timedispatch") or props.get("TimeDispatch") or props.get("CreateDate") or props.get("DATE") or props.get("CallDate") or ""
        if isinstance(time_raw, (int, float)) and time_raw > 1e11:
            try:
                time_str = datetime.utcfromtimestamp(time_raw / 1000).strftime("%Y-%m-%d %H:%M")
            except (OSError, ValueError, OverflowError):
                time_str = str(time_raw)
        else:
            time_str = str(time_raw) if time_raw else ""
        if lat is None or lng is None:
            lat = props.get("Latitude") or props.get("lat") or props.get("Y")
            lng = props.get("Longitude") or props.get("lng") or props.get("X")
        try:
            lat_f = float(lat) if lat is not None else None
            lng_f = float(lng) if lng is not None else None
        except (TypeError, ValueError):
            lat_f, lng_f = None, None
        if lat_f is None or lng_f is None:
            continue
        if not (35.8 < lat_f < 36.5 and -115.6 < lng_f < -114.7):
            continue
        ctype = classify_type(str(classification))
        title = str(classification).strip() or "Call for service"
        crimes.append({
            "id": f"lvmpd-{incident_id}", "type": ctype, "title": title,
            "address": str(address).strip() or "Las Vegas area",
            "lat": round(lat_f, 5), "lng": round(lng_f, 5), "time": time_str,
            "description": f"LVMPD Call for Service: {title}", "source": "lvmpd-arcgis",
        })
    return crimes


def random_simulated() -> dict:
    template = random.choice(NEW_CRIME_POOL)
    return {
        "id": f"sim-{int(datetime.now().timestamp())}-{random.randint(100, 999)}",
        **template,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "simulated",
    }
