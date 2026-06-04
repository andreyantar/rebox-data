#!/usr/bin/env python3
"""Fetch Kaliningrad RSO container data from esoo39.ru and normalize to ReBox schema.

Output schema (sites.json):
  {
    "city": "kaliningrad",
    "sites": [
      {
        "id": "362196559",
        "lat": 54.7210017330816,
        "lng": 20.436263592649734,
        "address": "пр. Мира, 181",
        "fractions": ["paper", "metal", "plastic"],
        "container_type": "blue"
      }, ...
    ]
  }
"""
from __future__ import annotations
import hashlib
import json
import sys
import urllib.request
import ssl
from datetime import datetime, timezone
from pathlib import Path

SOURCE_URL = "https://new.esoo39.ru/js/maps/data.js?v=0.82"
CITY = "kaliningrad"
ROOT = Path(__file__).resolve().parent.parent
CITY_DIR = ROOT / "data" / CITY

PRESET_TO_FRACTIONS = {
    "islands#darkgreenIcon": (["paper", "metal", "plastic", "glass"], "green_4"),
    "islands#blueIcon":      (["paper", "metal", "plastic"],          "blue_3"),
    "islands#darkOrangeIcon":(["paper", "metal", "plastic"],          "orange_3"),
}


def fetch(url: str) -> bytes:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "ReBox-DataBot/1.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        return r.read()


def normalize(geojson: dict) -> list[dict]:
    sites = []
    skipped = []
    for f in geojson.get("features", []):
        preset = f.get("options", {}).get("preset")
        if preset not in PRESET_TO_FRACTIONS:
            skipped.append((f.get("id"), preset))
            continue
        fractions, ctype = PRESET_TO_FRACTIONS[preset]
        coords = f.get("geometry", {}).get("coordinates") or [None, None]
        lng, lat = coords[0], coords[1]
        if lat is None or lng is None:
            skipped.append((f.get("id"), "no-coords"))
            continue
        sites.append({
            "id": str(f.get("id")),
            "lat": lat,
            "lng": lng,
            "address": (f.get("properties", {}).get("iconCaption") or "").strip(),
            "fractions": fractions,
            "container_type": ctype,
        })
    if skipped:
        print(f"skipped {len(skipped)} features: {skipped[:5]}{'...' if len(skipped)>5 else ''}",
              file=sys.stderr)
    return sites


def main() -> int:
    CITY_DIR.mkdir(parents=True, exist_ok=True)
    raw = fetch(SOURCE_URL)
    geojson = json.loads(raw)
    if geojson.get("type") != "FeatureCollection":
        print(f"FATAL: expected FeatureCollection, got {geojson.get('type')!r}", file=sys.stderr)
        return 2

    sites = normalize(geojson)
    if not sites:
        print("FATAL: 0 sites after normalize — schema likely changed upstream", file=sys.stderr)
        return 3

    # raw snapshot (pretty-printed for readable git diff)
    raw_path = CITY_DIR / "raw.geojson"
    raw_path.write_text(json.dumps(geojson, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # normalized
    sites_payload = {"city": CITY, "sites": sites}
    sites_path = CITY_DIR / "sites.json"
    sites_text = json.dumps(sites_payload, ensure_ascii=False, indent=2) + "\n"
    sites_path.write_text(sites_text, encoding="utf-8")

    # meta
    sha = hashlib.sha256(sites_text.encode("utf-8")).hexdigest()
    meta = {
        "city": CITY,
        "source_url": SOURCE_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sites_count": len(sites),
        "sha256": sha,
    }
    (CITY_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")

    by_type = {}
    for s in sites:
        by_type[s["container_type"]] = by_type.get(s["container_type"], 0) + 1
    print(f"OK  city={CITY}  sites={len(sites)}  by_type={by_type}  sha={sha[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
