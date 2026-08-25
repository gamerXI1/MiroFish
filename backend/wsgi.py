"""Gunicorn entrypoint for the main MiroFish backend."""

from app import create_app
from app.config import Config

errors = Config.validate()
if errors:
    raise RuntimeError("; ".join(errors))

app = create_app()
