import pandas as pd

from src import DatasetStorage


def test_save_and_get_use_independent_copies():
    store = DatasetStorage()
    original = pd.DataFrame({"score": [80, 90]})
    dataset_id = store.save(original, "scores.csv")
    original.loc[0, "score"] = 0
    assert store.get(dataset_id).loc[0, "score"] == 80
    retrieved = store.get(dataset_id)
    retrieved.loc[0, "score"] = -1
    assert store.get(dataset_id).loc[0, "score"] == 80


def test_update_refreshes_metadata_preserves_filename_and_copies_input():
    store = DatasetStorage()
    dataset_id = store.save(pd.DataFrame({"a": [1, 2]}), "original.csv")
    processed = pd.DataFrame({"a": [1], "b": [3]})
    assert store.update(dataset_id, processed) is True
    processed.loc[0, "b"] = 99
    assert store.get(dataset_id).loc[0, "b"] == 3
    assert store.get_metadata(dataset_id) == {
        "id": 1, "filename": "original.csv", "rows": 1,
        "columns": 2, "column_names": ["a", "b"],
    }
    metadata = store.get_metadata(dataset_id)
    metadata["column_names"].append("extra")
    assert store.get_metadata(dataset_id)["column_names"] == ["a", "b"]


def test_missing_operations_and_clear():
    store = DatasetStorage()
    df = pd.DataFrame({"a": [1]})
    assert store.get(999) is None
    assert store.get_metadata(999) is None
    assert store.update(999, df) is False
    assert store.save(df, "a.csv") == 1
    assert store.save(df, "b.csv") == 2
    store.clear()
    assert store.get(1) is None
    assert store.get_metadata(2) is None
    assert store.save(df, "c.csv") == 1
