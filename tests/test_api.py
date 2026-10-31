from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app, storage

SAMPLE = (Path(__file__).resolve().parents[1] / "fixtures" / "sample_data.csv").read_bytes()


@pytest.fixture
def client():
    storage.clear()
    with TestClient(app) as test_client:
        yield test_client
    storage.clear()


def upload(client, filename="sample_data.csv", contents=SAMPLE):
    return client.post("/upload", files={"file": (filename, contents, "text/csv")})


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}


def test_upload_metadata_and_incrementing_ids(client):
    first = upload(client)
    assert first.status_code == 200
    assert first.json() == {
        "id": 1, "filename": "sample_data.csv", "rows": 6,
        "columns": 2, "column_names": ["student_id", "score"],
    }
    assert upload(client).json()["id"] == 2


def test_retrieval_preserves_order_duplicates_and_total(client):
    dataset_id = upload(client).json()["id"]
    response = client.get(f"/datasets/{dataset_id}?limit=2")
    assert response.status_code == 200
    assert response.json() == {
        "id": dataset_id,
        "data": [{"student_id": 1, "score": "80"}, {"student_id": 2, "score": "90"}],
        "total_rows": 6,
    }
    full = client.get(f"/datasets/{dataset_id}").json()
    assert len(full["data"]) == 6
    assert full["data"][1] == full["data"][2]
    assert full["data"][3]["score"] is None
    assert full["data"][4]["score"] == "unknown"
    assert storage.get_metadata(dataset_id)["rows"] == 6


def test_default_limit_is_100(client):
    contents = ("value\n" + "\n".join(str(i) for i in range(105))).encode()
    dataset_id = upload(client, contents=contents).json()["id"]
    data = client.get(f"/datasets/{dataset_id}").json()
    assert len(data["data"]) == 100
    assert data["total_rows"] == 105
    assert data["data"][0] == {"value": 0}


def test_limit_above_row_count(client):
    dataset_id = upload(client).json()["id"]
    assert len(client.get(f"/datasets/{dataset_id}?limit=999").json()["data"]) == 6


def test_missing_id(client):
    response = client.get("/datasets/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Dataset not found"}


@pytest.mark.parametrize("url", [
    "/datasets/abc", "/datasets/1?limit=0", "/datasets/1?limit=-1",
    "/datasets/1?limit=abc", "/datasets/1?limit=1.5",
])
def test_invalid_parameters(client, url):
    upload(client)
    assert client.get(url).status_code == 422


@pytest.mark.parametrize("filename", ["data.txt", "data.json", "data.csv.txt", "data"])
def test_reject_extension(client, filename):
    assert upload(client, filename=filename).status_code == 400
    assert upload(client).json()["id"] == 1


def test_uppercase_csv_extension(client):
    assert upload(client, filename="SAMPLE.CSV").status_code == 200


@pytest.mark.parametrize("contents", [b"", b"a,b\n1,2\n3,4,5\n", b"a,b\n1,\xff\n"])
def test_unreadable_csv_keeps_server_running(client, contents):
    response = upload(client, contents=contents)
    assert response.status_code == 400
    assert response.json() == {"detail": "Cannot read the uploaded CSV"}
    assert client.get("/health").status_code == 200
    assert upload(client).json()["id"] == 1


def test_file_is_required(client):
    assert client.post("/upload").status_code == 422


def test_header_only_csv(client):
    response = upload(client, contents=b"a,b\n")
    assert response.status_code == 200
    assert response.json()["rows"] == 0
    dataset_id = response.json()["id"]
    assert client.get(f"/datasets/{dataset_id}").json() == {
        "id": dataset_id, "data": [], "total_rows": 0,
    }


def test_response_models_in_openapi(client):
    spec = client.get("/openapi.json").json()
    for path, method, model in [
        ("/health", "get", "HealthResponse"), ("/upload", "post", "DatasetInfo"),
    ]:
        schema = spec["paths"][path][method]["responses"]["200"]["content"]["application/json"]["schema"]
        assert schema["$ref"].endswith("/" + model)


def test_application_logging(client, caplog):
    with caplog.at_level("DEBUG"):
        upload(client)
        client.get("/datasets/1?limit=2")
        client.get("/datasets/999")
        upload(client, filename="bad.txt")
    assert "Stored dataset: id=1, rows=6" in caplog.text
    assert "Uploaded dataset: id=1, filename=sample_data.csv, rows=6" in caplog.text
    assert "Retrieved dataset: id=1, returned_rows=2" in caplog.text
    assert "Dataset not found: 999" in caplog.text
    assert "Unsupported file format: .txt" in caplog.text
