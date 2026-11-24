"""Settings in one place, read from the environment with defaults. No secrets live here."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
STAGING_DIR = DATA_DIR / "staging"
SERVING_DIR = DATA_DIR / "serving"
SOURCE_FILES = ROOT / "source_files"
