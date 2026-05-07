"""GCS artifact store — upload and download model artifacts and processed data.

Used by:
  - scripts/retrain.py  : uploads new artifacts after a successful retrain
  - streamlit_app/      : downloads artifacts on startup if GCS is newer

Requires env vars:
  GCS_BUCKET   : name of the GCS bucket (e.g. olist-artifacts-curious490213)
  GCP_PROJECT  : GCP project ID (optional, inferred from credentials if absent)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MODELS_DIR = _PROJECT_ROOT / "models"
_PROCESSED_DIR = _PROJECT_ROOT / "data" / "processed"

# Files managed by the artifact store
_ARTIFACT_FILES: list[tuple[Path, str]] = [
    (_MODELS_DIR / "standard_scaler.pkl", "models/standard_scaler.pkl"),
    (_PROCESSED_DIR / "cluster_profile.parquet", "data/cluster_profile.parquet"),
    (_PROCESSED_DIR / "customer_features_labeled.parquet", "data/customer_features_labeled.parquet"),
    (_PROCESSED_DIR / "model_comparison.csv", "data/model_comparison.csv"),
    (_PROCESSED_DIR / "retrain_log.json", "data/retrain_log.json"),
]

# Model pkl + json are discovered dynamically (filename depends on best k)
_MODEL_GCS_PREFIX = "models/"


def _get_client():
    """Return an authenticated GCS client."""
    try:
        from google.cloud import storage
        return storage.Client(project=os.getenv("GCP_PROJECT"))
    except ImportError as exc:
        raise ImportError(
            "google-cloud-storage not installed. Run: pip install google-cloud-storage"
        ) from exc


def _bucket_name() -> str:
    name = os.getenv("GCS_BUCKET")
    if not name:
        raise EnvironmentError("GCS_BUCKET env var is not set.")
    return name


def upload_artifacts(best_k: int) -> None:
    """Upload all model artifacts to GCS after a successful retrain.

    Args:
        best_k: The k value of the best model (used to locate .pkl and .json files).
    """
    client = _get_client()
    bucket = client.bucket(_bucket_name())

    files_to_upload = list(_ARTIFACT_FILES)
    files_to_upload += [
        (_MODELS_DIR / f"best_clustering_kmeans_k{best_k}.pkl",
         f"models/best_clustering_kmeans_k{best_k}.pkl"),
        (_MODELS_DIR / f"best_clustering_kmeans_k{best_k}.json",
         f"models/best_clustering_kmeans_k{best_k}.json"),
    ]

    for local_path, gcs_path in files_to_upload:
        if not local_path.exists():
            logger.warning("Skipping %s — file not found locally", local_path.name)
            continue
        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(str(local_path))
        logger.info("Uploaded %s → gs://%s/%s", local_path.name, _bucket_name(), gcs_path)

    logger.info("All artifacts uploaded to gs://%s", _bucket_name())


def download_artifacts() -> bool:
    """Download artifacts from GCS to local disk if they are newer than local copies.

    Returns:
        True if any file was downloaded, False if everything was already up to date.
    """
    try:
        client = _get_client()
        bucket = client.bucket(_bucket_name())
    except Exception as exc:
        logger.warning("GCS not available (%s) — using local artifacts", exc)
        return False

    _MODELS_DIR.mkdir(parents=True, exist_ok=True)
    _PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Discover model files dynamically from GCS
    all_blobs = list(bucket.list_blobs(prefix=_MODEL_GCS_PREFIX))
    model_blobs = [
        (b, _MODELS_DIR / Path(b.name).name)
        for b in all_blobs
        if b.name.endswith((".pkl", ".json"))
    ]

    static_blobs = []
    for local_path, gcs_path in _ARTIFACT_FILES:
        blob = bucket.blob(gcs_path)
        if blob.exists():
            static_blobs.append((blob, local_path))

    updated = False
    for blob, local_path in model_blobs + static_blobs:
        blob.reload()
        gcs_updated = blob.updated

        if local_path.exists() and gcs_updated:
            import datetime
            local_mtime = datetime.datetime.fromtimestamp(
                local_path.stat().st_mtime, tz=datetime.timezone.utc
            )
            if local_mtime >= gcs_updated:
                logger.debug("%s already up to date", local_path.name)
                continue

        blob.download_to_filename(str(local_path))
        logger.info("Downloaded gs://%s/%s → %s", _bucket_name(), blob.name, local_path.name)
        updated = True

    return updated


def get_gcs_metadata() -> dict | None:
    """Fetch the latest model metadata JSON from GCS without downloading everything.

    Returns:
        Parsed metadata dict, or None if not found.
    """
    try:
        client = _get_client()
        bucket = client.bucket(_bucket_name())
        blobs = [
            b for b in bucket.list_blobs(prefix=_MODEL_GCS_PREFIX)
            if b.name.endswith(".json")
        ]
        if not blobs:
            return None
        latest = max(blobs, key=lambda b: b.updated or 0)
        return json.loads(latest.download_as_text())
    except Exception as exc:
        logger.warning("Could not fetch GCS metadata: %s", exc)
        return None
