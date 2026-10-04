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
INSTITUTIONS_DIRECTORY = ROOT / "data" / "institutions"
OUTPUT_PATH = ROOT / "site" / "pronom-catalog.json"
POLICY_STATUSES = {"Voorkeursformaat", "Geaccepteerd", "Legacy", "Open"}
KNOWLEDGE_LEVELS = {"Gekend", "Geidentificeerd", "In opslag"}


def load_institution_documents(directory):
    if not directory.is_dir():
        raise ValueError(f"Instellingenmap niet gevonden: {directory}")
    documents = []
    for path in sorted(directory.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        if document.get("schema_version") != 1:
            raise ValueError(f"{path.name} moet schema_version 1 hebben")
        if path.stem != document.get("id"):
            raise ValueError(f"Bestandsnaam en institution_id komen niet overeen: {path.name}")
        documents.append(document)
    return documents


def build_institution_profiles(institution_documents, format_profiles, catalog_records):
    if institution_documents is None:
        return []
    status_order = {"Voorkeursformaat": 0, "Geaccepteerd": 1, "Legacy": 2, "Open": 3}
    knowledge_order = {"Gekend": 0, "Geidentificeerd": 1, "In opslag": 2}
    pages = []
    seen_ids = set()
    for document in institution_documents:
        institution_id = document.get("id")
        name = document.get("name")
        if not institution_id or not name or institution_id in seen_ids:
            raise ValueError(f"Ontbrekende of dubbele institution_id/naam: {institution_id!r} / {name!r}")
        seen_ids.add(institution_id)
        if not isinstance(document.get("formats", []), list):
            raise ValueError(f"formats moet een lijst zijn voor instelling: {name}")
        formats = []
        seen_puids = set()
        for entry in document.get("formats", []):
            puid = entry.get("puid")
            if puid not in catalog_records:
                raise ValueError(f"Onbekende PUID in instellingsbestand {institution_id}: {puid}")
            if puid in seen_puids:
                raise ValueError(f"Dubbele PUID in instellingsbestand {institution_id}: {puid}")
            seen_puids.add(puid)
            policy_statuses = entry.get("policy_statuses", [])
            knowledge_levels = entry.get("knowledge_levels", [])
            if not isinstance(policy_statuses, list) or set(policy_statuses) - POLICY_STATUSES:
                raise ValueError(f"Ongeldig formaatbeleid in {institution_id} voor {puid}")
            if not isinstance(knowledge_levels, list) or set(knowledge_levels) - KNOWLEDGE_LEVELS:
                raise ValueError(f"Ongeldig kennisniveau in {institution_id} voor {puid}")
            record = catalog_records[puid]
            shared_profile = format_profiles.get(puid, {})
            shared_nara = shared_profile.get("nara_risk")
            formats.append({
                "puid": puid,
                "format_name": record.get("formatName") or puid,
                "version": record.get("version"),
                "family_name": entry.get("family_name"),
                "policy_statuses": sorted(set(policy_statuses), key=lambda value: (status_order.get(value, 99), value.casefold())),
                "knowledge_levels": sorted(set(knowledge_levels), key=lambda value: (knowledge_order.get(value, 99), value.casefold())),
                "nara_risk": {
                    "numeric_risk_rating": shared_nara.get("numeric_risk_rating"),
                    "numeric_risk_rating_range": shared_nara.get("numeric_risk_rating_range"),
                    "risk_level": shared_nara.get("risk_level"),
                } if shared_nara else None,
            })
        formats.sort(key=lambda item: (item["format_name"].casefold(), item["puid"]))
        page = {
            "id": institution_id,
            "name": name,
            "description": document.get("description"),
            "location": document.get("location"),
            "isil": document.get("isil"),
            "website_url": document.get("website_url"),
            "source_url": document.get("source_url"),
            "revision_timestamp": document.get("revision_timestamp"),
            "overview_sources": document.get("overview_sources", {}),
            "family_importance": document.get("family_importance", []),
            "formats": formats,
            "preferred_count": sum("Voorkeursformaat" in item["policy_statuses"] for item in formats),
        }
        pages.append(page)
    return sorted(pages, key=lambda item: item["name"].casefold())


def verrijk_pronom_catalogus(catalogus, taxonomy, format_profiles=None, institution_documents=None):
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
    if institution_documents is not None and not isinstance(institution_documents, list):
        raise ValueError("Instellingsbestanden moeten als lijst worden aangeleverd")
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
    catalogus["institution_profiles"] = build_institution_profiles(
        institution_documents, format_profiles, catalogus.get("records", {})
    )
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
    institution_documents = load_institution_documents(INSTITUTIONS_DIRECTORY)
    enriched = verrijk_pronom_catalogus(
        catalogus,
        taxonomy,
        profile_document.get("records", {}),
        institution_documents,
    )
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
