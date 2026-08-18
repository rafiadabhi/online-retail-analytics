from pathlib import Path

from src.config import database_url, validate_database_config


def get_engine():
    from sqlalchemy import create_engine

    validate_database_config()
    return create_engine(database_url(), pool_pre_ping=True)


def test_connection() -> str:
    from sqlalchemy import text

    engine = get_engine()
    with engine.connect() as connection:
        return connection.execute(text("SELECT version()")).scalar_one()


def execute_sql_file(path: Path) -> None:
    """Execute a trusted project SQL file as one PostgreSQL script."""
    sql = path.read_text(encoding="utf-8")
    engine = get_engine()
    with engine.begin() as connection:
        connection.exec_driver_sql(sql)
