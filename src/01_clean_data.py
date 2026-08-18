import argparse
import json
from pathlib import Path
import time

import pandas as pd

from src.config import (
    CLEAN_CSV,
    DATA_QUALITY_REPORT,
    RAW_XLSX,
    ensure_directories,
)


COLUMN_MAP = {
    "Invoice": "invoice_no",
    "StockCode": "stock_code",
    "Description": "description",
    "Quantity": "quantity",
    "InvoiceDate": "invoice_date",
    "Price": "unit_price",
    "Customer ID": "customer_id",
    "Country": "country",
}

COUNTRY_NAME_MAP = {
    "EIRE": "Ireland",
    "Korea": "South Korea",
    "RSA": "South Africa",
    "USA": "United States",
}


def load_workbook(path: Path) -> pd.DataFrame:
    sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    frames = []
    for sheet_name, frame in sheets.items():
        frame = frame.copy()
        frame["source_period"] = sheet_name
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def clean_transactions(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = raw.rename(columns=COLUMN_MAP).copy()

    required = set(COLUMN_MAP.values())
    missing_columns = sorted(required.difference(df.columns))
    if missing_columns:
        raise ValueError(f"Required columns missing: {missing_columns}")

    df["invoice_no"] = df["invoice_no"].astype("string").str.strip()
    df["stock_code"] = df["stock_code"].astype("string").str.strip()
    df["description"] = df["description"].astype("string").str.strip()
    df["customer_id"] = (
        pd.to_numeric(df["customer_id"], errors="coerce")
        .astype("Int64")
        .astype("string")
    )
    df["country"] = df["country"].astype("string").str.strip()
    df["country"] = df["country"].replace(COUNTRY_NAME_MAP)
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")

    raw_rows = len(df)
    duplicate_rows = int(df.duplicated().sum())
    missing_customer_rows = int(df["customer_id"].isna().sum())
    missing_description_rows = int(df["description"].isna().sum())
    cancelled_rows = int(df["invoice_no"].str.upper().str.startswith("C", na=False).sum())
    invalid_quantity_rows = int((df["quantity"] <= 0).sum())
    invalid_price_rows = int((df["unit_price"] <= 0).sum())

    df = df.drop_duplicates().copy()
    df["is_cancelled"] = df["invoice_no"].str.upper().str.startswith("C", na=False)

    valid_mask = (
        df["invoice_date"].notna()
        & df["invoice_no"].notna()
        & df["invoice_no"].ne("")
        & df["stock_code"].notna()
        & df["stock_code"].ne("")
        & df["customer_id"].notna()
        & df["country"].notna()
        & df["country"].ne("")
        & df["quantity"].gt(0)
        & df["unit_price"].gt(0)
        & ~df["is_cancelled"]
    )
    clean = df.loc[valid_mask].copy()
    clean["quantity"] = clean["quantity"].astype("int64")
    # Preserve the source's three-decimal prices (including legitimate £0.001
    # lines). Rounding to two decimals created zero revenue and violated the
    # PostgreSQL CHECK constraint during COPY.
    clean["unit_price"] = clean["unit_price"].round(3)
    clean["revenue"] = (clean["quantity"] * clean["unit_price"]).round(3)

    clean = clean[
        [
            "invoice_no",
            "stock_code",
            "description",
            "quantity",
            "invoice_date",
            "unit_price",
            "customer_id",
            "country",
            "source_period",
            "revenue",
        ]
    ].sort_values(["invoice_date", "invoice_no", "stock_code"])

    if clean.empty:
        raise ValueError("Cleaning produced zero valid transactions.")
    if clean["revenue"].le(0).any():
        raise ValueError("Clean data contains nonpositive revenue.")
    expected_revenue = (clean["quantity"] * clean["unit_price"]).round(3)
    if not clean["revenue"].equals(expected_revenue):
        raise ValueError("Revenue validation failed after rounding.")

    report = {
        "raw_rows": raw_rows,
        "duplicate_rows_detected": duplicate_rows,
        "missing_customer_rows": missing_customer_rows,
        "missing_description_rows": missing_description_rows,
        "cancelled_invoice_rows": cancelled_rows,
        "quantity_le_zero_rows": invalid_quantity_rows,
        "price_le_zero_rows": invalid_price_rows,
        "clean_rows": len(clean),
        "clean_customers": int(clean["customer_id"].nunique()),
        "clean_invoices": int(clean["invoice_no"].nunique()),
        "clean_countries": int(clean["country"].nunique()),
        "clean_date_min": clean["invoice_date"].min().isoformat(),
        "clean_date_max": clean["invoice_date"].max().isoformat(),
        "clean_revenue": round(float(clean["revenue"].sum()), 3),
    }
    return clean, report


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean the UCI Online Retail II workbook.")
    parser.add_argument("--input", type=Path, default=RAW_XLSX)
    parser.add_argument("--output", type=Path, default=CLEAN_CSV)
    args = parser.parse_args()

    ensure_directories()
    if not args.input.exists():
        raise FileNotFoundError(f"Dataset not found: {args.input}")

    started = time.time()
    raw = load_workbook(args.input)
    clean, report = clean_transactions(raw)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(args.output, index=False, date_format="%Y-%m-%d %H:%M:%S")
    report_path = DATA_QUALITY_REPORT
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"Saved clean data to: {args.output}")
    print(f"Saved data-quality report to: {report_path}")
    print(f"Elapsed seconds: {time.time() - started:.1f}")


if __name__ == "__main__":
    main()
