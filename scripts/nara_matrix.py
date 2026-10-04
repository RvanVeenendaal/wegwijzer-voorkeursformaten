#!/usr/bin/env python3
"""Replace legacy durability values with data from the downloaded NARA matrix."""

import argparse
import csv
from datetime import datetime
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROFILES_PATH = ROOT / "data" / "format_profiles.json"
CATALOG_PATH = ROOT / "data" / "pronom_catalog.json"
MATRIX_PATH = ROOT / "data" / "NARA_File_Format_Risk_Matrix_20260320_Numbered.csv"
CROSSWALK_PATH = ROOT / "data" / "nara_crosswalk.csv"
WEIGHTS_PATH = ROOT / "data" / "NARA_File_Format_Risk_Matrix_Weights_20241218.csv"
MATRIX_SOURCE_URL = "https://github.com/usnationalarchives/digital-preservation/blob/master/Digital_Preservation_Risk_Matrix/NARA_File_Format_Risk_Matrix_20260320_Numbered.csv"
WEIGHTS_SOURCE_URL = "https://github.com/usnationalarchives/digital-preservation/blob/master/Supporting_Documentation/Risk_Matrix_Weights/NARA_File_Format_Risk_Matrix_Weights_20241218.csv"
WEIGHTS_TOTAL_COLUMN = "TOTAL NARA Risk Level Numeric Score"
SCORE_RANGE_PATTERN = re.compile(
    r"Highest possible score\s*=\s*(-?\d+)\s*;\s*Lowest possible score\s*=\s*(-?\d+)",
    re.IGNORECASE,
)
CATEGORY_COLUMNS = (
    ("Disclosure", "1: TOTAL Disclosure Score"),
    ("Adoption", "2: TOTAL Adoption Score"),
    ("Transparency", "3: TOTAL Transparency Score"),
    ("Self-Documentation", "4: TOTAL Self-Documentation Score"),
    ("External Hardware Dependencies", "5: TOTAL External Hardware Dependencies Score"),
    ("External Software Dependencies", "6: TOTAL External Software Dependencies Score"),
    ("Impact of Patents", "7: TOTAL Impact of Patents Score"),
    ("Technical Protection Mechanisms", "8: TOTAL Technical Protection Mechanisms Score"),
)


def _number(value):
    if value is None or not value.strip():
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


def parse_score_ranges(weight_rows):
    if len(weight_rows) != 1:
        raise ValueError("De NARA-gewichten-CSV moet precies één gegevensrij bevatten")

    row = weight_rows[0]

    def extract_range(column):
        description = row.get(column, "")
        match = SCORE_RANGE_PATTERN.search(description)
        if not match:
            raise ValueError(f"Geen min/max-scoregrens gevonden in gewichtenkolom: {column}")
        maximum, minimum = (int(value) for value in match.groups())
        return {"minimum": minimum, "maximum": maximum}

    categories = {name: extract_range(column) for name, column in CATEGORY_COLUMNS}
    return {
        "numeric_risk_rating": extract_range(WEIGHTS_TOTAL_COLUMN),
        "categories": categories,
    }


