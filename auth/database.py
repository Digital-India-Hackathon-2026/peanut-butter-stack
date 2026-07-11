"""Shared MongoDB connection for the auth module."""

from __future__ import annotations

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from auth.config import MONGODB_URL

_client: MongoClient | None = None


def get_client() -> MongoClient:
    """Return a cached MongoDB client, creating it if needed."""
    global _client
    if _client is None:
        _client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
    return _client


def get_users_collection():
    """Return the users collection used for credential storage."""
    db = get_client().get_default_database()
    return db["users"]


def ping_database() -> bool:
    """Check whether the MongoDB server is reachable."""
    try:
        get_client().admin.command("ping")
        return True
    except ConnectionFailure:
        return False
