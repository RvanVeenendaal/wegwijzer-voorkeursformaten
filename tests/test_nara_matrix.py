import unittest

from scripts.nara_matrix import apply_nara_matrix


class NaraMatrixTests(unittest.TestCase):
    def test_applies_explicit_crosswalk_and_replaces_legacy_scores(self):
        profiles = {
            "fmt/1": {"page_title": "WARC 1.0", "durability": {"score": 27}},
            "fmt/2": {"page_title": "WARC", "durability": {"score": 99}},
        }
        matrix_rows = [{
            "NARA Format ID": "NF00439",
            "Format Name": "Web ARChive (WARC) 1.0",
            "File Extension(s)": "warc",
            "TOTAL Numeric Risk Rating": "24.00",
            "Risk Level": "Low Risk",
            "1: TOTAL Disclosure Score": "6",
            "2: TOTAL Adoption Score": "3",
            "3: TOTAL Transparency Score": "0",
            "4: TOTAL Self-Documentation Score": "1",
            "5: TOTAL External Hardware Dependencies Score": "4",
            "6: TOTAL External Software Dependencies Score": "2",
            "7: TOTAL Impact of Patents Score": "4",
            "8: TOTAL Technical Protection Mechanisms Score": "4",
            "NARA TOTAL": "24.00",
        }]

        catalog = {"fmt/1": {}, "fmt/2": {}}
        crosswalk = [{
            "puid": "fmt/1",
            "nara_format_id": "NF00439",
            "basis": "profielnaam_via_nara_afkorting",
            "evidence": "WARC 1.0 -> Web ARChive (WARC) 1.0",
            "scope": "individual",
        }]

        counts = apply_nara_matrix(profiles, catalog, matrix_rows, crosswalk, "2026-03-20")

        self.assertEqual(counts, {"matched": 1, "unmatched": 1})
        self.assertNotIn("durability", profiles["fmt/1"])
        self.assertEqual(profiles["fmt/1"]["nara_risk"]["nara_format_id"], "NF00439")
        self.assertEqual(profiles["fmt/1"]["nara_risk"]["numeric_risk_rating"], 24)
        self.assertNotIn("nara_total", profiles["fmt/1"]["nara_risk"])
        self.assertEqual(profiles["fmt/1"]["nara_risk"]["match_basis"], "profielnaam_via_nara_afkorting")
        self.assertEqual(profiles["fmt/1"]["nara_risk"]["category_totals"][0], {"name": "Disclosure", "score": 6})
        self.assertNotIn("nara_risk", profiles["fmt/2"])
        self.assertNotIn("durability", profiles["fmt/2"])

    def test_creates_nara_only_profile_for_unprofiled_puid(self):
        profiles = {}
        catalog = {"fmt/1": {}}
        matrix_rows = [{"NARA Format ID": "NF1", "Format Name": "Format"}]
        crosswalk = [{
            "puid": "fmt/1",
            "nara_format_id": "NF1",
            "basis": "pronom_naam_exact",
            "evidence": "Format -> Format",
            "scope": "individual",
        }]

        apply_nara_matrix(profiles, catalog, matrix_rows, crosswalk, "2026-03-20")

        self.assertEqual(profiles["fmt/1"]["format_policy"], [])
        self.assertEqual(profiles["fmt/1"]["nara_risk"]["nara_format_id"], "NF1")

    def test_rejects_unknown_ids_and_duplicate_puids(self):
        catalog = {"fmt/1": {}}
        matrix_rows = [{"NARA Format ID": "NF1", "Format Name": "Format"}]
        valid = {
            "puid": "fmt/1",
            "nara_format_id": "NF1",
            "basis": "pronom_naam_exact",
            "evidence": "Format -> Format",
            "scope": "individual",
        }

        with self.assertRaisesRegex(ValueError, "Onbekende PUID"):
            apply_nara_matrix({}, catalog, matrix_rows, [{**valid, "puid": "fmt/2"}], "2026-03-20")
        with self.assertRaisesRegex(ValueError, "Dubbele PUID"):
            apply_nara_matrix({}, catalog, matrix_rows, [valid, valid], "2026-03-20")


if __name__ == "__main__":
    unittest.main()