Query hazards by postcode (usage)
=================================

Quick usage notes for `scripts/query_hazard_by_postcode.py`.

Prerequisites
- Python 3.8+
- `requests` library: `pip install requests`

Examples

- Query a WFS layer (Digital Earth Australia example):

  ```bash
  python scripts/query_hazard_by_postcode.py \
    --postcode 2000 \
    --wfs-base "https://ows.digitalearth.au/ows" \
    --layer "dea:flood_extent" \
    --radius-km 2.0
  ```

- Query an ArcGIS REST layer (sample server):

  ```bash
  python scripts/query_hazard_by_postcode.py \
    --postcode 2000 \
    --arcgis "https://sampleserver6.arcgisonline.com/arcgis/rest/services/USA/MapServer/0" \
    --arcgis-mode --radius-km 1.0
  ```

Notes
- Replace `--layer` with the exact WFS `typeName` as returned by the provider's GetCapabilities.
- Replace `--arcgis` with a layer URL that supports `/query`.
- Many providers require API keys or access controls; if so, add headers to the script or use a proxy.

Output
- The script prints GeoJSON (WFS) or JSON (ArcGIS) to stdout. Pipe or save to a file for analysis.

If you want, I can add a small `requirements.txt` and a brief test run command next.
