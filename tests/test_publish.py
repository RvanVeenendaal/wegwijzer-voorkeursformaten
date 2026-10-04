import json
import unittest
from pathlib import Path

import yaml

from scripts import publish


ROOT = Path(__file__).resolve().parent.parent


class CatalogPublishingTests(unittest.TestCase):
    def test_enriches_records_and_keeps_unassigned_records_separate(self):
        catalog = {
            "schema_versie": 1,
            "release_tag": "V125",
            "aantal": 3,
            "records": {
                "fmt/200": {
                    "puid": "fmt/200",
                    "formatName": "Material Exchange Format",
                    "formatTypes": "Video",
                    "formatFamilies": None,
                },
                "fmt/300": {
                    "puid": "fmt/300",
                    "formatName": "WARC",
                    "formatTypes": "Aggregate",
                    "formatFamilies": None,
                },
                "fmt/88": {
                    "puid": "fmt/88",
                    "formatName": "Unmapped format",
                    "formatTypes": None,
                    "formatFamilies": None,
                },
            },
        }
        taxonomy = {
            "schema_versie": 1,
            "toepassingsgebieden": {
                "bewegend-beeld": "Bewegend beeld",
                "webarchivering": "Webarchivering",
            },
            "type_naar_toepassingsgebied": {"Video": ["bewegend-beeld"], "Aggregate": []},
            "familie_overrides": {
                "Material Exchange Format": {
                    "id": "mxf",
                    "label": "MXF",
                    "toepassingsgebieden": ["bewegend-beeld"],
                },
                "WARC": {
                    "id": "warc",
                    "label": "WARC",
                    "toepassingsgebieden": ["webarchivering"],
                },
            },
        }

        enriched = publish.verrijk_pronom_catalogus(catalog, taxonomy)

        self.assertEqual(enriched["records"]["fmt/200"]["browse_family"], {"id": "mxf", "label": "MXF"})
        self.assertEqual(enriched["records"]["fmt/200"]["browse_application_areas"], ["bewegend-beeld"])
        self.assertEqual(enriched["records"]["fmt/300"]["browse_application_areas"], ["webarchivering"])
        self.assertEqual(enriched["records"]["fmt/88"]["browse_application_areas"], [])
        self.assertEqual(enriched["browse_unassigned_count"], 1)
        self.assertEqual(enriched["browse_application_areas"], taxonomy["toepassingsgebieden"])

    def test_pinned_catalog_maps_only_to_declared_application_areas(self):
        source = json.loads((ROOT / "data" / "pronom_catalog.json").read_text(encoding="utf-8"))
        taxonomy = yaml.safe_load((ROOT / "data" / "pronom_taxonomy.yaml").read_text(encoding="utf-8"))

        enriched = publish.verrijk_pronom_catalogus(source, taxonomy)
        known_areas = set(taxonomy["toepassingsgebieden"])
        mapped_areas = {
            area
            for record in enriched["records"].values()
            for area in record["browse_application_areas"]
        }

        self.assertEqual(enriched["aantal"], 2571)
        self.assertEqual(len(known_areas), 24)
        self.assertLessEqual(mapped_areas, known_areas)
        self.assertGreater(enriched["browse_unassigned_count"], 0)
        self.assertIn("webarchivering", mapped_areas)
        self.assertEqual(enriched["format_profiles"], {})

    def test_format_profiles_are_joined_by_puid(self):
        catalog = {"records": {"fmt/1": {"formatTypes": "Video"}}}
        taxonomy = {
            "schema_versie": 1,
            "toepassingsgebieden": {"bewegend-beeld": "Bewegend beeld"},
            "type_naar_toepassingsgebied": {"Video": ["bewegend-beeld"]},
        }
        profiles = {"fmt/1": {"format_policy": [{"status": "Open", "institutions": ["Archief X"]}]}}

        enriched = publish.verrijk_pronom_catalogus(catalog, taxonomy, profiles)

        self.assertEqual(enriched["format_profiles"], profiles)

    def test_format_profile_for_unknown_puid_is_rejected(self):
        catalog = {"records": {"fmt/1": {"formatTypes": "Video"}}}
        taxonomy = {
            "schema_versie": 1,
            "toepassingsgebieden": {"bewegend-beeld": "Bewegend beeld"},
            "type_naar_toepassingsgebied": {"Video": ["bewegend-beeld"]},
        }

        with self.assertRaisesRegex(ValueError, "onbekende PUID's"):
            publish.verrijk_pronom_catalogus(catalog, taxonomy, {"fmt/2": {}})

    def test_unknown_taxonomy_area_is_rejected(self):
        catalog = {"records": {"fmt/1": {"formatTypes": "Video"}}}
        taxonomy = {
            "schema_versie": 1,
            "toepassingsgebieden": {"bewegend-beeld": "Bewegend beeld"},
            "type_naar_toepassingsgebied": {"Video": ["unknown-area"]},
        }

        with self.assertRaisesRegex(ValueError, "onbekende toepassingsgebieden"):
            publish.verrijk_pronom_catalogus(catalog, taxonomy)


if __name__ == "__main__":
    unittest.main()
