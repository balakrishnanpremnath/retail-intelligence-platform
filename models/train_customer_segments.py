from pathlib import Path
import joblib
import pandas as pd
import numpy as np

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parents[1]

DATA_FILE = (
    ROOT_DIR
    / "data"
    / "processed"
    / "customer_rfm.csv"
)

MODEL_DIR = ROOT_DIR / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

def load_data():

    df = pd.read_csv(
        DATA_FILE
    )

    return df


# ---------------------------------------------------------
# PREPARE RFM FEATURES
# ---------------------------------------------------------

def prepare_features(df):

    features = df[
        [
            "recency",
            "frequency",
            "monetary"
        ]
    ].copy()

    # Reduce skew before clustering
    features["frequency"] = np.log1p(
        features["frequency"]
    )

    features["monetary"] = np.log1p(
        features["monetary"]
    )

    scaler = StandardScaler()

    scaled_features = scaler.fit_transform(
        features
    )

    return (
        features,
        scaled_features,
        scaler
    )


# ---------------------------------------------------------
# FIND SUITABLE K
# ---------------------------------------------------------

def evaluate_k_values(
    scaled_features
):

    results = []

    for k in range(2, 7):

        model = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=20
        )

        labels = model.fit_predict(
            scaled_features
        )

        score = silhouette_score(
            scaled_features,
            labels
        )

        results.append({
            "k": k,
            "silhouette_score": score
        })

    return pd.DataFrame(
        results
    )


# ---------------------------------------------------------
# TRAIN FINAL MODEL
# ---------------------------------------------------------

def train_model(
    scaled_features,
    k=4
):

    model = KMeans(
        n_clusters=k,
        random_state=42,
        n_init=20
    )

    clusters = model.fit_predict(
        scaled_features
    )

    return model, clusters


# ---------------------------------------------------------
# PROFILE CLUSTERS
# ---------------------------------------------------------

def create_cluster_profile(df):

    profile = (
        df
        .groupby(
            "cluster",
            as_index=False
        )
        .agg(
            customers=(
                "customer_id",
                "count"
            ),

            avg_recency=(
                "recency",
                "mean"
            ),

            avg_frequency=(
                "frequency",
                "mean"
            ),

            avg_monetary=(
                "monetary",
                "mean"
            )
        )
    )

    return profile


# ---------------------------------------------------------
# BUSINESS-FRIENDLY LABELS
# ---------------------------------------------------------

