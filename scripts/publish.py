#!/usr/bin/env python3
"""Verrijk de gepinde PRONOM-catalogus met toepassingsgebieden."""

import argparse
import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = ROOT / "data" / "pronom_catalog.json"
TAXONOMY_PATH = ROOT / "data" / "pronom_taxonomy.yaml"
FORMAT_PROFILES_PATH = ROOT / "data" / "format_profiles.json"
OUTPUT_PATH = ROOT / "site" / "pronom-catalog.json"


def verrijk_pronom_catalogus(catalogus, taxonomy, format_profiles=None):
    if taxonomy.get("schema_versie") != 1:
        raise ValueError("pronom_taxonomy.yaml moet schema_versie 1 hebben")

    application_areas = taxonomy.get("toepassingsgebieden")
    if not isinstance(application_areas, dict) or not application_areas:
        raise ValueError("pronom_taxonomy.yaml moet toepassingsgebieden met labels bevatten")

    mappings = taxonomy.get("type_naar_toepassingsgebied", {})
    overrides = taxonomy.get("familie_overrides", {})
    bekende_gebieden = set(application_areas)
    if format_profiles is None:
        format_profiles = {}
    if not isinstance(format_profiles, dict):
        raise ValueError("format_profiles.json moet records per PUID bevatten")
    unknown_puids = set(format_profiles) - set(catalogus.get("records", {}))
    if unknown_puids:
        raise ValueError(f"onbekende PUID's in formaatprofielen: {sorted(unknown_puids)}")
    for type_naam, gebieden in mappings.items():
        onbekend = set(gebieden) - bekende_gebieden
        if onbekend:
            raise ValueError(f"onbekende toepassingsgebieden voor {type_naam}: {sorted(onbekend)}")

    niet_ingedeeld = 0
    for record in catalogus.get("records", {}).values():
        naam = record.get("formatName") or record.get("puid") or "Onbekend formaat"
        override = overrides.get(naam, {})
        familie_bron = record.get("formatFamilies")
        familie_label = override.get("label") or familie_bron or naam
        record["browse_family"] = {
            "id": override.get("id") or re.sub(r"[^a-z0-9]+", "-", familie_label.casefold()).strip("-"),
            "label": familie_label,
        }

        source_types = [
            item.strip()
            for item in (record.get("formatTypes") or "").split(",")
            if item.strip()
        ]
        gebieden = override.get("toepassingsgebieden")
        if gebieden is None:
            gebieden = sorted({
                gebied
                for source_type in source_types
                for gebied in mappings.get(source_type, [])
            })
        onbekend = set(gebieden) - bekende_gebieden
        if onbekend:
            raise ValueError(f"onbekende toepassingsgebieden voor {naam}: {sorted(onbekend)}")
        record["browse_application_areas"] = sorted(set(gebieden))
        if not record["browse_application_areas"]:
            niet_ingedeeld += 1

    catalogus["browse_taxonomy_version"] = taxonomy["schema_versie"]
    catalogus["browse_application_areas"] = application_areas
    catalogus["browse_unassigned_count"] = niet_ingedeeld
    catalogus["format_profiles"] = format_profiles
    return catalogus


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE_PATH)
    parser.add_argument("--taxonomy", type=Path, default=TAXONOMY_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    catalogus = json.loads(args.source.read_text(encoding="utf-8"))
    taxonomy = yaml.safe_load(args.taxonomy.read_text(encoding="utf-8")) or {}
    profile_document = json.loads(FORMAT_PROFILES_PATH.read_text(encoding="utf-8"))
    if profile_document.get("schema_version") != 1:
        raise ValueError("format_profiles.json moet schema_version 1 hebben")
    enriched = verrijk_pronom_catalogus(catalogus, taxonomy, profile_document.get("records", {}))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(enriched, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Gegenereerd: {enriched['aantal']} PRONOM-records, "
        f"{len(enriched['browse_application_areas'])} toepassingsgebieden, "
        f"{enriched['browse_unassigned_count']} niet ingedeeld"
    )


if __name__ == "__main__":
    main()
