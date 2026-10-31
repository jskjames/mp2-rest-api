# MP2 REST API

This application uses FastAPI to upload CSV files, store datasets in memory, and retrieve rows as JSON. The processing endpoint reuses the MP1 pipeline to validate required and numeric columns, remove duplicates, handle missing values, and optionally remove outliers. It returns separate validation and cleaning results and updates the stored dataset after successful processing. Request middleware logs the HTTP method, path, status, duration, and request ID, which is also returned in the `X-Request-ID` response header.

## Setup

Tested with Python 3.12. Run commands from the directory containing `main.py`.

```bash
python -m venv venv
```

Windows PowerShell:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn main:app --reload
```

macOS / Linux:

```bash
source venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs to send requests. Keep the server terminal running; stop it with Ctrl+C.

## Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/health` | Return application status and version |
| POST | `/upload` | Upload a CSV file and return its metadata |
| GET | `/datasets/{dataset_id}` | Return stored records; optional `limit` defaults to 100 |
| POST | `/datasets/{dataset_id}/process` | Validate and clean the stored dataset using a JSON configuration |

Uploads use a multipart field named `file`. Successful requests return 200. Unsupported uploads and processing settings return 400, missing datasets return 404, and invalid request data returns 422. Unexpected server errors return a generic 500 response; the traceback is logged on the server.

## Upload, process, and retrieve

1. Upload `fixtures/sample_data.csv` through `/docs`. It contains six rows and two columns.
2. Use the returned ID with the processing endpoint and the following request body. The same JSON is saved in `fixtures/process_config.json`.

```json
{
  "validation": {
    "required_columns": ["student_id", "score"],
    "numeric_columns": ["score"]
  },
  "processing": {
    "remove_duplicates": true,
    "missing": {
      "enabled": true,
      "axis": "rows"
    },
    "outliers": {
      "enabled": false,
      "columns": [],
      "method": "iqr",
      "threshold": 1.5
    }
  }
}
```

Expected processing response for dataset ID 1:

```json
{
  "id": 1,
  "validation_rows_removed": 1,
  "cleaning_report": {
    "rows_before": 5,
    "rows_after": 3,
    "rows_removed": 2,
    "columns_before": 2,
    "columns_after": 2,
    "columns_removed": 0
  }
}
```

3. Retrieve that dataset. It now contains student IDs 1, 2, and 5, with numeric scores 80, 90, and 85.

Validation removes the row containing `unknown`. Cleaning removes the duplicate and the row with a missing score. The cleaning report compares the validated data with the processed data, so it starts at five rows. Upload a fresh sample before repeating a demonstration that depends on the original six rows.

The processing body is required, but `{}` uses default settings: no configured column validation, duplicate removal enabled, missing rows dropped, and outliers disabled. Missing-value axes are `rows` or `columns`; outlier methods are `iqr` or `zscore`. Unsupported values in enabled steps follow the MP1 error behavior.

## Storage and logging

The `data_pipeline` package contains the reusable MP1 modules. The `src` package contains API models, storage, logging setup, and middleware. Stored DataFrames are copied on save, retrieval, and update. Failed validation or processing leaves stored data unchanged. Metadata uses the current stored DataFrame.

Storage is temporary and belongs to one server process. Restarting or reloading clears the data and resets IDs. Request logs use INFO for successful responses, WARNING for 4xx responses, and ERROR for 5xx responses. Each request receives an eight-character request ID.

## Tests

Windows PowerShell:

```powershell
.\venv\Scripts\python.exe -m pytest tests -v
```

With an activated environment:

```bash
python -m pytest tests -v
```

Tests cover the upload-process-retrieve flow, metadata, validation failures, storage preservation, request IDs, log levels, unexpected errors, and storage copies. Fixtures reset storage before and after each API test.
