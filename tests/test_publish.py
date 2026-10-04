import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from scripts import publish


ROOT = Path(__file__).resolve().parent.parent


class CatalogPublishingTests(unittest.TestCase):
    def test_loads_one_top_level_json_document_per_institution(self):
        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            (directory / "dans.json").write_text(
                json.dumps({"schema_version": 1, "id": "dans", "name": "DANS", "formats": []}),
                encoding="utf-8",
            )
            template_directory = directory / "template"
            template_directory.mkdir()
            (template_directory / "institution.json").write_text("{}", encoding="utf-8")

            documents = publish.load_institution_documents(directory)

        self.assertEqual([document["id"] for document in documents], ["dans"])

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

    def test_builds_institution_pages_from_source_metadata_and_format_profiles(self):
        catalog_records = {"fmt/1": {"formatName": "Example Format", "version": "1.0"}}
        profiles = {
            "fmt/1": {
                "nara_risk": {"numeric_risk_rating": 24, "risk_level": "Low Risk"},
            }
        }
        institutions = [{
            "id": "archief-x",
            "name": "Archief X",
            "source_url": "https://example.org/profile",
            "formats": [{
                "puid": "fmt/1",
                "family_name": "Example Family",
                "policy_statuses": ["Voorkeursformaat"],
                "knowledge_levels": ["Gekend"],
            }],
        }]

        pages = publish.build_institution_profiles(institutions, profiles, catalog_records)

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]["id"], "archief-x")
        self.assertEqual(pages[0]["preferred_count"], 1)
        self.assertEqual(pages[0]["formats"][0]["puid"], "fmt/1")
        self.assertEqual(pages[0]["formats"][0]["family_name"], "Example Family")
        self.assertEqual(pages[0]["formats"][0]["policy_statuses"], ["Voorkeursformaat"])
        self.assertEqual(pages[0]["formats"][0]["knowledge_levels"], ["Gekend"])
        self.assertEqual(pages[0]["formats"][0]["nara_risk"]["numeric_risk_rating"], 24)

    def test_institution_profile_rejects_unknown_puid(self):
        institutions = [{"id": "archief-x", "name": "Archief X", "formats": [{"puid": "fmt/2"}]}]

        with self.assertRaisesRegex(ValueError, "(?i)onbekende PUID"):
            publish.build_institution_profiles(institutions, {}, {"fmt/1": {}})

    def test_published_catalog_keeps_per_institution_documents(self):
        catalog = {"records": {}}
        taxonomy = {
            "schema_versie": 1,
            "toepassingsgebieden": {"tekst": "Tekst"},
            "type_naar_toepassingsgebied": {},
        }
        institutions = [{
            "id": "dans",
            "name": "DANS",
            "source_url": "https://example.org/dans",
            "formats": [],
        }]

        enriched = publish.verrijk_pronom_catalogus(catalog, taxonomy, institution_documents=institutions)

        self.assertEqual(enriched["institution_profiles"][0]["source_url"], "https://example.org/dans")

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
