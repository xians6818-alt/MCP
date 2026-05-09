import os
from datetime import datetime
from typing import Any, Dict, Optional

from supabase import Client, create_client


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
        return {
            "schema_version": "supabase-v1",
            "rubric_version": "v2",
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
        return self.client.table("calibration_samples").insert(payload).execute()

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
