from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_local_env(path: Path) -> None:
    """Load simple KEY=VALUE entries without an additional dependency."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env(PROJECT_ROOT / ".env")

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"
MODEL_DIR = PROJECT_ROOT / "models"
SQL_DIR = PROJECT_ROOT / "sql"

RAW_XLSX = RAW_DIR / "online_retail_II.xlsx"
CLEAN_CSV = PROCESSED_DIR / "retail_transactions_clean.csv"
DATA_QUALITY_REPORT = PROCESSED_DIR / "data_quality_report.json"
TABLEAU_CSV = OUTPUT_DIR / "tableau_dashboard_dataset.csv"


def ensure_directories() -> None:
    for directory in (RAW_DIR, PROCESSED_DIR, OUTPUT_DIR, MODEL_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def database_url():
    """Build a SQLAlchemy URL without manually concatenating the password."""
    from sqlalchemy import URL

    return URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        database=os.getenv("PGDATABASE", "online_retail_db"),
    )


def psycopg2_params() -> dict:
    return {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "5432")),
        "dbname": os.getenv("PGDATABASE", "online_retail_db"),
        "user": os.getenv("PGUSER", "postgres"),
        "password": os.getenv("PGPASSWORD", ""),
    }


def validate_database_config() -> None:
    password = os.getenv("PGPASSWORD", "")
    if not password or password == "CHANGE_ME":
        raise RuntimeError(
            "PostgreSQL password is not configured. Copy .env.example to .env "
            "and replace PGPASSWORD=CHANGE_ME with your actual password."
        )
