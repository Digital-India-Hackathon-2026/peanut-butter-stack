from __future__ import annotations

import logging
from typing import Any

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from services.config import MONGODB_URL

logger = logging.getLogger("vitalguard.services.database")

DEFAULT_COLLECTIONS = ["patients", "patient_vitals", "patients_registry", "patient_info"]


class PatientRepository:
    def __init__(self) -> None:
        self._client = None
        self._db = None
        if MONGODB_URL:
            try:
                client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=3000)
                self._client = client
                self._db = client.get_default_database() or client["vitalguard"]
                logger.info("[PatientRepository] Connected to MongoDB database '%s'.", self._db.name)
            except PyMongoError as exc:
                logger.warning(
                    "[PatientRepository] Unable to connect to MongoDB '%s': %s",
                    MONGODB_URL,
                    exc,
                )
                self._client = None
                self._db = None

    def find_patient(self, patient_id: str | None = None, bed: str | None = None) -> dict[str, Any]:
        if self._db is None:
            return {}

        query: dict[str, str] = {}
        if patient_id:
            query["patient_id"] = patient_id
        if bed and "patient_id" not in query:
            query["bed"] = bed
        if not query:
            return {}

        for collection_name in DEFAULT_COLLECTIONS:
            if collection_name not in self._db.list_collection_names():
                continue
            try:
                document = self._db[collection_name].find_one(query)
                if document:
                    return {k: v for k, v in document.items() if isinstance(k, str)}
            except PyMongoError as exc:
                logger.warning(
                    "[PatientRepository] Query failed on collection '%s': %s",
                    collection_name,
                    exc,
                )
        return {}
