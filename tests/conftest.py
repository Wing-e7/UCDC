import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

# Ensure tests are isolated and don't require a running Postgres instance.
TEST_DB_PATH = ROOT / "test-ucdc.sqlite"
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ.setdefault("DATABASE_URL", f"sqlite+pysqlite:///{TEST_DB_PATH}")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret")
os.environ.setdefault("CONSENT_ISSUER", "ucdc-test")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("UCDC_ENV", "test")

