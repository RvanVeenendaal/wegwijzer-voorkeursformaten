#!/usr/bin/env python3
"""Haal de volledige, commit-vastgepinde PRONOM-catalogus op."""

import argparse
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
import zipfile


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "data" / "pronom_catalog.json"
USER_AGENT = "WegwijzerVoorkeursformaten/2.0 (read-only PRONOM catalog harvester)"
RELEASE_API = "https://api.github.com/repos/nationalarchives/pronom/releases/latest"
REPOSITORY_API = "https://api.github.com/repos/nationalarchives/pronom"
_CATALOG = None


def get_url(url, accept="application/json"):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urlopen(request, timeout=25) as response:
        return response.read()


def get_json(url):
    return json.loads(get_url(url).decode("utf-8"))


def catalogus_uit_zip(archive_bytes, release_tag, commit_sha, release_url):
    catalogus = {}
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        for path in archive.namelist():
            parts = path.split("/")
            try:
                signatures_index = parts.index("signatures")
            except ValueError:
                continue
            if len(parts) <= signatures_index + 2:
                continue
            namespace, filename = parts[signatures_index + 1:signatures_index + 3]
            if namespace not in {"fmt", "x-fmt"} or not filename.endswith(".json"):
                continue
            record = json.loads(archive.read(path).decode("utf-8"))
            if not isinstance(record, dict):
                continue
            puid = next((
                item.get("identifierText")
                for item in record.get("identifiers", [])
                if item.get("identifierType", "").casefold() == "puid"
            ), f"{namespace}/{filename[:-5]}")
            catalogus[puid] = {
                "puid": puid,
                "record": record,
                "release_tag": release_tag,
                "source_commit": commit_sha,
                "release_url": release_url,
                "source_url": f"https://github.com/nationalarchives/pronom/blob/{commit_sha}/signatures/{namespace}/{filename}",
            }
    return catalogus


def pronom_catalogus():
    global _CATALOG
    if _CATALOG is None:
        release = get_json(RELEASE_API)
        release_tag = release["tag_name"]
        commit = get_json(f"{REPOSITORY_API}/commits/{release_tag}")
        commit_sha = commit["sha"]
        archive_bytes = get_url(
            f"{REPOSITORY_API}/zipball/{commit_sha}",
            "application/vnd.github+json",
        )
        _CATALOG = catalogus_uit_zip(
            archive_bytes,
            release_tag,
            commit_sha,
            release.get("html_url", f"https://github.com/nationalarchives/pronom/releases/tag/{release_tag}"),
        )
    return _CATALOG


def pronom_catalog_document(catalog=None):
    catalog = catalog if catalog is not None else pronom_catalogus()
    first = next(iter(catalog.values()), {})
    records = {
        puid: {
            **item["record"],
            "puid": puid,
            "source_url": item["source_url"],
        }
        for puid, item in catalog.items()
    }
    return {
        "schema_versie": 1,
        "opgehaald_op": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "release_tag": first.get("release_tag"),
        "source_commit": first.get("source_commit"),
        "release_url": first.get("release_url"),
        "aantal": len(records),
        "aantal_fmt": sum(puid.startswith("fmt/") for puid in records),
        "aantal_x_fmt": sum(puid.startswith("x-fmt/") for puid in records),
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    document = pronom_catalog_document()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"PRONOM {document['release_tag']}: {document['aantal']} records "
        f"(commit {document['source_commit']}) naar {args.output}"
    )


if __name__ == "__main__":
    main()
