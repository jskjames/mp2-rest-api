# MP2 REST API

A FastAPI application for uploading CSV files and retrieving datasets stored in memory.

## Setup

Python 3.12.

```bash
python -m venv venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source venv/bin/activate
```

Install dependencies and start the server:

```bash
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Interactive API documentation: http://127.0.0.1:8000/docs

## Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/health` | Return the application status and version |
| POST | `/upload` | Upload a CSV file and return its metadata |
| GET | `/datasets/{dataset_id}` | Retrieve rows from a stored dataset |

The upload uses a multipart form field named `file`. Dataset retrieval accepts an optional `limit` query parameter, with a default of 100 and a minimum of 1.

Successful requests return 200. Unsupported files or unreadable CSVs return 400, missing datasets return 404, and invalid parameters return 422.

## Example

Upload `fixtures/sample_data.csv` through `/docs`. The response contains an ID, filename, row count, column count, and column names.

```json
{
  "id": 1,
  "filename": "sample_data.csv",
  "rows": 6,
  "columns": 2,
  "column_names": ["student_id", "score"]
}
```

Request `/datasets/1?limit=2` using the ID returned by the upload:

```json
{
  "id": 1,
  "data": [
    {"student_id": 1, "score": "80"},
    {"student_id": 2, "score": "90"}
  ],
  "total_rows": 6
}
```

The limit changes the number of returned rows without changing the stored dataset. Missing values are returned as JSON null. Duplicates and other values are preserved.

## Storage

Datasets are stored in memory and reset when the server restarts or reloads. IDs start at 1. Saving, retrieving, and updating use DataFrame copies. Metadata is calculated from the current stored DataFrame.

## Logging

Storage operations use DEBUG, successful uploads and retrievals use INFO, and rejected uploads or missing datasets use WARNING. The logging setup is reused from MP1.

## Tests

```bash
python -m pytest -q
```

Tests cover uploads, retrieval, response models, invalid requests, missing values, row limits, storage copies, updates, and ID resets.
