from src.config import SQL_DIR
from src.db import execute_sql_file


def main() -> None:
    execute_sql_file(SQL_DIR / "03_tableau_views.sql")
    print("Created Tableau-ready views in schema retail.")


if __name__ == "__main__":
    main()
