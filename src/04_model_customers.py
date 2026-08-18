import argparse
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.cluster import KMeans
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    silhouette_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.config import MODEL_DIR, ensure_directories
from src.db import get_engine


FEATURE_COLUMNS = [
    "recency_days",
    "frequency",
    "monetary",
    "average_order_value",
    "unique_products",
    "active_days",
    "tenure_days",
    "avg_days_between_orders",
]

SNAPSHOT_DATES = pd.to_datetime(
    [
        "2010-06-01",
        "2010-09-01",
        "2010-12-01",
        "2011-03-01",
        "2011-06-01",
        "2011-09-01",
    ]
)
OBSERVATION_DAYS = 180
PREDICTION_DAYS = 90
OBSERVATION_DELTA = pd.Timedelta(OBSERVATION_DAYS, unit="D")
PREDICTION_DELTA = pd.Timedelta(PREDICTION_DAYS, unit="D")
ONE_DAY = pd.Timedelta(1, unit="D")


def load_transactions() -> pd.DataFrame:
    query = """
        SELECT invoice_no, stock_code, quantity, invoice_date,
               unit_price, customer_id, country, revenue
        FROM retail.transactions
    """
    df = pd.read_sql(query, get_engine())

    df["invoice_date"] = pd.to_datetime(df["invoice_date"])
    df["customer_id"] = df["customer_id"].astype("string")
    df["invoice_no"] = df["invoice_no"].astype("string")
    df["stock_code"] = df["stock_code"].astype("string")
    df["revenue"] = pd.to_numeric(df["revenue"])
    return df


def create_order_level(transactions: pd.DataFrame) -> pd.DataFrame:
    return (
        transactions.groupby(["customer_id", "invoice_no"], as_index=False)
        .agg(
            order_date=("invoice_date", "min"),
            order_revenue=("revenue", "sum"),
            order_items=("quantity", "sum"),
        )
        .sort_values(["customer_id", "order_date", "invoice_no"])
    )


def load_lifetime_features() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM retail.customer_features", get_engine())


def build_snapshot_dataset(
    transactions: pd.DataFrame,
    orders: pd.DataFrame,
    snapshots: pd.DatetimeIndex = SNAPSHOT_DATES,
) -> pd.DataFrame:
    first_purchase = orders.groupby("customer_id")["order_date"].min()
    frames = []

    for snapshot in snapshots:
        observation_start = snapshot - OBSERVATION_DELTA
        prediction_end = snapshot + PREDICTION_DELTA

        history_orders = orders[
            (orders["order_date"] >= observation_start)
            & (orders["order_date"] < snapshot)
        ].copy()
        history_tx = transactions[
            (transactions["invoice_date"] >= observation_start)
            & (transactions["invoice_date"] < snapshot)
        ]
        future_orders = orders[
            (orders["order_date"] >= snapshot)
            & (orders["order_date"] < prediction_end)
        ]

        history_orders["previous_order_date"] = history_orders.groupby("customer_id")[
            "order_date"
        ].shift()
        history_orders["gap_days"] = (
            history_orders["order_date"] - history_orders["previous_order_date"]
        ).dt.days

        features = history_orders.groupby("customer_id", as_index=False).agg(
            last_order_date=("order_date", "max"),
            frequency=("invoice_no", "nunique"),
            monetary=("order_revenue", "sum"),
            average_order_value=("order_revenue", "mean"),
            active_days=("order_date", lambda s: s.dt.normalize().nunique()),
            avg_days_between_orders=("gap_days", "mean"),
        )
        unique_products = history_tx.groupby("customer_id")["stock_code"].nunique()
        features["unique_products"] = features["customer_id"].map(unique_products)
        features["recency_days"] = (
            snapshot - features["last_order_date"].dt.normalize()
        ).dt.days
        features["tenure_days"] = (
            snapshot - features["customer_id"].map(first_purchase).dt.normalize()
        ).dt.days

        future = future_orders.groupby("customer_id", as_index=False).agg(
            future_orders=("invoice_no", "nunique"),
            future_revenue=("order_revenue", "sum"),
        )
        features = features.merge(future, on="customer_id", how="left")
        features[["future_orders", "future_revenue"]] = features[
            ["future_orders", "future_revenue"]
        ].fillna(0)
        features["churn"] = (features["future_orders"] == 0).astype("int8")
        features["snapshot_date"] = snapshot
        frames.append(features)

    return pd.concat(frames, ignore_index=True)


