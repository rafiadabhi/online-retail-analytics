import argparse
from pathlib import Path

import pandas as pd

from src.config import OUTPUT_DIR, TABLEAU_CSV, ensure_directories
from src.db import get_engine


TABLEAU_COLUMNS = [
    "record_type",
    "record_id",
    "transaction_id",
    "invoice_no",
    "invoice_date",
    "transaction_year",
    "transaction_month",
    "source_period",
    "stock_code",
    "description",
    "quantity",
    "unit_price",
    "customer_id",
    "country",
    "revenue",
    "is_merchandise",
    "primary_country",
    "first_purchase_date",
    "last_purchase_date",
    "recency_days",
    "frequency",
    "monetary",
    "average_order_value",
    "total_items",
    "unique_products",
    "active_months",
    "tenure_days",
    "avg_days_between_orders",
    "rfm_score",
    "rfm_segment",
    "rule_based_churn_status",
    "rfm_cluster",
    "churn_probability",
    "churn_risk_band",
    "predicted_90d_value",
    "churn_score_method",
]


def validate_postgres_source(engine) -> dict[str, int]:
    count_sql = """
        SELECT record_type, COUNT(*)::bigint AS row_count
        FROM retail.tableau_dashboard_dataset
        GROUP BY record_type
    """
    integrity_sql = """
        SELECT
            COUNT(*)::bigint AS total_rows,
            COUNT(DISTINCT record_id)::bigint AS unique_record_ids,
            COUNT(*) FILTER (
                WHERE record_type = 'Transaction'
                  AND (monetary IS NOT NULL OR churn_probability IS NOT NULL)
            )::bigint AS contaminated_transaction_rows,
            COUNT(*) FILTER (
                WHERE record_type = 'Customer'
                  AND (transaction_id IS NOT NULL OR revenue IS NOT NULL)
            )::bigint AS contaminated_customer_rows
        FROM retail.tableau_dashboard_dataset
    """

    with engine.connect() as connection:
        counts = {
            row.record_type: int(row.row_count)
            for row in connection.exec_driver_sql(count_sql)
        }
        integrity = connection.exec_driver_sql(integrity_sql).mappings().one()

    if set(counts) != {"Transaction", "Customer"}:
        raise ValueError(f"Unexpected record types in Tableau view: {counts}")
    if any(value <= 0 for value in counts.values()):
        raise ValueError(f"Tableau view contains an empty record type: {counts}")
    if integrity["total_rows"] != integrity["unique_record_ids"]:
        raise ValueError("Tableau view contains duplicate record_id values.")
    if integrity["contaminated_transaction_rows"] != 0:
        raise ValueError("Transaction rows contain customer-grain measures.")
    if integrity["contaminated_customer_rows"] != 0:
        raise ValueError("Customer rows contain transaction-grain measures.")
    return counts


def export_from_postgres(path: Path, engine) -> int:
    query = """
        SELECT *
        FROM retail.tableau_dashboard_dataset
        ORDER BY
            CASE record_type WHEN 'Customer' THEN 1 ELSE 2 END,
            transaction_id,
            customer_id
    """
    total_rows = 0
    for chunk_number, frame in enumerate(
        pd.read_sql(query, engine, chunksize=100_000)
    ):
        if list(frame.columns) != TABLEAU_COLUMNS:
            raise ValueError(
                "PostgreSQL Tableau view columns do not match the export contract. "
                f"Observed: {list(frame.columns)}"
            )
        frame.to_csv(
            path,
            mode="w" if chunk_number == 0 else "a",
            header=chunk_number == 0,
            index=False,
            date_format="%Y-%m-%d %H:%M:%S",
        )
        total_rows += len(frame)
    return total_rows


def validate_export(path: Path, expected_counts: dict[str, int]) -> None:
    observed_counts = {"Transaction": 0, "Customer": 0}
    for frame in pd.read_csv(
        path,
        usecols=[
            "record_type",
            "record_id",
            "transaction_id",
            "revenue",
            "monetary",
            "churn_probability",
        ],
        chunksize=100_000,
    ):
        if frame["record_id"].isna().any():
            raise ValueError("Exported Tableau dataset contains a missing record_id.")
        unexpected_types = set(frame["record_type"].dropna()) - set(observed_counts)
        if unexpected_types:
            raise ValueError(f"Unexpected record types in CSV: {unexpected_types}")

        transaction_rows = frame["record_type"].eq("Transaction")
        customer_rows = frame["record_type"].eq("Customer")
        transaction_customer_fields = frame.loc[
            transaction_rows, ["monetary", "churn_probability"]
        ]
        customer_transaction_fields = frame.loc[
            customer_rows, ["transaction_id", "revenue"]
        ]
        if transaction_customer_fields.notna().any().any():
            raise ValueError("Exported transaction rows contain customer measures.")
        if customer_transaction_fields.notna().any().any():
            raise ValueError("Exported customer rows contain transaction measures.")

        counts = frame["record_type"].value_counts()
        for record_type in observed_counts:
            observed_counts[record_type] += int(counts.get(record_type, 0))

    if observed_counts != expected_counts:
        raise ValueError(
            "Exported row counts do not match PostgreSQL: "
            f"{observed_counts} != {expected_counts}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Export the validated PostgreSQL Tableau view to one centralized CSV."
        )
    )
    parser.parse_args()

    ensure_directories()

    # data/outputs is intentionally reserved for one final Tableau file.
    for generated_file in OUTPUT_DIR.iterdir():
        if generated_file.is_file() and generated_file.name != ".gitkeep":
            generated_file.unlink()

    temporary_path = TABLEAU_CSV.with_suffix(TABLEAU_CSV.suffix + ".tmp")
    engine = get_engine()
    expected_counts = validate_postgres_source(engine)

    try:
        total_rows = export_from_postgres(temporary_path, engine)
        if total_rows == 0:
            raise RuntimeError("PostgreSQL Tableau export returned zero rows.")
        validate_export(temporary_path, expected_counts)
        temporary_path.replace(TABLEAU_CSV)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    print(f"Exported {total_rows:,} PostgreSQL rows to: {TABLEAU_CSV}")
    print(f"Record counts: {expected_counts}")
    print("Use this one CSV as the only data source in Tableau Public.")


if __name__ == "__main__":
    main()