def apply_nara_matrix(profiles, catalog_records, matrix_rows, crosswalk_rows, score_ranges, matrix_date):
    matrix_by_id = {}
    for row in matrix_rows:
        nara_id = row.get("NARA Format ID", "").strip()
        if not nara_id or nara_id in matrix_by_id:
            raise ValueError(f"Ontbrekende of dubbele NARA Format ID: {nara_id!r}")
        matrix_by_id[nara_id] = row

    crosswalk = {}
    for line_number, entry in enumerate(crosswalk_rows, start=2):
        puid = (entry.get("puid") or "").strip()
        nara_id = (entry.get("nara_format_id") or "").strip()
        basis = (entry.get("basis") or "").strip()
        evidence = (entry.get("evidence") or "").strip()
        scope = (entry.get("scope") or "").strip()
        if not puid or not nara_id or not basis or not evidence:
            raise ValueError(f"Onvolledige kruistabelrij op regel {line_number}")
        if puid not in catalog_records:
            raise ValueError(f"Onbekende PUID in kruistabel op regel {line_number}: {puid}")
        if nara_id not in matrix_by_id:
            raise ValueError(f"Onbekend NARA Format ID op regel {line_number}: {nara_id}")
        if scope not in {"individual", "shared_family"}:
            raise ValueError(f"Ongeldige scope in kruistabel op regel {line_number}: {scope}")
        if puid in crosswalk:
            raise ValueError(f"Dubbele PUID in kruistabel op regel {line_number}: {puid}")
        crosswalk[puid] = {"nara_id": nara_id, "basis": basis, "evidence": evidence, "scope": scope}

    for profile in profiles.values():
        profile.pop("durability", None)
        profile.pop("nara_risk", None)

    for puid, mapping in crosswalk.items():
        profile = profiles.setdefault(puid, {
            "page_title": None,
            "revision_timestamp": None,
            "identifiers": {"wikidata": None, "loc": None},
            "format_policy": [],
            "knowledge_levels": [],
        })
        row = matrix_by_id[mapping["nara_id"]]
        profile["nara_risk"] = {
            "nara_format_id": row["NARA Format ID"],
            "format_name": row["Format Name"],
            "file_extensions": row.get("File Extension(s)"),
            "numeric_risk_rating": _number(row.get("TOTAL Numeric Risk Rating")),
            "numeric_risk_rating_range": score_ranges["numeric_risk_rating"],
            "risk_level": row.get("Risk Level"),
            "category_totals": [
                {
                    "name": name,
                    "score": _number(row.get(column)),
                    **score_ranges["categories"][name],
                }
                for name, column in CATEGORY_COLUMNS
            ],
            "matrix_date": matrix_date,
            "source_url": MATRIX_SOURCE_URL,
            "match_basis": mapping["basis"],
            "match_evidence": mapping["evidence"],
            "match_scope": mapping["scope"],
        }

    return {"matched": len(crosswalk), "unmatched": len(catalog_records) - len(crosswalk)}


def _matrix_date(path):
    match = re.search(r"(20\d{6})", path.stem)
    if not match:
        raise ValueError(f"Geen matrixdatum gevonden in bestandsnaam: {path.name}")
    return datetime.strptime(match.group(1), "%Y%m%d").date().isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=Path, default=PROFILES_PATH)
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--matrix", type=Path, default=MATRIX_PATH)
    parser.add_argument("--crosswalk", type=Path, default=CROSSWALK_PATH)
    args = parser.parse_args()

    profile_document = json.loads(args.profiles.read_text(encoding="utf-8"))
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    with args.matrix.open(encoding="utf-8-sig", newline="") as handle:
        matrix_rows = list(csv.DictReader(handle))
    if not matrix_rows:
        raise ValueError(f"De NARA-matrix is leeg: {args.matrix}")
    with args.crosswalk.open(encoding="utf-8-sig", newline="") as handle:
        crosswalk_rows = list(csv.DictReader(handle))
    if not crosswalk_rows:
        raise ValueError(f"De NARA-kruistabel is leeg: {args.crosswalk}")
    with WEIGHTS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        score_ranges = parse_score_ranges(list(csv.DictReader(handle)))

    matrix_date = _matrix_date(args.matrix)
    counts = apply_nara_matrix(
        profile_document["records"], catalog["records"], matrix_rows, crosswalk_rows, score_ranges, matrix_date
    )
    profile_document["nara_matrix"] = {
        "matrix_date": matrix_date,
        "source_url": MATRIX_SOURCE_URL,
        "source_file": args.matrix.name,
        "crosswalk_file": args.crosswalk.name,
    }
    args.profiles.write_text(
        json.dumps(profile_document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"NARA-matrix {matrix_date}: {counts['matched']} gekoppeld, "
        f"{counts['unmatched']} PRONOM-PUID's zonder kruistabelkoppeling"
    )


if __name__ == "__main__":
    main()