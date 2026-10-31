import logging

logger = logging.getLogger(__name__)


class DatasetStorage:
    def __init__(self):
        self._store = {}
        self._counter = 0

    def save(self, df, filename):
        """Store a copy of the data and return a new integer ID."""
        self._counter += 1
        dataset_id = self._counter
        self._store[dataset_id] = {"filename": filename, "data": df.copy()}
        logger.debug("Stored dataset: id=%s, rows=%s", dataset_id, len(df))
        return dataset_id

    def get(self, dataset_id):
        """Return a copy of the stored DataFrame, or None."""
        item = self._store.get(dataset_id)
        if item is None:
            logger.debug("Dataset not found: id=%s", dataset_id)
            return None
        df = item["data"].copy()
        logger.debug("Retrieved dataset copy: id=%s, rows=%s", dataset_id, len(df))
        return df

    def get_metadata(self, dataset_id):
        """Return metadata calculated from the current stored DataFrame."""
        item = self._store.get(dataset_id)
        if item is None:
            logger.debug("Metadata not found: id=%s", dataset_id)
            return None
        df = item["data"]
        metadata = {
            "id": dataset_id,
            "filename": item["filename"],
            "rows": df.shape[0],
            "columns": df.shape[1],
            "column_names": df.columns.tolist(),
        }
        logger.debug("Retrieved metadata: id=%s", dataset_id)
        return metadata

    def update(self, dataset_id, df):
        """Replace an existing dataset; return True, or False if missing."""
        if dataset_id not in self._store:
            logger.debug("Cannot update missing dataset: id=%s", dataset_id)
            return False
        self._store[dataset_id]["data"] = df.copy()
        logger.debug("Updated dataset: id=%s, rows=%s", dataset_id, len(df))
        return True

    def clear(self):
        """Clear all data and reset the ID counter."""
        self._store.clear()
        self._counter = 0
        logger.debug("Cleared datasets and reset ID counter")