def create_current_features(
    transactions: pd.DataFrame, orders: pd.DataFrame
) -> pd.DataFrame:
    snapshot = transactions["invoice_date"].max().normalize() + ONE_DAY
    observation_start = snapshot - OBSERVATION_DELTA
    all_customers = pd.DataFrame({"customer_id": transactions["customer_id"].unique()})
    first_purchase = orders.groupby("customer_id")["order_date"].min()
    last_purchase = orders.groupby("customer_id")["order_date"].max()

    history_orders = orders[
        (orders["order_date"] >= observation_start) & (orders["order_date"] < snapshot)
    ].copy()
    history_tx = transactions[
        (transactions["invoice_date"] >= observation_start)
        & (transactions["invoice_date"] < snapshot)
    ]
    history_orders["previous_order_date"] = history_orders.groupby("customer_id")[
        "order_date"
    ].shift()
    history_orders["gap_days"] = (
        history_orders["order_date"] - history_orders["previous_order_date"]
    ).dt.days

    features = history_orders.groupby("customer_id", as_index=False).agg(
        frequency=("invoice_no", "nunique"),
        monetary=("order_revenue", "sum"),
        average_order_value=("order_revenue", "mean"),
        active_days=("order_date", lambda s: s.dt.normalize().nunique()),
        avg_days_between_orders=("gap_days", "mean"),
    )
    features["unique_products"] = features["customer_id"].map(
        history_tx.groupby("customer_id")["stock_code"].nunique()
    )

    current = all_customers.merge(features, on="customer_id", how="left")
    current["recency_days"] = (
        snapshot - current["customer_id"].map(last_purchase).dt.normalize()
    ).dt.days
    current["tenure_days"] = (
        snapshot - current["customer_id"].map(first_purchase).dt.normalize()
    ).dt.days
    for column in [
        "frequency",
        "monetary",
        "average_order_value",
        "unique_products",
        "active_days",
    ]:
        current[column] = current[column].fillna(0)
    return current


