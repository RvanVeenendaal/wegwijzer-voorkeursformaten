# Sjabloon instellingspagina

Kopieer `institution.json` naar `data/institutions/<id>.json`. Gebruik dezelfde slug in de bestandsnaam en in het veld `id`. De build leest ieder JSON-bestand in die map als één instellingspagina; er is geen aggregate bestand.

## Velden

- Vul publieke organisatiegegevens en `source_url` in. Laat onbekende waarden `null`.
- Voeg bij `formats` één object per PUID toe, met `family_name`, `policy_statuses` en/of `knowledge_levels`. Gebruik voor `family_name` dezelfde familienaam als een regel in `family_importance`; die koppeling is nodig voor de plot.
- Geldige beleidsstatussen: `Voorkeursformaat`, `Geaccepteerd`, `Legacy`, `Open`.
- Geldige kennisniveaus: `Gekend`, `Geidentificeerd`, `In opslag`.
- Voeg optioneel `family_importance` toe met score 0–12 en dimensies `Laag`, `Midden` of `Hoog`.

Een voorbeeld van een formatregel:

```json
{
	"puid": "fmt/199",
	"family_name": "PDF",
	"policy_statuses": ["Geaccepteerd"],
	"knowledge_levels": ["Gekend"]
}
```

Laat een formatregel weg als er geen instellingsstandpunt is; afwezigheid betekent niet dat een formaat is afgewezen. De NARA-risicoscore komt gedeeld uit de NARA-matrix en wordt niet per instelling gekopieerd. Persoonsgebonden contactgegevens en legacy-houdbaarheidsscores horen niet in dit bestand.

Valideer na bewerken met `python scripts/publish.py` en `python -m unittest discover -s tests`.