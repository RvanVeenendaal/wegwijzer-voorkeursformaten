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
- `scripts/harvest.py` haalt de nieuwste getagde PRONOM-release op, resolveert die naar een commit en vervangt de broncatalogus.
- `scripts/publish.py` verrijkt de bronrecords met gebieds- en familielabels en schrijft `site/pronom-catalog.json`.
- `site/index.html` biedt zoeken, filteren op PRONOM-type, navigeren via toepassingsgebied en formaatfamilie, en detailpagina's met PRONOM-gegevens en directe links voor beschikbare Wikidata- en Library of Congress-identifiers.

Records zonder bruikbare PRONOM-type-indeling blijven zichtbaar onder **Niet ingedeeld**. Dit is een expliciete restgroep, geen toepassingsgebied. Een toepassingsgebied is bovendien geen voorkeurs- of preserveringsadvies: de site toont de broncatalogus en herleidbare metadata. Externe broninformatie wordt niet gekopieerd naar de catalogus.

## Catalogus verversen

Voer `python scripts/harvest.py` uit. De harvester downloadt de nieuwste PRONOM-release en slaat zowel de releasetag als commit-SHA op. Controleer de gewijzigde brondata en voer daarna `python scripts/publish.py` en de tests uit. De geplande GitHub Actions-workflow doet hetzelfde en opent een pull request met alleen de vernieuwde broncatalogus.

## Repositorystructuur

```text
data/
  pronom_catalog.json       # gepinde volledige PRONOM-snapshot
  pronom_taxonomy.yaml      # toepassingsgebieden en bronmapping
scripts/
  harvest.py                # PRONOM-release ophalen
  publish.py                # catalogus verrijken voor de site
tests/
  test_harvest.py
  test_publish.py
site/
  index.html
  pronom-catalog.json      # gegenereerde catalogus voor de browser
.github/workflows/
  build.yml
  harvest.yml
```
