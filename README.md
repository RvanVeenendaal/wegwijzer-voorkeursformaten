# Wegwijzer Voorkeursformaten

Een catalogus om bestandsformaten te verkennen per toepassingsgebied van de Wegwijzer. De site gebruikt de volledige, aan een PRONOM-release vastgepinde `fmt`- en `x-fmt`-catalogus. De PRONOM-indeling is bronmetadata; deze site kent zelf geen voorkeursstatus, duurzaamheidsscore of beleidsadvies toe.

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
`wegwijzer-site`-artifact. Deze private repository heeft geen GitHub Pages-
deployment; publicatie op de bestaande hosting gebeurt buiten deze workflow.

## Catalogus en indeling

- `data/pronom_catalog.json` bevat de volledige PRONOM-snapshot, inclusief signatures, relaties en bronverwijzingen.
- `data/pronom_taxonomy.yaml` definieert de 24 toepassingsgebieden, de koppeling van PRONOM-typen naar gebieden en enkele expliciete familie-uitzonderingen.
- `data/wegwijzer_profielen.json` bevat optionele Wegwijzer-verrijkingen per PUID: instellingbeleid, kennisniveaus, NARA-houdbaarheid en Wikidata/COPTR-bronnen. De PNG-pagina (`fmt/11`) is de eerste ingevulde profielpagina.
- `scripts/harvest.py` haalt de nieuwste getagde PRONOM-release op, resolveert die naar een commit en vervangt de broncatalogus.
- `scripts/publish.py` verrijkt de bronrecords met gebieds- en familielabels en schrijft `site/pronom-catalog.json`.
- `site/index.html` biedt zoeken, filteren op PRONOM-type, navigeren via toepassingsgebied en formaatfamilie, plus detailsecties voor beschrijving, beleid, kennisniveaus, houdbaarheid en PRONOM/Wikidata/COPTR-data.

Records zonder bruikbare PRONOM-type-indeling blijven zichtbaar onder **Niet ingedeeld**. Dit is een expliciete restgroep, geen Wegwijzer-toepassingsgebied. Een Wegwijzer-gebied is bovendien geen voorkeurs- of preserveringsadvies: de site toont de broncatalogus en herleidbare metadata.
Wegwijzer-profielen zijn optioneel; wanneer er geen lokale verrijking is, toont de detailpagina dat expliciet in plaats van beleid of scores af te leiden uit PRONOM-metadata.

## Catalogus verversen

Voer `python scripts/harvest.py` uit. De harvester downloadt de nieuwste PRONOM-release en slaat zowel de releasetag als commit-SHA op. Controleer de gewijzigde brondata en voer daarna `python scripts/publish.py` en de tests uit. De geplande GitHub Actions-workflow doet hetzelfde en opent een pull request met alleen de vernieuwde broncatalogus.

## Repositorystructuur

```text
data/
  pronom_catalog.json       # gepinde volledige PRONOM-snapshot
  pronom_taxonomy.yaml      # Wegwijzergebieden en bronmapping
  wegwijzer_profielen.json  # optionele, PUID-gekoppelde detaildata
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
