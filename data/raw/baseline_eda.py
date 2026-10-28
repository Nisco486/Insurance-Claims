"""
notebooks/baseline_eda.py
Baseline EDA + XGBoost fraud detection model.
Run this to reproduce baseline results for the CalibFraud paper.

Usage:
    python notebooks/baseline_eda.py                     # uses data/claims.csv
    python notebooks/baseline_eda.py --adapted            # uses data/claims_adapted.csv

Outputs:
    - Console: statistics, model metrics, calibration analysis
    - data/baseline_results.json: metrics for paper Table 1
    - data/calibration_curve.png: reliability diagram (paper Figure 2)
"""

import os
import sys
import json
import argparse

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)
from sklearn.calibration import calibration_curve
from sklearn.preprocessing import LabelEncoder

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import FRAUD_TYPES, FRAUD_DISTRIBUTION


def load_and_prepare(claims_path: str, patients_path: str, hospitals_path: str):
    """Load CSVs and prepare features for modeling."""
    print(f"Loading data from {claims_path}...")
    claims = pd.read_csv(claims_path)
    patients = pd.read_csv(patients_path)
    hospitals = pd.read_csv(hospitals_path)

    # Merge
    df = claims.merge(patients, on="patient_id", how="left", suffixes=("", "_patient"))
    df = df.merge(hospitals, on="hospital_id", how="left", suffixes=("", "_hospital"))

    return df


def eda_summary(df: pd.DataFrame):
    """Print comprehensive EDA statistics."""
    print("\n" + "=" * 60)
    print("EXPLORATORY DATA ANALYSIS")
    print("=" * 60)

    # Basic stats
    print(f"\nDataset shape: {df.shape}")
    print(f"Fraud rate: {df['fraud_label'].mean():.1%}")
    print(f"Unique patients: {df['patient_id'].nunique()}")
    print(f"Unique hospitals: {df['hospital_id'].nunique()}")

    # Fraud type distribution
    print("\n--- Fraud Type Distribution ---")
    fraud_dist = df[df["fraud_label"] == 1]["fraud_type"].value_counts()
    for ft, count in fraud_dist.items():
        pct = count / df["fraud_label"].sum() * 100
        print(f"  {ft:25s} {count:6,} ({pct:5.1f}%)")

    # Language distribution
    print("\n--- Language Distribution ---")
    lang_dist = df["language"].value_counts()
    for lang, count in lang_dist.items():
        pct = count / len(df) * 100
        print(f"  {lang:15s} {count:6,} ({pct:5.1f}%)")

    # Amount statistics
    print("\n--- Claim Amount Statistics (INR) ---")
    print(f"  Mean requested:  {df['claim_amount_requested_inr'].mean():>12,.0f}")
    print(f"  Median requested:{df['claim_amount_requested_inr'].median():>12,.0f}")
    print(f"  Mean approved:   {df['claim_amount_approved_inr'].mean():>12,.0f}")
    print(f"  Max requested:   {df['claim_amount_requested_inr'].max():>12,.0f}")

    # Fraud vs legitimate amount comparison
    legit_amt = df[df["fraud_label"] == 0]["claim_amount_requested_inr"].mean()
    fraud_amt = df[df["fraud_label"] == 1]["claim_amount_requested_inr"].mean()
    print(f"\n  Legit mean:      {legit_amt:>12,.0f}")
    print(f"  Fraud mean:      {fraud_amt:>12,.0f}")
    print(f"  Fraud/Legit ratio: {fraud_amt/legit_amt:.2f}x")

    # Confidence statistics
    print("\n--- Confidence Score Statistics ---")
    print(f"  Overall mean:    {df['fraud_confidence'].mean():.4f}")
    print(f"  Legit mean:      {df[df['fraud_label']==0]['fraud_confidence'].mean():.4f}")
    print(f"  Fraud mean:      {df[df['fraud_label']==1]['fraud_confidence'].mean():.4f}")

    # Hospital phantom rate
    phantom_claims = df[df.get("is_phantom", pd.Series([False]*len(df))) == True]
    if "is_phantom" in df.columns:
        print(f"\n--- Phantom Hospital Claims ---")
        print(f"  Claims at phantom hospitals: {len(phantom_claims)}")

    print("=" * 60)


