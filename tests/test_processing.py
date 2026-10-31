import pytest

from main import storage
from src import ProcessConfig


@pytest.mark.parametrize("failure", ["required", "numeric", "axis", "method"])
def test_processing_error_preserves_stored_data(
    client, uploaded_dataset_id, processing_body, failure
):
    before = client.get(f"/datasets/{uploaded_dataset_id}").json()
    if failure == "required":
        processing_body["validation"]["required_columns"].append("missing")
        expected = "Required column missing: missing"
    elif failure == "numeric":
        processing_body["validation"]["numeric_columns"].append("missing")
        expected = "Numeric column missing: missing"
    elif failure == "axis":
        processing_body["processing"]["missing"]["axis"] = "invalid"
        expected = "Unsupported missing value axis: invalid"
    else:
        processing_body["processing"]["outliers"].update(
            enabled=True, columns=["score"], method="invalid"
        )
        expected = "Unsupported outlier method: invalid"

    response = client.post(
        f"/datasets/{uploaded_dataset_id}/process", json=processing_body
    )
    assert response.status_code == 400
    assert response.json() == {"detail": expected}
    assert client.get(f"/datasets/{uploaded_dataset_id}").json() == before


def test_process_missing_dataset(client, processing_body):
    response = client.post("/datasets/999/process", json=processing_body)
    assert response.status_code == 404


@pytest.mark.parametrize("body", [None, [], {"validation": {"numeric_columns": 12}}])
def test_invalid_processing_body(client, uploaded_dataset_id, body):
    before = client.get(f"/datasets/{uploaded_dataset_id}").json()
    response = client.post(f"/datasets/{uploaded_dataset_id}/process", json=body)
    assert response.status_code == 422
    assert client.get(f"/datasets/{uploaded_dataset_id}").json() == before


def test_default_processing_and_repeat_processing(client, uploaded_dataset_id):
    response = client.post(f"/datasets/{uploaded_dataset_id}/process", json={})
    assert response.status_code == 200
    assert response.json()["validation_rows_removed"] == 0
    assert response.json()["cleaning_report"]["rows_after"] == 4
    records = client.get(f"/datasets/{uploaded_dataset_id}").json()["data"]
    assert records[-2] == {"student_id": 4, "score": "unknown"}
    repeated = client.post(f"/datasets/{uploaded_dataset_id}/process", json={})
    assert repeated.json()["cleaning_report"]["rows_removed"] == 0


def test_numeric_validation_without_cleaning(
    client, uploaded_dataset_id, processing_body
):
    processing_body["processing"]["remove_duplicates"] = False
    processing_body["processing"]["missing"]["enabled"] = False
    response = client.post(
        f"/datasets/{uploaded_dataset_id}/process", json=processing_body
    )
    assert response.status_code == 200
    assert response.json()["validation_rows_removed"] == 1
    assert response.json()["cleaning_report"]["rows_removed"] == 0
    data = client.get(f"/datasets/{uploaded_dataset_id}").json()
    assert data["total_rows"] == 5
    assert data["data"][1] == data["data"][2]
    assert data["data"][3] == {"student_id": 3, "score": None}


def test_drop_missing_columns_updates_metadata(
    client, uploaded_dataset_id, processing_body
):
    processing_body["processing"]["missing"]["axis"] = "columns"
    response = client.post(
        f"/datasets/{uploaded_dataset_id}/process", json=processing_body
    )
    assert response.status_code == 200
    assert response.json()["cleaning_report"] == {
        "rows_before": 5, "rows_after": 4, "rows_removed": 1,
        "columns_before": 2, "columns_after": 1, "columns_removed": 1,
    }
    assert storage.get_metadata(uploaded_dataset_id) == {
        "id": uploaded_dataset_id, "filename": "sample_data.csv",
        "rows": 4, "columns": 1, "column_names": ["student_id"],
    }


@pytest.mark.parametrize("method,threshold", [("iqr", 1.5), ("zscore", 1.0)])
def test_enabled_outliers(client, method, threshold):
    response = client.post(
        "/upload", files={"file": ("values.csv", b"value\n10\n11\n12\n13\n100\n", "text/csv")}
    )
    dataset_id = response.json()["id"]
    response = client.post(
        f"/datasets/{dataset_id}/process",
        json={"processing": {"outliers": {
            "enabled": True, "columns": ["value"],
            "method": method, "threshold": threshold,
        }}},
    )
    assert response.status_code == 200
    assert response.json()["cleaning_report"]["rows_removed"] == 1
    assert client.get(f"/datasets/{dataset_id}").json()["data"] == [
        {"value": 10}, {"value": 11}, {"value": 12}, {"value": 13},
    ]


def test_disabled_steps_ignore_unsupported_settings(client, uploaded_dataset_id):
    response = client.post(
        f"/datasets/{uploaded_dataset_id}/process",
        json={"processing": {
            "remove_duplicates": False,
            "missing": {"enabled": False, "axis": "invalid"},
            "outliers": {"enabled": False, "method": "invalid"},
        }},
    )
    assert response.status_code == 200
    assert response.json()["cleaning_report"]["rows_after"] == 6


def test_nested_model_defaults_are_independent():
    first = ProcessConfig()
    second = ProcessConfig()
    first.validation.required_columns.append("score")
    first.processing.outliers.columns.append("score")
    first.processing.missing.axis = "columns"
    assert second.validation.required_columns == []
    assert second.processing.outliers.columns == []
    assert second.processing.missing.axis == "rows"
