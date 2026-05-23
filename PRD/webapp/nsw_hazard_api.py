"""
nsw_hazard_api.py
-----------------
Generic NSW Property Hazard Checker.

Queries the official NSW Government ePlanning ArcGIS REST services to return
Bushfire, Flood, Landslide, and Cyclone/Wind Zone hazard information for any
given NSW address.

USAGE (CLI):
    python nsw_hazard_api.py "68 Bingara Rd, Beecroft NSW 2119"
    python nsw_hazard_api.py "34 Avondale Ave, East Lismore NSW 2480"

USAGE (as importable module):
    from nsw_hazard_api import get_property_hazards
    result = get_property_hazards("68 Bingara Rd, Beecroft NSW 2119")
    print(result)

RETURNS:
    A dict with keys: address, coordinates, hazards, raw_results, errors
"""

import sys
import json
import argparse
import requests

# Force UTF-8 on Windows consoles (cp1252 cannot render unicode symbols)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

# Primary geocoder: NSW Spatial Portal Address Feature Service
NSW_GEOCODER_URL = (
    "https://portal.spatial.nsw.gov.au/server/rest/services/"
    "NSW_Geocoded_Addresses/FeatureServer/0/query"
)

# Fallback geocoder: Nominatim (OpenStreetMap) - no API key required
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# NSW ePlanning Hazard MapServer (identify endpoint queries all layers at once)
HAZARD_IDENTIFY_URL = (
    "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/"
    "ePlanning/Planning_Portal_Hazard/MapServer/identify"
)

# Layer IDs within the Planning_Portal_Hazard MapServer
# (based on published NSW ePlanning service directory)
HAZARD_LAYER_MAP = {
    0: "Bushfire",
    1: "Flood",
    2: "Landslide",
}

# BoM Wind Regions (AS/NZS 1170.2) approximate latitude thresholds for NSW.
# North of 25°S  → Region C/D (Cyclone country)
# 25°S – 33°S    → Region B (Sub-tropical, ex-cyclone risk)
# South of 33°S  → Region A (Temperate, standard)
WIND_REGIONS = [
    (-25.0, "C/D", "Tropical Cyclone Zone – design for Category 2–5 direct strike risk"),
    (-33.0, "B",   "Sub-Tropical – elevated wind risk; ex-cyclone events possible"),
    (None,  "A",   "Temperate – standard wind design; no direct tropical cyclone risk"),
]

REQUEST_TIMEOUT = 15  # seconds


# ---------------------------------------------------------------------------
# STEP 1: GEOCODING
# ---------------------------------------------------------------------------

