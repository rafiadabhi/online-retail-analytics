import argparse
from pathlib import Path

import psycopg2

from src.config import (
    CLEAN_CSV,
    SQL_DIR,
    psycopg2_params,
    validate_database_config,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Load clean retail transactions into PostgreSQL.")
    parser.add_argument("--csv", type=Path, default=CLEAN_CSV)
    args = parser.parse_args()

    if not args.csv.exists():
        raise FileNotFoundError(f"Clean CSV not found: {args.csv}")

    validate_database_config()
    schema_sql = (SQL_DIR / "01_schema.sql").read_text(encoding="utf-8")
    connection = psycopg2.connect(**psycopg2_params())
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(schema_sql)
                with args.csv.open("r", encoding="utf-8", newline="") as csv_file:
                    cursor.copy_expert(
                        """
                        COPY retail.transactions (
                            invoice_no, stock_code, description, quantity,
                            invoice_date, unit_price, customer_id, country,
                            source_period, revenue
                        )
                        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
                        """,
                        csv_file,
                    )
                cursor.execute(
                    "CREATE INDEX idx_transactions_customer ON retail.transactions (customer_id)"
                )
                cursor.execute(
                    "CREATE INDEX idx_transactions_invoice_date ON retail.transactions (invoice_date)"
                )
                cursor.execute(
                    "CREATE INDEX idx_transactions_invoice ON retail.transactions (invoice_no)"
                )
                cursor.execute(
                    "CREATE INDEX idx_transactions_stock ON retail.transactions (stock_code)"
                )
                cursor.execute("ANALYZE retail.transactions")
                cursor.execute("SELECT COUNT(*) FROM retail.transactions")
                row_count = cursor.fetchone()[0]
                if row_count <= 0:
                    raise RuntimeError("PostgreSQL load completed with zero rows.")
        print(f"Loaded {row_count:,} rows into retail.transactions")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