def prepare_features(df: pd.DataFrame):
    """Prepare feature matrix for XGBoost."""
    # Select numeric and boolean features
    feature_cols = [
        "claim_amount_requested_inr",
        "claim_amount_approved_inr",
        "length_of_stay_days",
        "days_since_policy_start",
        "num_insurers_same_event",
        "discharge_readmit_gap_days",
        "pharmacy_bill_ratio",
        "age",
    ]

    # Boolean features -> int
    bool_cols = [
        "is_cashless",
        "provider_blacklist_flag",
        "previous_fraud_on_policy",
        "icd_code_matches_procedure",
        "identity_verified",
    ]

    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(int)
            feature_cols.append(col)

    # Encode categoricals
    cat_cols = ["policy_type", "language", "kyc_type"]
    le_dict = {}
    for col in cat_cols:
        if col in df.columns:
            le = LabelEncoder()
            df[f"{col}_encoded"] = le.fit_transform(df[col].astype(str))
            feature_cols.append(f"{col}_encoded")
            le_dict[col] = le

    # Tier
    if "tier" in df.columns:
        feature_cols.append("tier")

    # Filter to available columns
    available = [c for c in feature_cols if c in df.columns]
    X = df[available].fillna(0)
    y = df["fraud_label"].values

    return X, y, available


def compute_ece(y_true, y_prob, n_bins=10):
    """Compute Expected Calibration Error."""
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    total = len(y_true)
    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        
        # Determine elements in current bin
        if i == n_bins - 1:
            in_bin = (y_prob >= bin_lower) & (y_prob <= bin_upper)
        else:
            in_bin = (y_prob >= bin_lower) & (y_prob < bin_upper)
            
        prop_in_bin = np.mean(in_bin)
        
        if prop_in_bin > 0:
            accuracy_in_bin = np.mean(y_true[in_bin])
            avg_confidence_in_bin = np.mean(y_prob[in_bin])
            ece += prop_in_bin * np.abs(avg_confidence_in_bin - accuracy_in_bin)
            
    return ece



def train_and_evaluate(X, y, feature_names):
    """Train XGBoost baseline and evaluate."""
    print("\n" + "=" * 60)
    print("MODEL TRAINING & EVALUATION")
    print("=" * 60)

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\nTrain: {len(X_train):,} | Test: {len(X_test):,}")
    print(f"Train fraud rate: {y_train.mean():.1%}")
    print(f"Test fraud rate:  {y_test.mean():.1%}")

    # Train GradientBoosting (similar to XGBoost, scikit-learn native)
    print("\nTraining GradientBoosting classifier...")
    model = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
    )
    model.fit(X_train, y_train)

    # Predict
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    # Metrics
    auc = roc_auc_score(y_test, y_prob)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    ece = compute_ece(y_test, y_prob)

    print(f"\n--- Results ---")
    print(f"  AUC-ROC:   {auc:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1-Score:  {f1:.4f}")
    print(f"  ECE:       {ece:.4f}")

    # Classification report
    print(f"\n--- Classification Report ---")
    print(classification_report(y_test, y_pred, target_names=["legitimate", "fraud"]))

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    print(f"--- Confusion Matrix ---")
    print(f"  TN={cm[0,0]:,}  FP={cm[0,1]:,}")
    print(f"  FN={cm[1,0]:,}  TP={cm[1,1]:,}")

    # Feature importance
    print(f"\n--- Top 10 Feature Importances ---")
    importances = sorted(
        zip(feature_names, model.feature_importances_),
        key=lambda x: x[1],
        reverse=True,
    )
    for feat, imp in importances[:10]:
        print(f"  {feat:35s} {imp:.4f}")

    # Calibration curve data
    fraction_pos, mean_pred = calibration_curve(y_test, y_prob, n_bins=10)

    print("=" * 60)

    return {
        "auc_roc": round(auc, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "ece": round(ece, 4),
        "confusion_matrix": cm.tolist(),
        "feature_importances": {f: round(float(i), 4) for f, i in importances},
        "calibration_curve": {
            "fraction_of_positives": fraction_pos.tolist(),
            "mean_predicted_value": mean_pred.tolist(),
        },
    }


def save_results(results: dict, output_path: str = "data/baseline_results.json"):
    """Save results as JSON for paper Table 1."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Baseline EDA + XGBoost for IndiaClaimGuard")
    parser.add_argument(
        "--adapted", action="store_true",
        help="Use adapted dataset (data/claims_adapted.csv) instead of raw",
    )
    args = parser.parse_args()

    # Paths
    if args.adapted and os.path.exists("data/claims_adapted.csv"):
        claims_path = "data/claims_adapted.csv"
    else:
        claims_path = "data/claims.csv"
    patients_path = "data/patients.csv"
    hospitals_path = "data/hospitals.csv"

    # Check files exist
    for p in [claims_path, patients_path, hospitals_path]:
        if not os.path.exists(p):
            print(f"Error: {p} not found. Run generate_dataset.py first.")
            sys.exit(1)

    # Load
    df = load_and_prepare(claims_path, patients_path, hospitals_path)

    # EDA
    eda_summary(df)

    # Train & evaluate
    X, y, feature_names = prepare_features(df)
    results = train_and_evaluate(X, y, feature_names)

    # Save
    save_results(results)

    print("\nDone. Use these numbers for paper Table 1 (Section 7: Results).")
    print("For calibration curve plot, see data/baseline_results.json -> calibration_curve")


if __name__ == "__main__":
    main()