def fit_rfm_clusters(lifetime: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    cluster_data = lifetime[["recency_days", "frequency", "monetary"]].copy()
    cluster_data = np.log1p(cluster_data.clip(lower=0))
    scaler = StandardScaler()
    scaled = scaler.fit_transform(cluster_data)

    scores = {}
    sample_size = min(len(lifetime), 5000)
    rng = np.random.default_rng(42)
    sample_idx = rng.choice(len(lifetime), size=sample_size, replace=False)
    for k in range(2, 7):
        candidate = KMeans(n_clusters=k, random_state=42, n_init=20)
        labels = candidate.fit_predict(scaled)
        scores[k] = float(silhouette_score(scaled[sample_idx], labels[sample_idx]))

    best_k = max(scores, key=scores.get)
    model = KMeans(n_clusters=best_k, random_state=42, n_init=30)
    lifetime = lifetime.copy()
    lifetime["rfm_cluster"] = model.fit_predict(scaled).astype(int)

    profiles = lifetime.groupby("rfm_cluster", as_index=False).agg(
        customers=("customer_id", "nunique"),
        avg_recency=("recency_days", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
        total_revenue=("monetary", "sum"),
    )
    metadata = {"selected_k": int(best_k), "silhouette_scores": scores}
    joblib.dump({"model": model, "scaler": scaler}, MODEL_DIR / "rfm_kmeans.joblib")
    return lifetime, profiles, metadata


def classifier_metrics(model, x_data, y_data) -> dict:
    probability = model.predict_proba(x_data)[:, 1]
    prediction = (probability >= 0.5).astype(int)
    return {
        "roc_auc": roc_auc_score(y_data, probability),
        "pr_auc": average_precision_score(y_data, probability),
        "f1": f1_score(y_data, prediction, zero_division=0),
        "precision": precision_score(y_data, prediction, zero_division=0),
        "recall": recall_score(y_data, prediction, zero_division=0),
    }


def regression_metrics(actual, prediction) -> dict:
    return {
        "mae": mean_absolute_error(actual, prediction),
        "rmse": mean_squared_error(actual, prediction) ** 0.5,
        "r2": r2_score(actual, prediction),
    }


def train_models(snapshot_data: pd.DataFrame):
    snapshot_dates = sorted(snapshot_data["snapshot_date"].drop_duplicates())
    if len(snapshot_dates) < 3:
        raise ValueError("At least three snapshots are required for train/validation/test.")

    validation_date = snapshot_dates[-2]
    test_date = snapshot_dates[-1]
    train = snapshot_data[snapshot_data["snapshot_date"] < validation_date]
    validation = snapshot_data[snapshot_data["snapshot_date"] == validation_date]
    test = snapshot_data[snapshot_data["snapshot_date"] == test_date]

    if train.empty or validation.empty or test.empty:
        raise ValueError("Temporal train/validation/test split produced an empty set.")

    x_train = train[FEATURE_COLUMNS]
    y_train = train["churn"]
    x_validation = validation[FEATURE_COLUMNS]
    y_validation = validation["churn"]
    x_test = test[FEATURE_COLUMNS]
    y_test = test["churn"]

    classifiers = {
        "Logistic Regression": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=2000, class_weight="balanced", random_state=42
                    ),
                ),
            ]
        ),
        "Random Forest": Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=300,
                        min_samples_leaf=5,
                        class_weight="balanced_subsample",
                        random_state=42,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
    }

    results = []
    validation_scores = {}
    for name, classifier in classifiers.items():
        candidate = clone(classifier)
        candidate.fit(x_train, y_train)
        metrics = classifier_metrics(candidate, x_validation, y_validation)
        validation_scores[name] = metrics["roc_auc"]
        results.extend(
            {
                "model_type": "churn_classification",
                "model_name": name,
                "evaluation_split": "validation",
                "evaluation_snapshot": validation_date.date().isoformat(),
                "metric": metric,
                "value": value,
            }
            for metric, value in metrics.items()
        )

    best_classifier_name = max(validation_scores, key=validation_scores.get)
    development = pd.concat([train, validation], ignore_index=True)
    best_classifier = clone(classifiers[best_classifier_name])
    best_classifier.fit(development[FEATURE_COLUMNS], development["churn"])
    test_metrics = classifier_metrics(best_classifier, x_test, y_test)
    results.extend(
        {
            "model_type": "churn_classification",
            "model_name": best_classifier_name,
            "evaluation_split": "test",
            "evaluation_snapshot": test_date.date().isoformat(),
            "metric": metric,
            "value": value,
        }
        for metric, value in test_metrics.items()
    )

    value_model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                TransformedTargetRegressor(
                    regressor=HistGradientBoostingRegressor(
                        max_iter=200, learning_rate=0.05, random_state=42
                    ),
                    func=np.log1p,
                    inverse_func=np.expm1,
                ),
            ),
        ]
    )
    value_model.fit(development[FEATURE_COLUMNS], development["future_revenue"])
    value_prediction = np.clip(value_model.predict(x_test), 0, None)
    value_metrics = regression_metrics(test["future_revenue"], value_prediction)
    results.extend(
        {
            "model_type": "customer_value_regression",
            "model_name": "Gradient Boosting (log target)",
            "evaluation_split": "test",
            "evaluation_snapshot": test_date.date().isoformat(),
            "metric": metric,
            "value": value,
        }
        for metric, value in value_metrics.items()
    )

    metrics_frame = pd.DataFrame(results)
    metrics_frame["selected_model"] = (
        (metrics_frame["model_type"] == "customer_value_regression")
        | (metrics_frame["model_name"] == best_classifier_name)
    )

    joblib.dump(best_classifier, MODEL_DIR / "churn_classifier.joblib")
    joblib.dump(value_model, MODEL_DIR / "customer_value_90d.joblib")
    return (
        best_classifier_name,
        best_classifier,
        value_model,
        metrics_frame,
        validation_date,
        test_date,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build RFM clusters, churn scores, and 90-day value estimates "
            "from PostgreSQL, then write model outputs back to PostgreSQL."
        )
    )
    parser.parse_args()

    ensure_directories()
    transactions = load_transactions()
    orders = create_order_level(transactions)
    lifetime = load_lifetime_features()
    lifetime["customer_id"] = lifetime["customer_id"].astype("string")

    clustered, profiles, cluster_metadata = fit_rfm_clusters(lifetime)
    snapshots = build_snapshot_dataset(transactions, orders)
    (
        classifier_name,
        classifier,
        value_model,
        metrics,
        validation_date,
        test_date,
    ) = train_models(snapshots)
    current = create_current_features(transactions, orders)

    active_mask = current["frequency"] > 0
    current["churn_probability"] = 0.99
    current["churn_score_method"] = "Rule: no purchase in observation window"
    current.loc[active_mask, "churn_probability"] = classifier.predict_proba(
        current.loc[active_mask, FEATURE_COLUMNS]
    )[:, 1]
    current.loc[active_mask, "churn_score_method"] = "Selected classification model"
    current["predicted_90d_value"] = 0.0
    current.loc[active_mask, "predicted_90d_value"] = np.clip(
        value_model.predict(current.loc[active_mask, FEATURE_COLUMNS]), 0, None
    )
    current["churn_risk_band"] = pd.cut(
        current["churn_probability"],
        bins=[-np.inf, 0.40, 0.70, np.inf],
        labels=["Low", "Medium", "High"],
    ).astype("string")

    cluster_map = clustered.set_index("customer_id")["rfm_cluster"]
    current["rfm_cluster"] = current["customer_id"].map(cluster_map).astype("Int64")
    customer_analytics = current[
        [
            "customer_id",
            "rfm_cluster",
            "churn_probability",
            "churn_risk_band",
            "predicted_90d_value",
            "churn_score_method",
        ]
    ].copy()
    customer_analytics["churn_probability"] = customer_analytics[
        "churn_probability"
    ].round(4)
    customer_analytics["predicted_90d_value"] = customer_analytics[
        "predicted_90d_value"
    ].round(2)

    customer_dashboard = clustered[
        [
            "customer_id",
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
        ]
    ].merge(
        customer_analytics.drop(columns="rfm_cluster"),
        on="customer_id",
        how="left",
        validate="one_to_one",
    )

    if len(customer_dashboard) != lifetime["customer_id"].nunique():
        raise ValueError("Customer dashboard export does not have one row per customer.")
    if customer_dashboard[
        ["rfm_segment", "churn_probability", "predicted_90d_value"]
    ].isna().any().any():
        raise ValueError("Customer dashboard export contains missing analytical fields.")

    metadata = {
        "observation_window_days": OBSERVATION_DAYS,
        "prediction_window_days": PREDICTION_DAYS,
        "snapshot_dates": [d.date().isoformat() for d in SNAPSHOT_DATES],
        "validation_snapshot": validation_date.date().isoformat(),
        "test_snapshot": test_date.date().isoformat(),
        "classification_selection_metric": "validation_roc_auc",
        "selected_churn_model": classifier_name,
        **cluster_metadata,
    }
    (MODEL_DIR / "model_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    engine = get_engine()
    metrics_for_db = metrics.copy()
    metrics_for_db["evaluation_snapshot"] = pd.to_datetime(
        metrics_for_db["evaluation_snapshot"]
    ).dt.date
    with engine.begin() as connection:
        connection.exec_driver_sql(
                """
                DROP TABLE IF EXISTS retail.customer_analytics CASCADE;
                DROP TABLE IF EXISTS retail.cluster_profiles CASCADE;
                DROP TABLE IF EXISTS retail.model_metrics CASCADE;

                CREATE TABLE retail.customer_analytics (
                    customer_id TEXT PRIMARY KEY
                        REFERENCES retail.customer_features(customer_id),
                    rfm_cluster INTEGER NOT NULL CHECK (rfm_cluster >= 0),
                    churn_probability NUMERIC(6, 4) NOT NULL
                        CHECK (churn_probability BETWEEN 0 AND 1),
                    churn_risk_band TEXT NOT NULL
                        CHECK (churn_risk_band IN ('Low', 'Medium', 'High')),
                    predicted_90d_value NUMERIC(16, 2) NOT NULL
                        CHECK (predicted_90d_value >= 0),
                    churn_score_method TEXT NOT NULL
                );

                CREATE TABLE retail.cluster_profiles (
                    rfm_cluster INTEGER PRIMARY KEY,
                    customers BIGINT NOT NULL CHECK (customers > 0),
                    avg_recency DOUBLE PRECISION NOT NULL,
                    avg_frequency DOUBLE PRECISION NOT NULL,
                    avg_monetary DOUBLE PRECISION NOT NULL,
                    total_revenue DOUBLE PRECISION NOT NULL
                );

                CREATE TABLE retail.model_metrics (
                    model_type TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    evaluation_split TEXT NOT NULL
                        CHECK (evaluation_split IN ('validation', 'test')),
                    evaluation_snapshot DATE NOT NULL,
                    metric TEXT NOT NULL,
                    value DOUBLE PRECISION NOT NULL,
                    selected_model BOOLEAN NOT NULL,
                    PRIMARY KEY (model_type, model_name, evaluation_split, metric)
                );
                """
        )
        customer_analytics.to_sql(
            "customer_analytics",
            connection,
            schema="retail",
            if_exists="append",
            index=False,
            method="multi",
            chunksize=2000,
        )
        profiles.to_sql(
            "cluster_profiles",
            connection,
            schema="retail",
            if_exists="append",
            index=False,
        )
        metrics_for_db.to_sql(
            "model_metrics",
            connection,
            schema="retail",
            if_exists="append",
            index=False,
        )

    print(json.dumps(metadata, indent=2))
    print(metrics.to_string(index=False))
    print("Model outputs written to PostgreSQL schema retail.")
    print(f"Model files saved to: {MODEL_DIR}")


if __name__ == "__main__":
    main()