def _geocode_nsw_portal(address: str) -> tuple[float, float] | None:
    """Try NSW Spatial Portal geocoder first (most accurate for NSW parcels)."""
    # Build a WHERE clause that accepts partial matches
    upper = address.upper()
    params = {
        "where": f"address_string LIKE '%{upper}%'",
        "outFields": "latitude,longitude,address_string",
        "resultRecordCount": 1,
        "f": "json",
    }
    try:
        r = requests.get(NSW_GEOCODER_URL, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        features = data.get("features", [])
        if features:
            attrs = features[0]["attributes"]
            lat = attrs.get("latitude")
            lng = attrs.get("longitude")
            if lat and lng:
                matched = attrs.get("address_string", address)
                return float(lat), float(lng), matched
    except Exception:
        pass
    return None


def _geocode_nominatim(address: str) -> tuple[float, float, str] | None:
    """Fallback geocoder via OpenStreetMap Nominatim."""
    params = {
        "q": address + ", NSW, Australia",
        "format": "json",
        "limit": 1,
        "countrycodes": "au",
    }
    headers = {"User-Agent": "NSW-Hazard-Checker/1.0"}
    try:
        r = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        results = r.json()
        if results:
            lat = float(results[0]["lat"])
            lng = float(results[0]["lon"])
            display = results[0].get("display_name", address)
            return lat, lng, display
    except Exception:
        pass
    return None


def geocode_address(address: str) -> dict:
    """
    Convert a free-text address into (lat, lng) coordinates.

    Tries:
      1. NSW Spatial Portal (most accurate for NSW properties)
      2. Nominatim / OpenStreetMap (fallback, no API key needed)

    Returns a dict with: lat, lng, matched_address, source, success
    """
    result = _geocode_nsw_portal(address)
    if result:
        lat, lng, matched = result
        return {"lat": lat, "lng": lng, "matched_address": matched,
                "source": "NSW Spatial Portal", "success": True}

    result = _geocode_nominatim(address)
    if result:
        lat, lng, matched = result
        return {"lat": lat, "lng": lng, "matched_address": matched,
                "source": "Nominatim (OpenStreetMap)", "success": True}

    return {"lat": None, "lng": None, "matched_address": None,
            "source": None, "success": False}


# ---------------------------------------------------------------------------
# STEP 2: WIND / CYCLONE REGION
# ---------------------------------------------------------------------------

def get_wind_region(lat: float) -> dict:
    """
    Determine the Australian Wind Region (AS/NZS 1170.2) for a given latitude.
    Returns: region, cyclone_risk (bool), description
    """
    for threshold, region, description in WIND_REGIONS:
        if threshold is None or lat > threshold:
            cyclone_risk = region in ("C/D",)
            elevated_wind = region in ("B", "C/D")
            return {
                "wind_region": region,
                "cyclone_direct_risk": cyclone_risk,
                "elevated_wind_risk": elevated_wind,
                "description": description,
            }
    # Should never reach here, but safe fallback
    return {"wind_region": "A", "cyclone_direct_risk": False,
            "elevated_wind_risk": False, "description": "Temperate"}


# ---------------------------------------------------------------------------
# STEP 3: NSW ePLANNING HAZARD LAYERS
# ---------------------------------------------------------------------------

def _build_hazard_defaults() -> dict:
    return {
        "Bushfire": {
            "detected": False,
            "label": "Not Detected",
            "detail": "Property does not intersect NSW Bushfire Prone Land (BFPL) mapping.",
            "raw_attributes": {},
        },
        "Flood": {
            "detected": False,
            "label": "Not Detected",
            "detail": "Property is not within a mapped Flood Planning Area (1% AEP or greater).",
            "raw_attributes": {},
        },
        "Landslide": {
            "detected": False,
            "label": "Not Detected",
            "detail": "Property does not intersect NSW Landslide Risk mapping.",
            "raw_attributes": {},
        },
    }


def query_eplanning_hazards(lat: float, lng: float) -> dict:
    """
    Query the NSW ePlanning Hazard MapServer at the given coordinates.
    Returns a dict of hazard results keyed by hazard type.
    """
    hazards = _build_hazard_defaults()
    errors = []

    extent = f"{lng - 0.002},{lat - 0.002},{lng + 0.002},{lat + 0.002}"
    params = {
        "geometry": json.dumps({"x": lng, "y": lat}),
        "geometryType": "esriGeometryPoint",
        "sr": "4326",
        "layers": "all",
        "tolerance": "5",
        "mapExtent": extent,
        "imageDisplay": "800,600,96",
        "returnGeometry": "false",
        "f": "json",
    }

    try:
        r = requests.get(HAZARD_IDENTIFY_URL, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()

        if "error" in data:
            errors.append(f"ArcGIS error {data['error'].get('code')}: {data['error'].get('message')}")
            return hazards, errors

        for feature in data.get("results", []):
            layer_id   = feature.get("layerId")
            layer_name = feature.get("layerName", "")
            attrs      = feature.get("attributes", {})

            hazard_key = HAZARD_LAYER_MAP.get(layer_id)

            # Also match by layer name keywords as a safety net
            if not hazard_key:
                name_lower = layer_name.lower()
                if "bushfire" in name_lower or "bush fire" in name_lower:
                    hazard_key = "Bushfire"
                elif "flood" in name_lower:
                    hazard_key = "Flood"
                elif "landslide" in name_lower or "land slide" in name_lower:
                    hazard_key = "Landslide"

            if hazard_key and hazard_key in hazards:
                detail = _extract_detail(hazard_key, attrs)
                hazards[hazard_key] = {
                    "detected": True,
                    "label": "DETECTED",
                    "detail": detail,
                    "raw_attributes": attrs,
                }

    except requests.exceptions.Timeout:
        errors.append("Request to NSW ePlanning timed out.")
    except requests.exceptions.ConnectionError:
        errors.append("Could not connect to NSW ePlanning service. Check network.")
    except Exception as e:
        errors.append(f"Unexpected error querying hazard service: {e}")

    return hazards, errors


def _extract_detail(hazard_key: str, attrs: dict) -> str:
    """Build a human-readable detail string from raw ArcGIS attributes."""
    if hazard_key == "Bushfire":
        category    = attrs.get("Category") or attrs.get("Category_Name") or attrs.get("CAT")
        guideline   = attrs.get("Guideline") or attrs.get("GUIDELINE")
        council     = attrs.get("Council_Name") or attrs.get("LGA_NAME")
        parts = ["Mapped as Bush Fire Prone Land (BFPL)"]
        if category:
            parts.append(f"Category: {category}")
        if guideline:
            parts.append(f"Guideline: {guideline}")
        if council:
            parts.append(f"Council: {council}")
        return " | ".join(parts)

    elif hazard_key == "Flood":
        desc   = (attrs.get("EP_LUT_DESC") or attrs.get("LABEL")
                  or attrs.get("FloodClass") or attrs.get("FLOOD_TYPE"))
        epi    = attrs.get("EPI_NAME") or attrs.get("Instrument")
        parts = ["Mapped within Flood Planning Area"]
        if desc:
            parts.append(f"Type: {desc}")
        if epi:
            parts.append(f"Instrument: {epi}")
        return " | ".join(parts)

    elif hazard_key == "Landslide":
        risk   = (attrs.get("Risk_Class") or attrs.get("RISK_CLASS")
                  or attrs.get("LandslideClass") or attrs.get("CLASS"))
        parts = ["Mapped within Landslide Risk area"]
        if risk:
            parts.append(f"Risk Class: {risk}")
        return " | ".join(parts)

    return f"Detected on layer. Raw: {attrs}"


# ---------------------------------------------------------------------------
# STEP 4: MASTER FUNCTION
# ---------------------------------------------------------------------------

def get_property_hazards(address: str) -> dict:
    """
    Master function. Given a free-text NSW address string, returns a complete
    hazard profile covering Bushfire, Flood, Landslide, and Cyclone/Wind Zone.

    Parameters
    ----------
    address : str
        e.g. "68 Bingara Rd, Beecroft NSW 2119"

    Returns
    -------
    dict with schema:
    {
        "address":       str,          # original input address
        "coordinates":   {             # geocoded result
            "lat": float,
            "lng": float,
            "matched_address": str,
            "geocode_source": str,
        },
        "hazards": {
            "Bushfire":  { "detected": bool, "label": str, "detail": str, "raw_attributes": dict },
            "Flood":     { "detected": bool, "label": str, "detail": str, "raw_attributes": dict },
            "Landslide": { "detected": bool, "label": str, "detail": str, "raw_attributes": dict },
            "Cyclone": {
                "wind_region": str,
                "cyclone_direct_risk": bool,
                "elevated_wind_risk": bool,
                "description": str,
            },
        },
        "errors": [str, ...]           # any non-fatal errors during lookup
    }
    """
    output = {
        "address": address,
        "coordinates": {},
        "hazards": {},
        "errors": [],
    }

    # --- Geocode ---
    geo = geocode_address(address)
    output["coordinates"] = {
        "lat": geo["lat"],
        "lng": geo["lng"],
        "matched_address": geo["matched_address"],
        "geocode_source": geo["source"],
    }

    if not geo["success"]:
        output["errors"].append(
            "Geocoding failed: could not resolve address to coordinates. "
            "Check the address format (e.g. '68 Bingara Rd Beecroft NSW 2119')."
        )
        return output

    lat, lng = geo["lat"], geo["lng"]

    # --- Cyclone/Wind Region (pure calculation, no API needed) ---
    output["hazards"]["Cyclone"] = get_wind_region(lat)

    # --- NSW ePlanning spatial hazards ---
    hazards, hazard_errors = query_eplanning_hazards(lat, lng)
    output["hazards"].update(hazards)
    output["errors"].extend(hazard_errors)

    return output


# ---------------------------------------------------------------------------
# STEP 5: FORMATTED PRINT
# ---------------------------------------------------------------------------

def print_hazard_report(result: dict):
    """Pretty-print the hazard result to stdout (ASCII-safe for all platforms)."""
    print("\n" + "=" * 60)
    print("  NSW PROPERTY HAZARD REPORT")
    print("=" * 60)
    print(f"  Input Address   : {result['address']}")

    coords = result.get("coordinates", {})
    if coords.get("matched_address"):
        print(f"  Matched Address : {coords['matched_address']}")
    if coords.get("lat"):
        print(f"  Coordinates     : Lat {coords['lat']:.5f}, Lng {coords['lng']:.5f}")
        print(f"  Geocode Source  : {coords['geocode_source']}")
    print("-" * 60)

    hazards = result.get("hazards", {})

    for key in ("Bushfire", "Flood", "Landslide"):
        h = hazards.get(key, {})
        icon = "[!]" if h.get("detected") else "[OK]"
        label = h.get("label", "N/A")
        detail = h.get("detail", "")
        print(f"\n  {icon} {key.upper()}: {label}")
        if detail:
            print(f"      {detail}")

    cyc = hazards.get("Cyclone", {})
    print(f"\n  [~] CYCLONE / WIND REGION: {cyc.get('wind_region', 'N/A')}")
    print(f"      Direct Cyclone Risk : {'YES' if cyc.get('cyclone_direct_risk') else 'No'}")
    print(f"      Elevated Wind Risk  : {'YES' if cyc.get('elevated_wind_risk') else 'No'}")
    print(f"      {cyc.get('description', '')}")

    errors = result.get("errors", [])
    if errors:
        print("\n  [WARN] WARNINGS / ERRORS:")
        for e in errors:
            print(f"      - {e}")

    print("\n" + "=" * 60 + "\n")


# ---------------------------------------------------------------------------
# CLI ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NSW Property Hazard Checker — Bushfire, Flood, Landslide, Cyclone"
    )
    parser.add_argument(
        "address",
        nargs="?",
        default=None,
        help='Property address, e.g. "68 Bingara Rd Beecroft NSW 2119"',
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted report",
    )
    parser.add_argument(
        "--batch",
        nargs="+",
        metavar="ADDRESS",
        help="Check multiple addresses in one run",
    )
    args = parser.parse_args()

    addresses = []
    if args.batch:
        addresses = args.batch
    elif args.address:
        addresses = [args.address]
    else:
        # Default demo: run both example addresses if no argument provided
        addresses = [
            "68 Bingara Rd, Beecroft NSW 2119",
            "34 Avondale Ave, East Lismore NSW 2480",
        ]

    for addr in addresses:
        result = get_property_hazards(addr)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_hazard_report(result)
