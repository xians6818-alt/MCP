import os
from datetime import datetime
from typing import Any, Dict, Optional

from supabase import Client, create_client
from models.rubric import Dimension, Rubric, RubricVersion


def read_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name)
    if value:
        return value

    try:
        import streamlit as st

        if name in st.secrets:
            secret_value = st.secrets[name]
            return str(secret_value) if secret_value is not None else default
    except Exception:
        pass

    return default


class SupabaseStorage:
    def __init__(self, state_file: str = ""):
        self.state_file = state_file
        url = read_secret("SUPABASE_URL")
        key = read_secret("SUPABASE_KEY")
        if not url or not key:
            raise ValueError(
                "Supabase credentials are missing. Set SUPABASE_URL and SUPABASE_KEY "
                "in Streamlit secrets or environment variables."
            )
        self.client: Client = create_client(url, key)

    def load_state(self) -> Dict[str, Any]:
        evaluations = self.list_evaluation_records()
        predictions = self.list_prediction_records()
        calibration_pool = self.get_calibration_pool()
        active_rubric_version = self.get_active_rubric_version()
        return {
            "schema_version": "supabase-v1",
            "rubric_version": active_rubric_version or "v2",
            "data_layer": "supabase",
            "evaluation_records": evaluations,
            "prediction_records": predictions,
            "calibration_pool": calibration_pool,
            "calibration_samples": len(calibration_pool),
        }

    def save_state(self, state: Dict[str, Any]):
        raise RuntimeError("save_state is not supported after migrating to Supabase.")

    def update_state(self, updates: Dict[str, Any]):
        return updates

    def _is_schema_missing_error(self, exc: Exception) -> bool:
        message = str(exc)
        return any(
            token in message
            for token in ["PGRST204", "PGRST205", "schema cache", "Could not find", "relation", "does not exist"]
        )

    def get_calibration_pool(self) -> list:
        response = (
            self.client.table("calibration_samples")
            .select("*")
            .order("created_at", desc=True)
            .limit(500)
            .execute()
        )
        return response.data or []

    def add_calibration_sample(self, sample: Dict[str, Any]):
        payload = {
            "title": sample.get("title", ""),
            "actual_plays": sample.get("actual_plays", 0),
            "actual_likes": int(sample.get("actual_likes", 0) or 0),
            "actual_shares": int(sample.get("actual_shares", 0) or 0),
            "timestamp": sample.get("timestamp") or datetime.now().strftime("%Y-%m-%d"),
        }
        extended_payload = {
            **payload,
            "prediction_path": sample.get("prediction_path", ""),
            "script_path": sample.get("script_path", ""),
            "script_hash": sample.get("script_hash", ""),
            "bucket": sample.get("bucket", ""),
            "center": sample.get("center"),
            "confidence": sample.get("confidence", ""),
            "composite": sample.get("composite"),
            "scores": sample.get("scores") or {},
        }
        try:
            return self.client.table("calibration_samples").insert(extended_payload).execute()
        except Exception as exc:
            if self._is_schema_missing_error(exc):
                return self.client.table("calibration_samples").insert(payload).execute()
            raise

    def get_active_rubric_version(self) -> Optional[str]:
        try:
            response = (
                self.client.table("rubric_versions")
                .select("version")
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            rows = response.data or []
            return rows[0].get("version") if rows else None
        except Exception as exc:
            if self._is_schema_missing_error(exc):
                return None
            raise

    def list_rubric_versions(self) -> list:
        try:
            response = (
                self.client.table("rubric_versions")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )
            return response.data or []
        except Exception as exc:
            if self._is_schema_missing_error(exc):
                return []
            raise

    def save_rubric_version(self, rubric: Rubric, is_active: bool = False):
        current = None
        for version in rubric.versions:
            if version.version == rubric.current_version:
                current = version
                break
        if current is None:
            raise ValueError(f"Rubric version {rubric.current_version} not found.")

        payload = {
            "version": current.version,
            "formula": current.formula,
            "weights": current.weights,
            "normalization_constant": current.normalization_constant,
            "description": current.description,
            "dimensions": [dimension.model_dump() for dimension in rubric.dimensions],
            "is_active": False,
        }
        response = self.client.table("rubric_versions").upsert(payload, on_conflict="version").execute()
        if is_active:
            self.set_active_rubric_version(current.version)
        return response

    def set_active_rubric_version(self, version: str):
        self.client.table("rubric_versions").update({"is_active": False}).neq("version", "").execute()
        return self.client.table("rubric_versions").update({"is_active": True}).eq("version", version).execute()

    def load_active_rubric(self, default_rubric: Rubric) -> Rubric:
        rows = self.list_rubric_versions()
        if not rows:
            return default_rubric

        active_row = next((row for row in rows if row.get("is_active")), None)
        if not active_row:
            return default_rubric

        dimensions_payload = active_row.get("dimensions") or [dimension.model_dump() for dimension in default_rubric.dimensions]
        dimensions = [Dimension.model_validate(item) for item in dimensions_payload]
        versions = list(default_rubric.versions)
        existing_versions = {version.version for version in versions}

        for row in reversed(rows):
            if row.get("version") in existing_versions:
                continue
            versions.append(
                RubricVersion(
                    version=row.get("version", ""),
                    formula=row.get("formula", ""),
                    weights=row.get("weights") or {},
                    normalization_constant=float(row.get("normalization_constant") or sum((row.get("weights") or {}).values()) or 1.0),
                    description=row.get("description", ""),
                )
            )

        return Rubric(versions=versions, dimensions=dimensions, current_version=active_row.get("version", default_rubric.current_version))

    def add_evaluation_record(self, record: Dict[str, Any]):
        payload = {
            "title": record.get("title", ""),
            "script_path": record.get("script_path", ""),
            "composite": record.get("composite"),
            "scores": record.get("scores") or {},
            "storyboard_count": int(record.get("storyboard_count", 0) or 0),
            "created_at": record.get("created_at") or datetime.now().isoformat(),
        }
        return self.client.table("evaluation_records").insert(payload).execute()

    def add_prediction_record(self, record: Dict[str, Any]):
        payload = {
            "title": record.get("title", ""),
            "prediction_path": record.get("prediction_path", ""),
            "bucket": record.get("bucket", ""),
            "center": record.get("center"),
            "confidence": record.get("confidence", ""),
            "composite": record.get("composite"),
            "created_at": record.get("created_at") or datetime.now().isoformat(),
        }
        return self.client.table("prediction_records").insert(payload).execute()

    def list_evaluation_records(self) -> list:
        response = (
            self.client.table("evaluation_records")
            .select("*")
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
        return response.data or []

    def list_prediction_records(self) -> list:
        response = (
            self.client.table("prediction_records")
            .select("*")
            .order("created_at", desc=True)
            .limit(200)
            .execute()
        )
        return response.data or []
