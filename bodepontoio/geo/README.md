# geo

Geographic reference data for Brazil: regions, states (UFs), and municipalities sourced from the IBGE API.

Data is imported once via a management command and treated as read-only reference data by the rest of the application.

---

## Models

### `Regiao`
The five macro-regions of Brazil (Norte, Nordeste, Centro-Oeste, Sudeste, Sul).

| Field | Type |
|---|---|
| `id` | int (IBGE code) |
| `nome` | string |
| `sigla` | string |

### `UF`
States and the Federal District (27 total). Each belongs to a `Regiao`.

| Field | Type |
|---|---|
| `id` | int (IBGE code) |
| `nome` | string |
| `sigla` | string |
| `regiao` | FK → `Regiao` |

### `Municipio`
All Brazilian municipalities (~5570). Each belongs to a `UF`.

| Field | Type |
|---|---|
| `id` | int (IBGE code) |
| `nome` | string |
| `uf` | FK → `UF` |

---

## API

All endpoints are **public** (no authentication required).

| Method | URL | Description |
|---|---|---|
| GET | `/api/geo/regioes/` | List all regions |
| GET | `/api/geo/regioes/{id}/` | Retrieve a region |
| GET | `/api/geo/ufs/` | List all states |
| GET | `/api/geo/ufs/?regiao={id}` | List states filtered by region |
| GET | `/api/geo/ufs/{id}/` | Retrieve a state |
| GET | `/api/geo/municipios/` | List all municipalities |
| GET | `/api/geo/municipios/?uf={id}` | List municipalities filtered by state |
| GET | `/api/geo/municipios/{id}/` | Retrieve a municipality |

Fetching `/api/geo/municipios/` without a filter returns all ~5570 records. Always filter by `?uf=` in the UI.

---

## Loading data

Run the import command from inside the backend container. It fetches live data from the IBGE Localidades API and upserts all records (safe to re-run):

```bash
python manage.py import-geo-data
```

The command is defined in `geo/management/commands/import-geo-data.py` and runs in three sequential passes: regions → states → municipalities.

