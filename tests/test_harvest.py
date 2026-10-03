import io
import json
import unittest
from unittest.mock import patch
import zipfile

from scripts import harvest


class PronomHarvestTests(unittest.TestCase):
    def pronom_zip(self):
        records = {
            "signatures/fmt/7.json": {
                "formatName": "Tagged Image File Format",
                "formatTypes": "Image (Raster)",
                "identifiers": [{"identifierText": "fmt/7", "identifierType": "PUID"}],
                "relationships": [{"relationshipType": "Has successor", "relatedFormatID": 353}],
                "internalSignatures": [],
                "externalSignatures": [{"externalSignature": "tif", "signatureType": "File extension"}],
                "containerSignatures": [],
            },
            "signatures/x-fmt/7.json": {
                "formatName": "Legacy format",
                "identifiers": [{"identifierText": "x-fmt/7", "identifierType": "PUID"}],
            },
        }
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, record in records.items():
                archive.writestr(f"nationalarchives-pronom-deadbeef/{name}", json.dumps(record))
        return buffer.getvalue()

    def test_release_zip_indexes_both_puid_namespaces(self):
        catalog = harvest.catalogus_uit_zip(
            self.pronom_zip(), "V125", "deadbeef",
            "https://github.com/nationalarchives/pronom/releases/tag/V125",
        )

        self.assertEqual(set(catalog), {"fmt/7", "x-fmt/7"})
        self.assertEqual(catalog["fmt/7"]["record"]["formatTypes"], "Image (Raster)")
        self.assertEqual(catalog["fmt/7"]["source_commit"], "deadbeef")

    def test_catalog_document_preserves_signatures_and_release_metadata(self):
        catalog = harvest.catalogus_uit_zip(
            self.pronom_zip(), "V125", "deadbeef",
            "https://github.com/nationalarchives/pronom/releases/tag/V125",
        )

        document = harvest.pronom_catalog_document(catalog)

        self.assertEqual(document["aantal"], 2)
        self.assertEqual(document["aantal_fmt"], 1)
        self.assertEqual(document["aantal_x_fmt"], 1)
        self.assertEqual(document["records"]["fmt/7"]["relationships"][0]["relatedFormatID"], 353)
        self.assertEqual(document["records"]["fmt/7"]["externalSignatures"][0]["externalSignature"], "tif")

    def test_latest_release_is_pinned_to_a_commit(self):
        release = {"tag_name": "V125", "html_url": "https://github.com/nationalarchives/pronom/releases/tag/V125"}
        commit = {"sha": "deadbeef"}
        original_catalog = harvest._CATALOG
        try:
            harvest._CATALOG = None
            with (
                patch.object(harvest, "get_json", side_effect=[release, commit]),
                patch.object(harvest, "get_url", return_value=self.pronom_zip()) as download,
            ):
                catalog = harvest.pronom_catalogus()
            self.assertIn("/zipball/deadbeef", download.call_args.args[0])
            self.assertEqual(catalog["fmt/7"]["source_commit"], "deadbeef")
        finally:
            harvest._CATALOG = original_catalog


if __name__ == "__main__":
    unittest.main()
