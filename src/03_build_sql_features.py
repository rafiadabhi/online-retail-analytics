from src.config import SQL_DIR
from src.db import execute_sql_file, test_connection


def main() -> None:
    print(test_connection())
    execute_sql_file(SQL_DIR / "02_analytics.sql")
    print("Created SQL analytics tables and materialized views in schema retail.")


if __name__ == "__main__":
    main()
