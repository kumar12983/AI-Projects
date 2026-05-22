#!/usr/bin/env python3
"""
Discover Australian Flood Risk Information Portal (AFRIP) ArcGIS Services

Queries the ArcGIS REST API used by:
  https://experience.arcgis.com/experience/064d72c01bcb4d16979753545c4b72b4

Enumerates all available FeatureServer layers, their fields, and geometry types,
then writes a service_manifest.json for use by load_afrip_flood_data.py.

Usage:
    python discover_afrip_services.py [--save-manifest] [--timeout 30]

Outputs:
    afrip_service_manifest.json  (created with --save-manifest)
"""

import json
import sys
import argparse
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Known AFRIP service endpoints (Geoscience Australia / Digital Atlas)
# These are the primary FeatureServer services backing the AFRIP experience.
# The service discovery step below validates and augments this list at runtime.
# ─────────────────────────────────────────────────────────────────────────────
AFRIP_SERVICES = [
    {
        "name": "AFRIP_Flood_Studies",
        "description": "Flood study boundaries and metadata",
        "url": "https://services.ga.gov.au/gis/services/AFRIP/MapServer/WFSServer",
        "rest_url": "https://services.ga.gov.au/gis/rest/services/AFRIP/MapServer",
    },
    {
        "name": "AFRIP_Feature_Service",
        "description": "AFRIP FeatureServer – flood study polygons and points",
        "url": "https://services.ga.gov.au/gis/rest/services/AFRIP/FeatureServer",
        "rest_url": "https://services.ga.gov.au/gis/rest/services/AFRIP/FeatureServer",
    },
    # Digital Atlas hosted layers (ArcGIS Online – public)
    {
        "name": "AFRIP_FloodStudy_Areas",
        "description": "Flood study area polygons",
        "rest_url": (
            "https://services6.arcgis.com/MD9nRmWdXCW7XCWQ/arcgis/rest/services"
            "/AFRIP_FloodStudy_Extents/FeatureServer"
        ),
    },
    # Geoscience Australia AGOL services
    {
        "name": "GA_NationalFloodRisk",
        "description": "National flood risk layers",
        "rest_url": (
            "https://services.arcgis.com/HFPzFi9wAiuRCxVe/arcgis/rest/services"
            "/National_Flood_Risk_Index_Australia/FeatureServer"
        ),
    },
]

# Alternative base URLs to try if the above fail
FALLBACK_BASE_URLS = [
    "https://services.ga.gov.au/gis/rest/services/AFRIP",
    "https://flood.ga.gov.au/arcgis/rest/services",
    "https://services6.arcgis.com/MD9nRmWdXCW7XCWQ/arcgis/rest/services",
    "https://services.arcgis.com/HFPzFi9wAiuRCxVe/arcgis/rest/services",
]