def assign_segment_labels(profile):

    profile = profile.copy()

    remaining_clusters = set(
        profile["cluster"]
    )

    label_map = {}

    # High Value:
    # high spending + high purchase frequency + recent activity
    profile["value_score"] = (
        profile["avg_monetary"].rank(
            ascending=False
        )
        +
        profile["avg_frequency"].rank(
            ascending=False
        )
        +
        profile["avg_recency"].rank(
            ascending=True
        )
    )

    high_value_cluster = (
        profile
        .sort_values("value_score")
        .iloc[0]["cluster"]
    )

    label_map[
        high_value_cluster
    ] = "High Value"

    remaining_clusters.remove(
        high_value_cluster
    )

    # At Risk:
    # longest time since last purchase
    at_risk_cluster = (
        profile[
            profile["cluster"].isin(
                remaining_clusters
            )
        ]
        .sort_values(
            "avg_recency",
            ascending=False
        )
        .iloc[0]["cluster"]
    )

    label_map[
        at_risk_cluster
    ] = "At Risk"

    remaining_clusters.remove(
        at_risk_cluster
    )

    # Remaining cluster
    loyal_cluster = list(
        remaining_clusters
    )[0]

    label_map[
        loyal_cluster
    ] = "Loyal"

    profile["segment"] = (
        profile["cluster"]
        .map(label_map)
    )

    return profile, label_map


    # -----------------------------------------------------
    # HIGH VALUE
    # -----------------------------------------------------

    high_value_cluster = (
        profile
        .sort_values(
            "value_score"
        )
        .iloc[0][
            "cluster"
        ]
    )

    label_map[
        high_value_cluster
    ] = "High Value"

    remaining_clusters.remove(
        high_value_cluster
    )


    # -----------------------------------------------------
    # AT RISK
    # Highest recency among remaining clusters
    # -----------------------------------------------------

    at_risk_cluster = (
        profile[
            profile[
                "cluster"
            ].isin(
                remaining_clusters
            )
        ]
        .sort_values(
            "avg_recency",
            ascending=False
        )
        .iloc[0][
            "cluster"
        ]
    )

    label_map[
        at_risk_cluster
    ] = "At Risk"

    remaining_clusters.remove(
        at_risk_cluster
    )


    # -----------------------------------------------------
    # LOYAL
    # Highest frequency among remaining clusters
    # -----------------------------------------------------

    loyal_cluster = (
        profile[
            profile[
                "cluster"
            ].isin(
                remaining_clusters
            )
        ]
        .sort_values(
            "avg_frequency",
            ascending=False
        )
        .iloc[0][
            "cluster"
        ]
    )

    label_map[
        loyal_cluster
    ] = "Loyal"

    remaining_clusters.remove(
        loyal_cluster
    )


    # -----------------------------------------------------
    # POTENTIAL
    # -----------------------------------------------------

    potential_cluster = list(
        remaining_clusters
    )[0]

    label_map[
        potential_cluster
    ] = "Potential"


    profile[
        "segment"
    ] = profile[
        "cluster"
    ].map(
        label_map
    )

    return profile, label_map


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print(
        "Loading customer RFM data..."
    )

    df = load_data()

    (
        features,
        scaled_features,
        scaler
    ) = prepare_features(df)


    # -----------------------------------------------------
    # K SELECTION
    # -----------------------------------------------------

    print()
    print(
        "Evaluating K values..."
    )

    k_results = evaluate_k_values(
        scaled_features
    )

    print()
    print(
        k_results.to_string(
            index=False
        )
    )


    # K=3 achieved the highest silhouette score
    # and provides clear business segments.

    FINAL_K = 3

    print()
    print(
        f"Training final K-Means model "
        f"with K={FINAL_K}..."
    )

    model, clusters = train_model(
        scaled_features,
        k=FINAL_K
    )

    df[
        "cluster"
    ] = clusters


    # -----------------------------------------------------
    # PROFILE CLUSTERS
    # -----------------------------------------------------

    profile = create_cluster_profile(
        df
    )

    (
        profile,
        label_map
    ) = assign_segment_labels(
        profile
    )

    df[
        "segment"
    ] = df[
        "cluster"
    ].map(
        label_map
    )


    # -----------------------------------------------------
    # OUTPUT
    # -----------------------------------------------------

    print()
    print(
        "Customer Segment Profile"
    )

    display_profile = (
        profile[
            [
                "cluster",
                "segment",
                "customers",
                "avg_recency",
                "avg_frequency",
                "avg_monetary"
            ]
        ]
        .sort_values(
            "avg_monetary",
            ascending=False
        )
    )

    print(
        display_profile.to_string(
            index=False,
            formatters={
                "avg_recency":
                    "{:.2f}".format,

                "avg_frequency":
                    "{:.2f}".format,

                "avg_monetary":
                    "{:.2f}".format
            }
        )
    )


    # -----------------------------------------------------
    # SAVE FILES
    # -----------------------------------------------------

    df.to_csv(
        MODEL_DIR
        / "customer_segments.csv",
        index=False
    )

    k_results.to_csv(
        MODEL_DIR
        / "k_selection.csv",
        index=False
    )

    display_profile.to_csv(
        MODEL_DIR
        / "customer_segment_profile.csv",
        index=False
    )

    joblib.dump(
        {
            "scaler":
                scaler,

            "model":
                model,

            "label_map":
                label_map
        },

        MODEL_DIR
        / "customer_segmentation.joblib"
    )


    print()
    print(
        "Customer segmentation completed."
    )

    print(
        "Saved:"
    )

    print(
        "- models/customer_segments.csv"
    )

    print(
        "- models/k_selection.csv"
    )

    print(
        "- models/customer_segment_profile.csv"
    )

    print(
        "- models/customer_segmentation.joblib"
    )


if __name__ == "__main__":
    main()