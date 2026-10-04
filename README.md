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

GitHub Actions bouwt, test en publiceert de statische site naar GitHub Pages bij
iedere push naar `main`. De Pages-bron staat ingesteld op **GitHub Actions**. De
projectpagina is beschikbaar op
`https://rvanveenendaal.github.io/wegwijzer-voorkeursformaten/`.

## Catalogus en indeling

- `data/pronom_catalog.json` bevat de volledige PRONOM-snapshot, inclusief signatures, relaties en bronverwijzingen.
- `data/pronom_taxonomy.yaml` definieert de 24 toepassingsgebieden, de koppeling van PRONOM-typen naar gebieden en enkele expliciete familie-uitzonderingen.
- `data/format_profiles.json` bevat per gevonden PUID lokaal beleid en kennisniveaus, plus NARA-risicototalen voor PUID's uit de kruistabel. De oudere Wegwijzer-duurzaamheidsscores worden niet bewaard.
- `data/institutions/<id>.json` is het ene bewerkbare bronbestand per instelling. Het bevat organisatiegegevens, formatstatussen per PUID en optioneel familiebelang. De build leest deze bestanden rechtstreeks.
- `data/institutions/template/institution.json` is het lege, kopieerbare sjabloon voor een nieuwe instelling.
- `data/nara_crosswalk.csv` is de handmatig beheerde koppeling van PRONOM-PUID naar NARA Format ID. `basis` benoemt het gebruikte naam-/alias-/signatuurbewijs, `evidence` legt de bronwaarden vast en `scope` markeert NARA-rijen die door meerdere PUID's worden gedeeld.
- `data/NARA_File_Format_Risk_Matrix_20260320_Numbered.csv` is de lokaal gedownloade NARA-bronmatrix die de risicototalen levert.
- `data/NARA_File_Format_Risk_Matrix_Weights_20241218.csv` bevat de officiële NARA-gewichten en mogelijke minimum-/maximumscore per categorie en Numeric Risk Rating.
- `scripts/nara_matrix.py` leest de grenzen uit de acht categorie-totalen en `TOTAL NARA Risk Level Numeric Score`. Prevalence, Feasibility en NARA TOTAL worden niet meegenomen.
- `scripts/harvest.py` haalt de nieuwste getagde PRONOM-release op, resolveert die naar een commit en vervangt de broncatalogus.
- `scripts/harvest_profiles.py` zoekt bronpagina's per PUID en slaat lokaal beleid, kennisniveaus en identifiers op.
- `scripts/nara_matrix.py` vervangt legacy-scores door de totalen uit de gedownloade NARA-CSV en gebruikt uitsluitend expliciete regels uit de kruistabel. Onbekende PUID's en NARA-ID's worden geweigerd.
- `scripts/publish.py` verrijkt PRONOM-records en groepeert formatstatussen per instelling in `site/pronom-catalog.json`.
- `site/index.html` biedt zoeken, filteren op PRONOM-type, navigeren via toepassingsgebied en formaatfamilie, en detailpagina's voor formaten en instellingen.
- In de instellingenweergave maakt **Nieuw profiel** een instellings-JSON via het Wegwijzer-stappenplan. Download het bestand en plaats het als `data/institutions/<id>.json`; de statische site kan bestanden niet rechtstreeks naar GitHub opslaan.

Records zonder bruikbare PRONOM-type-indeling blijven zichtbaar onder **Niet ingedeeld**. Dit is een expliciete restgroep, geen toepassingsgebied. Een toepassingsgebied is bovendien geen voorkeurs- of preserveringsadvies: de site toont de broncatalogus en herleidbare metadata. Externe broninformatie wordt niet gekopieerd naar de catalogus.

## Catalogus verversen

Instellingsgegevens worden per bestand onderhouden in `data/institutions/`; kopieer `template/institution.json` en geef het bestand en `id` dezelfde slug. Wijzig daarna alleen dat instellingsbestand. Voer `python scripts/publish.py` en `python -m unittest discover -s tests` uit. Werk `data/nara_crosswalk.csv` handmatig bij voor nieuwe of gecorrigeerde NARA-koppelingen; noteer steeds het bewijs en geef gedeelde NARA-familierijen de scope `shared_family`.

## Repositorystructuur

```text
data/
  pronom_catalog.json       # gepinde volledige PRONOM-snapshot
  pronom_taxonomy.yaml      # toepassingsgebieden en bronmapping
  format_profiles.json      # lokaal beleid en NARA-risicototalen per PUID
  institutions/            # één bewerkbaar JSON-bestand per instelling
    template/institution.json
  nara_crosswalk.csv        # handmatig beheerde PUID-naar-NARA-koppelingen
  NARA_File_Format_Risk_Matrix_20260320_Numbered.csv  # gedownloade matrixbron
  NARA_File_Format_Risk_Matrix_Weights_20241218.csv  # scoregrenzen uit NARA-gewichten
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