def fetch_json(url: str, timeout: int = 30) -> dict | None:
    """Fetch JSON from an ArcGIS REST endpoint."""
    sep = "&" if "?" in url else "?"
    full_url = f"{url}{sep}f=json"
    try:
        req = urllib.request.Request(
            full_url,
            headers={
                "User-Agent": "Mozilla/5.0 (AFRIP-Loader/1.0)",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            data = json.loads(raw)
            if "error" in data:
                return None
            return data
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return None


def probe_service(rest_url: str, timeout: int = 30) -> dict | None:
    """Return service metadata if the URL is a live ArcGIS REST endpoint."""
    data = fetch_json(rest_url, timeout)
    if data and ("layers" in data or "services" in data or "serviceDescription" in data):
        return data
    return None


def get_layer_details(service_url: str, layer_id: int, timeout: int = 30) -> dict | None:
    """Fetch field and geometry metadata for a single layer."""
    url = f"{service_url}/{layer_id}"
    return fetch_json(url, timeout)


def discover_services(timeout: int = 30) -> list[dict]:
    """
    Try each known service URL and fall back to directory discovery.
    Returns a list of confirmed live services with their layer manifests.
    """
    live_services: list[dict] = []

    print("=" * 70)
    print("AFRIP Service Discovery")
    print("=" * 70)

    # 1. Probe known services
    for svc in AFRIP_SERVICES:
        url = svc["rest_url"]
        print(f"\n[PROBE] {svc['name']}")
        print(f"        {url}")
        data = probe_service(url, timeout)
        if data:
            print(f"  ✓ Live – found {len(data.get('layers', []))} layer(s)")
            layers = []
            for lyr in data.get("layers", []):
                lyr_detail = get_layer_details(url, lyr["id"], timeout)
                if lyr_detail:
                    layers.append(
                        {
                            "id": lyr["id"],
                            "name": lyr.get("name", f"layer_{lyr['id']}"),
                            "type": lyr_detail.get("type", "unknown"),
                            "geometryType": lyr_detail.get("geometryType", ""),
                            "fields": [
                                {
                                    "name": f["name"],
                                    "type": f["type"],
                                    "alias": f.get("alias", f["name"]),
                                    "length": f.get("length"),
                                    "nullable": f.get("nullable", True),
                                }
                                for f in lyr_detail.get("fields", [])
                            ],
                            "objectIdField": lyr_detail.get("objectIdField", "OBJECTID"),
                            "displayField": lyr_detail.get("displayField", ""),
                            "description": lyr_detail.get("description", ""),
                            "extent": lyr_detail.get("extent"),
                            "maxRecordCount": lyr_detail.get("maxRecordCount", 1000),
                        }
                    )
                time.sleep(0.2)
            live_services.append(
                {
                    "name": svc["name"],
                    "description": svc.get("description", ""),
                    "url": url,
                    "type": data.get("type", "FeatureServer"),
                    "layers": layers,
                }
            )
        else:
            print("  ✗ Not reachable")

    # 2. Try fallback base directories
    if not live_services:
        print("\n[INFO] Trying fallback service directories ...")
        for base in FALLBACK_BASE_URLS:
            data = fetch_json(base, timeout)
            if not data:
                continue
            for svc_entry in data.get("services", []):
                if any(
                    kw in svc_entry.get("name", "").lower()
                    for kw in ("flood", "afrip", "hazard")
                ):
                    svc_url = f"{base}/{svc_entry['name']}/{svc_entry['type']}"
                    svc_data = probe_service(svc_url, timeout)
                    if svc_data:
                        print(f"  ✓ Found: {svc_entry['name']} ({svc_entry['type']})")
                        live_services.append(
                            {
                                "name": svc_entry["name"],
                                "description": "",
                                "url": svc_url,
                                "type": svc_entry["type"],
                                "layers": [
                                    {"id": l["id"], "name": l.get("name", f"layer_{l['id']}")}
                                    for l in svc_data.get("layers", [])
                                ],
                            }
                        )

    return live_services


def print_summary(services: list[dict]) -> None:
    print("\n" + "=" * 70)
    print("Discovery Summary")
    print("=" * 70)
    if not services:
        print("No live AFRIP services found.")
        print()
        print("Possible reasons:")
        print("  • Services require authentication (token-based access)")
        print("  • Service URLs have changed since last update")
        print("  • Network/firewall restrictions")
        print()
        print("Next steps:")
        print("  1. Open the AFRIP portal in a browser:")
        print("     https://experience.arcgis.com/experience/064d72c01bcb4d16979753545c4b72b4")
        print("  2. Open browser DevTools → Network tab → reload the page")
        print("  3. Filter by 'FeatureServer' or 'MapServer' to find service URLs")
        print("  4. Update AFRIP_SERVICES in this script with the discovered URLs")
        print("  5. Re-run: python discover_afrip_services.py --save-manifest")
        return

    total_layers = sum(len(s.get("layers", [])) for s in services)
    print(f"Services found : {len(services)}")
    print(f"Total layers   : {total_layers}")
    print()
    for svc in services:
        print(f"  Service : {svc['name']}")
        print(f"  URL     : {svc['url']}")
        for lyr in svc.get("layers", []):
            geom = lyr.get("geometryType", "")
            nfields = len(lyr.get("fields", []))
            print(f"    Layer {lyr['id']:>3} | {lyr['name']:<40} | {geom:<25} | {nfields} fields")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--save-manifest",
        action="store_true",
        help="Write results to afrip_service_manifest.json",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP request timeout in seconds (default: 30)",
    )
    args = parser.parse_args()

    services = discover_services(timeout=args.timeout)
    print_summary(services)

    if args.save_manifest:
        manifest = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "portal_url": (
                "https://experience.arcgis.com/experience/064d72c01bcb4d16979753545c4b72b4"
            ),
            "services": services,
        }
        out_path = Path(__file__).parent / "afrip_service_manifest.json"
        out_path.write_text(json.dumps(manifest, indent=2))
        print(f"Manifest saved → {out_path}")


if __name__ == "__main__":
    main()
