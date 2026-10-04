import unittest

from scripts.harvest_profiles import parse_format_page


class FormatProfileParsingTests(unittest.TestCase):
    def test_extracts_source_ids_policy_knowledge_and_nara_details(self):
        html = """
        <h2><span>Beschrijving</span></h2>
        <table><tbody>
          <tr><th>Naam</th><td>WARC 1.0</td></tr>
          <tr><th>Wikidata ID</th><td>Q7978505</td></tr>
          <tr><th>Library of Congress ID</th><td><i>geen</i></td></tr>
        </tbody></table>
        <h2><span>Formaatbeleid</span></h2>
        <table><tbody>
          <tr><th>Formaatbeleid</th><th>Instellingen</th></tr>
          <tr><td>Voorkeursformaat</td><td><i>geen</i></td></tr>
          <tr><td>Geaccepteerd</td><td><a>Expertisegroep 3</a></td></tr>
        </tbody></table>
        <h2><span>Kennisniveaus</span></h2>
        <table><tbody>
          <tr><th>Kennisniveau</th><th>Instellingen</th></tr>
          <tr><td>Gekend</td><td><i>geen</i></td></tr>
          <tr><td>In opslag</td><td><a>Archief X</a></td></tr>
        </tbody></table>
        <h2><span>Houdbaarheid</span></h2>
        <h3><span>Openheid</span></h3>
        <table><tbody>
          <tr><th>Score:</th><td colspan="3">10</td></tr>
          <tr><th>Open specificatie</th><td>Ja</td><td>conform NARA</td><td>Is de specificatie open?</td></tr>
        </tbody></table>
        """

        profile = parse_format_page(html, "WARC 1.0", "2021-03-10T01:27:39Z")

        self.assertEqual(profile["page_title"], "WARC 1.0")
        self.assertEqual(profile["revision_timestamp"], "2021-03-10T01:27:39Z")
        self.assertEqual(profile["identifiers"], {"wikidata": "Q7978505", "loc": None})
        self.assertEqual(profile["format_policy"][0], {"status": "Voorkeursformaat", "institutions": []})
        self.assertEqual(profile["format_policy"][1]["institutions"], ["Expertisegroep 3"])
        self.assertEqual(profile["knowledge_levels"][1]["institutions"], ["Archief X"])
        self.assertEqual(profile["durability"]["score"], 10)
        self.assertEqual(profile["durability"]["factors"][0]["criteria"][0]["question"], "Is de specificatie open?")


if __name__ == "__main__":
    unittest.main()