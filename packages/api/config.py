import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
APP_DIR = STATIC_DIR / "app"

# Load .env from packages/api directory, falling back to CWD
load_dotenv(BASE_DIR / ".env")
load_dotenv()

DB_URL = os.getenv("DB_URL")
ENV = os.getenv("ENV", "DEV")
