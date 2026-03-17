"""ASGI entrypoint for the Task Management backend.

Many deployment environments default to importing `main:app` from the repository
or container root. The actual FastAPI application lives in `src.api.main`.

This file ensures the running service exposes the full API (/auth/* and /tasks).
"""

from src.api.main import app  # noqa: F401
