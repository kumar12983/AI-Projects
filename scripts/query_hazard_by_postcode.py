#!/usr/bin/env python3
"""
Query a map service for hazard features by postcode.

Usage examples:
  python scripts/query_hazard_by_postcode.py --postcode 2000 \
      --wfs-base https://ows.digitalearth.au/ows --layer dea:flood_extent

  python scripts/query_hazard_by_postcode.py --postcode 2000 \
      --arcgis "https://sampleserver6.arcgisonline.com/arcgis/rest/services/USA/MapServer/0" \
      --arcgis-mode

This script:
- Geocodes a postcode to a lat/lon using Nominatim (OpenStreetMap).
- Builds a small bbox around the point (configurable radius_km).
- Queries either a WFS `GetFeature` (GeoJSON) or an ArcGIS REST `query` endpoint
  and prints the returned GeoJSON or JSON.

Notes:
- Replace `--layer` with the exact WFS typeName for the provider you use.
- This is a helper script to run locally; services and layer names vary by provider.
"""
import argparse
import json
import math
import os
import sys
from urllib.parse import urlencode

import requests


def geocode_postcode(postcode: str):
    params = {
        'q': f'{postcode}, Australia',
        'format': 'json',
        'limit': 1,
    }
    url = 'https://nominatim.openstreetmap.org/search?' + urlencode(params)
    resp = requests.get(url, headers={'User-Agent': 'OpenAI-QueryScript/1.0'}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise RuntimeError(f'No geocode result for postcode {postcode}')
    return float(data[0]['lat']), float(data[0]['lon'])


def bbox_for_point(lat, lon, radius_km: float):
    # Approx conversion: 1 degree latitude ~= 111 km
    delta_deg = radius_km / 111.0
    miny = lat - delta_deg
    maxy = lat + delta_deg
    # longitude degrees scale by cos(lat)
    delta_lon = delta_deg / max(1e-6, math.cos(math.radians(lat)))
    minx = lon - delta_lon
    maxx = lon + delta_lon
    return (minx, miny, maxx, maxy)


def query_wfs(wfs_base: str, layer: str, bbox: tuple):
    params = {
        'service': 'WFS',
        'version': '2.0.0',
        'request': 'GetFeature',
        'typeName': layer,
        'bbox': f'{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]},EPSG:4326',
        'outputFormat': 'application/json',
    }
    url = wfs_base
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def query_arcgis(rest_url: str, lat: float, lon: float, radius_m: int = 1000):
    # Query features near the point using a buffer (geometry circle not supported by all servers)
    # We'll use geometry and geometryType=esriGeometryPoint with distance parameter when supported
    params = {
        'geometry': f'{lon},{lat}',
        'geometryType': 'esriGeometryPoint',
        'inSR': 4326,
        'outFields': '*',
        'f': 'json',
    }
    # Some ArcGIS services accept 'distance' and 'units'
    params['distance'] = radius_m
    params['units'] = 'esriSRUnit_Meter'
    resp = requests.get(rest_url.rstrip('/') + '/query', params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--postcode', required=True, help='Postcode to query')
    p.add_argument('--radius-km', type=float, default=1.0, help='Search radius in km')
    p.add_argument('--wfs-base', help='WFS base URL (e.g. https://ows.digitalearth.au/ows)')
    p.add_argument('--layer', help='WFS layer/typeName to query (required with --wfs-base)')
    p.add_argument('--arcgis', help='ArcGIS MapServer/FeatureServer layer URL (use with --arcgis-mode)')
    p.add_argument('--arcgis-mode', action='store_true', help='Use ArcGIS REST query instead of WFS')
    args = p.parse_args()

    lat, lon = geocode_postcode(args.postcode)
    print(f'Geocoded postcode {args.postcode} → lat={lat}, lon={lon}')
    bbox = bbox_for_point(lat, lon, args.radius_km)
    print('Query bbox (minx,miny,maxx,maxy)=', bbox)

    if args.arcgis_mode:
        if not args.arcgis:
            print('Error: --arcgis URL required with --arcgis-mode', file=sys.stderr)
            sys.exit(2)
        print('Querying ArcGIS REST endpoint...')
        out = query_arcgis(args.arcgis, lat, lon, int(args.radius_km * 1000))
        print(json.dumps(out, indent=2))
        return

    if args.wfs_base:
        if not args.layer:
            print('Error: --layer required when using --wfs-base', file=sys.stderr)
            sys.exit(2)
        print('Querying WFS GetFeature...')
        out = query_wfs(args.wfs_base, args.layer, bbox)
        print(json.dumps(out, indent=2))
        return

    print('Error: must specify --wfs-base/--layer or --arcgis with --arcgis-mode', file=sys.stderr)
    sys.exit(2)


if __name__ == '__main__':
    main()
