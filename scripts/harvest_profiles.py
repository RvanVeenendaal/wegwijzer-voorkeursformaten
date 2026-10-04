#!/usr/bin/env python3
"""Harvest locally maintained format data from the legacy MediaWiki register."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = ROOT / "data" / "pronom_catalog.json"
OUTPUT_PATH = ROOT / "data" / "format_profiles.json"
API_URL = "https://www.wegwijzervoorkeursformaten.nl/api.php"
USER_AGENT = "BestandsformatenCatalogus/1.0 (read-only profile importer)"
PUID_PATTERN = re.compile(r"\bPUID\s*=\s*((?:x-)?fmt/\d+)", re.IGNORECASE)
IDENTIFIER_FIELDS = {
    "wikidata id": "wikidata",
    "library of congress id": "loc",
}


def _plain_text(parts):
    return " ".join("".join(parts).split())


class _FormatPageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.section = ""
        self.factor = None
        self.heading_tag = None
        self.heading_parts = []
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None
        self.anchor_parts = None

    def handle_starttag(self, tag, attrs):
        if tag in {"h2", "h3"}:
            self.heading_tag = tag
            self.heading_parts = []
        elif tag == "table" and self.table is None:
            self.table = {"section": self.section, "factor": self.factor, "rows": []}
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in {"th", "td"} and self.row is not None:
            self.cell = {"text": [], "links": []}
        elif tag == "a" and self.cell is not None:
            self.anchor_parts = []

    def handle_data(self, data):
        if self.heading_tag:
            self.heading_parts.append(data)
        if self.cell is not None:
            self.cell["text"].append(data)
        if self.anchor_parts is not None:
            self.anchor_parts.append(data)

    def handle_endtag(self, tag):
        if tag == self.heading_tag:
            heading = _plain_text(self.heading_parts)
            if tag == "h2":
                self.section = heading
                self.factor = None
            else:
                self.factor = heading
            self.heading_tag = None
        elif tag == "a" and self.anchor_parts is not None:
            anchor = _plain_text(self.anchor_parts)
            if anchor and self.cell is not None:
                self.cell["links"].append(anchor)
            self.anchor_parts = None
        elif tag in {"th", "td"} and self.cell is not None:
            self.cell["text"] = _plain_text(self.cell["text"])
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                self.table["rows"].append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def _tables_by_section(html):
    parser = _FormatPageParser()
    parser.feed(html)
    parser.close()
    return parser.tables


def _cell_text(row, index):
    return row[index]["text"] if index < len(row) else ""


def _institutions(cell):
    if not cell:
        return []
    text = cell["text"].strip()
    if not text or text.casefold() in {"geen", "n.v.t.", "nvt", "-"}:
        return []
    names = cell["links"] or [item.strip() for item in re.split(r"\s*[,;]\s*", text)]
    return list(dict.fromkeys(name for name in names if name and name.casefold() != "geen"))


def _table_key_value_rows(table, field_name):
    values = []
    for row in table["rows"]:
        label = _cell_text(row, 0)
        value = _cell_text(row, 1)
        if label.casefold() in {field_name.casefold(), field_name.casefold() + "en"}:
            continue
        if label and len(row) > 1:
            values.append((label, row[1]))
    return values


def parse_format_page(html, title, revision_timestamp):
    tables = _tables_by_section(html)
    identifiers = {"wikidata": None, "loc": None}
    source_classification = {"format_family": None, "application_area": None}
    for table in tables:
        if table["section"] != "Beschrijving":
            continue
        for label, cell in _table_key_value_rows(table, "Naam"):
            field = label.casefold()
            value = cell["text"]
            if field == "formaatfamilie":
                source_classification["format_family"] = value or None
            elif field == "toepassingsgebied":
                source_classification["application_area"] = value or None
            key = IDENTIFIER_FIELDS.get(label.casefold())
            if key and value.casefold() not in {"", "geen", "n.v.t.", "nvt", "-"}:
                identifiers[key] = value

    policy = []
    knowledge = []
    for table in tables:
        if table["section"] == "Formaatbeleid":
            for label, cell in _table_key_value_rows(table, "Formaatbeleid"):
                policy.append({"status": label, "institutions": _institutions(cell)})
        elif table["section"] == "Kennisniveaus":
            for label, cell in _table_key_value_rows(table, "Kennisniveau"):
                knowledge.append({"level": label, "institutions": _institutions(cell)})

    factors = []
    for table in tables:
        if table["section"] != "Houdbaarheid" or not table["factor"]:
            continue
        score = None
        criteria = []
        for row in table["rows"]:
            label = _cell_text(row, 0)
            value = _cell_text(row, 1)
            if label.casefold() == "score:":
                match = re.search(r"-?\d+", value)
                score = int(match.group()) if match else None
            elif label:
                criteria.append({
                    "name": label,
                    "value": value or None,
                    "note": _cell_text(row, 2) or None,
                    "question": _cell_text(row, 3) or None,
                })
        factors.append({"name": table["factor"], "score": score, "criteria": criteria})

    scores = [factor["score"] for factor in factors if factor["score"] is not None]
    durability = None
    if factors:
        durability = {"method": "NARA", "score": sum(scores), "factors": factors}

    return {
        "page_title": title,
        "revision_timestamp": revision_timestamp,
        "identifiers": identifiers,
        "source_classification": source_classification,
        "format_policy": policy,
        "knowledge_levels": knowledge,
        "durability": durability,
    }


def _api_json(params, timeout=45):
    url = API_URL + "?" + urlencode(params)
    request = Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(4):
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError, ConnectionError):
            if attempt == 3:
                raise
            time.sleep(min(2**attempt, 15))


def _all_pages():
    pages = []
    continuation = None
    while True:
        params = {"action": "query", "list": "allpages", "aplimit": "max", "format": "json"}
        if continuation:
            params["apcontinue"] = continuation
        response = _api_json(params)
        pages.extend(response.get("query", {}).get("allpages", []))
        continuation = response.get("continue", {}).get("apcontinue")
        if not continuation:
            return pages


def _source_pages_for_puids(puids):
    pages = _all_pages()
    found = {}
    for offset in range(0, len(pages), 50):
        batch = pages[offset : offset + 50]
        response = _api_json({
            "action": "query",
            "prop": "revisions",
            "rvprop": "content|timestamp",
            "rvslots": "main",
            "titles": "|".join(page["title"] for page in batch),
            "format": "json",
        })
        for page in response.get("query", {}).get("pages", {}).values():
            revisions = page.get("revisions", [])
            if not revisions:
                continue
            content = revisions[0].get("slots", {}).get("main", {}).get("*", "")
            for puid in set(PUID_PATTERN.findall(content)) & puids:
                if puid in found:
                    raise ValueError(f"Meerdere bronpagina's gevonden voor {puid}")
                found[puid] = {
                    "pageid": page["pageid"],
                    "title": page["title"],
                    "timestamp": revisions[0].get("timestamp"),
                }
    return found


def harvest_profiles(puids, workers=2, progress=None):
    source_pages = _source_pages_for_puids(set(puids))
    profiles = {}

    def harvest_one(puid, source_page):
        response = _api_json({
            "action": "parse",
            "pageid": source_page["pageid"],
            "prop": "text",
            "format": "json",
        })
        parsed = response["parse"]
        html = parsed.get("text", {}).get("*") or ""
        return puid, parse_format_page(html, source_page["title"], source_page["timestamp"])

    total = len(source_pages)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(harvest_one, puid, page): puid
            for puid, page in source_pages.items()
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            puid, profile = future.result()
            profiles[puid] = profile
            if progress and (completed % 100 == 0 or completed == total):
                progress(completed, total)

    return {
        "schema_version": 1,
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "records": dict(sorted(profiles.items())),
        "unmatched_puids": sorted(set(puids) - set(source_pages)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()

    catalog = json.loads(args.source.read_text(encoding="utf-8"))
    document = harvest_profiles(
        set(catalog.get("records", {})),
        workers=max(1, args.workers),
        progress=lambda completed, total: print(f"Opgeladen: {completed}/{total} profielpagina's"),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Gegenereerd: {len(document['records'])} profielen, "
        f"{len(document['unmatched_puids'])} PUID's zonder pagina"
    )


if __name__ == "__main__":
    main()