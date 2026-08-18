import subprocess
import sys
from pathlib import Path

from src.config import OUTPUT_DIR, TABLEAU_CSV, ensure_directories


STEPS = [
    "src.01_clean_data",
    "src.02_load_postgresql",
    "src.03_build_sql_features",
    "src.04_model_customers",
    "src.05_build_tableau_views",
    "src.06_export_tableau_csv",
]


def main() -> None:
    project_root = Path(__file__).resolve().parent
    raw_file = project_root / "data" / "raw" / "online_retail_II.xlsx"
    env_file = project_root / ".env"
    if not raw_file.exists():
        raise FileNotFoundError(f"Required raw dataset not found: {raw_file}")
    if not env_file.exists():
        raise FileNotFoundError(
            f"Database configuration not found: {env_file}. "
            "Copy .env.example to .env and enter your PostgreSQL password."
        )

    # data/outputs is reserved for the single final Tableau dataset. Removing
    # stale generated files prevents a failed run from leaving an old export
    # that looks current.
    ensure_directories()
    for generated_file in OUTPUT_DIR.iterdir():
        if generated_file.is_file() and generated_file.name != ".gitkeep":
            generated_file.unlink()

    for module in STEPS:
        print(f"\nRunning {module}...")
        subprocess.run([sys.executable, "-m", module], check=True)

    if not TABLEAU_CSV.exists() or TABLEAU_CSV.stat().st_size == 0:
        raise RuntimeError(
            f"Pipeline finished without a valid Tableau output: {TABLEAU_CSV}"
        )
    print(
        "\nPipeline complete. Use this one file for all Tableau dashboards:\n"
        f"{TABLEAU_CSV}"
    )


if __name__ == "__main__":
    main()
