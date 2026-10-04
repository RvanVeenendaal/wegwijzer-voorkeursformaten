# Bestandsformatencatalogus

Een catalogus om bestandsformaten te verkennen per toepassingsgebied. De site gebruikt de volledige, aan een PRONOM-release vastgepinde `fmt`- en `x-fmt`-catalogus. De PRONOM-indeling is bronmetadata; deze site kent zelf geen voorkeursstatus, duurzaamheidsscore of beleidsadvies toe.

## Starten

```powershell
pip install -r requirements.txt
python scripts/publish.py
python -m http.server --directory site 8000
```

Open daarna <http://localhost:8000>. Een webserver is nodig omdat de pagina de gegenereerde catalogus met `fetch()` laadt.

Tests uitvoeren:

```powershell
python -m unittest discover -s tests
```

GitHub Actions bouwt en test de catalogus en bewaart de statische site als
`bestandsformaten-site`-artifact. Deze private repository heeft geen GitHub Pages-
deployment; publicatie op de bestaande hosting gebeurt buiten deze workflow.

## Catalogus en indeling

- `data/pronom_catalog.json` bevat de volledige PRONOM-snapshot, inclusief signatures, relaties en bronverwijzingen.
- `data/pronom_taxonomy.yaml` definieert de 24 toepassingsgebieden, de koppeling van PRONOM-typen naar gebieden en enkele expliciete familie-uitzonderingen.
- `data/format_profiles.json` bevat per gevonden PUID lokaal beleid en kennisniveaus, plus NARA-risicototalen voor PUID's uit de kruistabel. De oudere Wegwijzer-duurzaamheidsscores worden niet bewaard.
- `data/nara_crosswalk.csv` is de handmatig beheerde koppeling van PRONOM-PUID naar NARA Format ID. `basis` benoemt het gebruikte naam-/alias-/signatuurbewijs, `evidence` legt de bronwaarden vast en `scope` markeert NARA-rijen die door meerdere PUID's worden gedeeld.
- `data/NARA_File_Format_Risk_Matrix_20260320_Numbered.csv` is de lokaal gedownloade NARA-bronmatrix die de risicototalen levert.
- `scripts/harvest.py` haalt de nieuwste getagde PRONOM-release op, resolveert die naar een commit en vervangt de broncatalogus.
- `scripts/harvest_profiles.py` zoekt bronpagina's per PUID en slaat lokaal beleid, kennisniveaus en identifiers op.
- `scripts/nara_matrix.py` vervangt legacy-scores door de totalen uit de gedownloade NARA-CSV en gebruikt uitsluitend expliciete regels uit de kruistabel. Onbekende PUID's en NARA-ID's worden geweigerd.
- `scripts/publish.py` verrijkt de bronrecords met gebieds- en familielabels en schrijft `site/pronom-catalog.json`.
- `site/index.html` biedt zoeken, filteren op PRONOM-type, navigeren via toepassingsgebied en formaatfamilie, en detailpagina's met beleid, kennisniveaus, NARA-criteria, PRONOM-gegevens en links naar externe bronnen.

Records zonder bruikbare PRONOM-type-indeling blijven zichtbaar onder **Niet ingedeeld**. Dit is een expliciete restgroep, geen toepassingsgebied. Een toepassingsgebied is bovendien geen voorkeurs- of preserveringsadvies: de site toont de broncatalogus en herleidbare metadata. Externe broninformatie wordt niet gekopieerd naar de catalogus.

## Catalogus verversen

Voer `python scripts/harvest.py` uit om de PRONOM-snapshot te verversen en `python scripts/harvest_profiles.py` om beleid en kennisniveaus opnieuw op te halen. Werk `data/nara_crosswalk.csv` handmatig bij voor nieuwe of gecorrigeerde koppelingen; noteer steeds het bewijs en geef gedeelde NARA-familierijen de scope `shared_family`. Voer daarna `python scripts/nara_matrix.py` uit; die gebruikt uitsluitend de kruistabel en verwijdert legacy-scores ook voor niet-gematchte profielen. Download voor een nieuwere matrixversie de genummerde CSV van de [officiële NARA-risicomatrix](https://github.com/usnationalarchives/digital-preservation/tree/master/Digital_Preservation_Risk_Matrix) en geef die met `python scripts/nara_matrix.py --matrix data/<bestandsnaam-met-datum>.csv` mee. Voer vervolgens `python scripts/publish.py` en de tests uit.

## Repositorystructuur

```text
data/
  pronom_catalog.json       # gepinde volledige PRONOM-snapshot
  pronom_taxonomy.yaml      # toepassingsgebieden en bronmapping
  format_profiles.json      # lokaal beleid en NARA-risicototalen per PUID
  nara_crosswalk.csv        # handmatig beheerde PUID-naar-NARA-koppelingen
  NARA_File_Format_Risk_Matrix_20260320_Numbered.csv  # gedownloade matrixbron
scripts/
  harvest.py                # PRONOM-release ophalen
  harvest_profiles.py      # lokaal beleid en kennisniveaus ophalen
  nara_matrix.py            # NARA-risicototalen importeren
  publish.py                # catalogus verrijken voor de site
tests/
  test_harvest.py
  test_harvest_profiles.py
  test_nara_matrix.py
  test_publish.py
site/
  index.html
  pronom-catalog.json      # gegenereerde catalogus voor de browser
.github/workflows/
  build.yml
  harvest.yml
```
