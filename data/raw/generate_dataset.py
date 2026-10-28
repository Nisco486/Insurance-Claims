"""
generate_dataset.py
Main entry point for IndiaClaimGuard dataset generation.

Usage:
    python generate_dataset.py          # Sample mode (500 rows, fast test)
    python generate_dataset.py --full   # Full mode (100K rows, 3-5 min)
"""

import os
import sys
import time
import argparse

import numpy as np
import pandas as pd

from config import (
    N_PATIENTS, N_HOSPITALS, N_CLAIMS,
    N_PATIENTS_FULL, N_HOSPITALS_FULL, N_CLAIMS_FULL,
    RANDOM_SEED, TARGET_FRAUD_RATE,
)
from generators import (
    generate_patients,
    generate_hospitals,
    generate_claims,
    inject_fraud_signals,
    generate_documents,
)


def update_patient_stats(patients_df: pd.DataFrame, claims_df: pd.DataFrame) -> pd.DataFrame:
    """Update patient aggregate statistics from generated claims."""
    df = patients_df.copy()

    # Aggregate claim stats per patient
    claim_stats = claims_df.groupby("patient_id").agg(
        total_claims=("claim_id", "count"),
        avg_amount=("claim_amount_requested_inr", "mean"),
    ).reset_index()

    # Count claims in last 12 months (approximate: last 365 days of claim window)
    claims_df_copy = claims_df.copy()
    claims_df_copy["date_of_claim_dt"] = pd.to_datetime(claims_df_copy["date_of_claim"])
    cutoff = claims_df_copy["date_of_claim_dt"].max() - pd.Timedelta(days=365)
    recent = claims_df_copy[claims_df_copy["date_of_claim_dt"] >= cutoff]
    recent_stats = recent.groupby("patient_id").agg(
        recent_claims=("claim_id", "count"),
    ).reset_index()

    # Merge
    df = df.merge(claim_stats, on="patient_id", how="left")
    df = df.merge(recent_stats, on="patient_id", how="left")

    df["number_of_claims_lifetime"] = df["total_claims"].fillna(0).astype(int)
    df["number_of_claims_last_12m"] = df["recent_claims"].fillna(0).astype(int)
    df["average_claim_amount"] = df["avg_amount"].fillna(0).round(2)

    df = df.drop(columns=["total_claims", "avg_amount", "recent_claims"], errors="ignore")
    return df


def print_summary(claims_df: pd.DataFrame, patients_df: pd.DataFrame,
                   hospitals_df: pd.DataFrame, documents_df: pd.DataFrame):
    """Print generation summary statistics."""
    n = len(claims_df)
    fraud_rate = claims_df["fraud_label"].mean()
    fraud_types = claims_df[claims_df["fraud_label"] == 1]["fraud_type"].nunique()
    languages = patients_df["language"].nunique()
    phantom_rate = hospitals_df["is_phantom"].mean()

    print("\n" + "=" * 60)
    print("IndiaClaimGuard -- Generation Summary")
    print("=" * 60)
    print(f"  Claims:          {n:,}")
    print(f"  Patients:        {len(patients_df):,}")
    print(f"  Hospitals:       {len(hospitals_df):,}")
    print(f"  Documents:       {len(documents_df):,}")
    print(f"  Fraud rate:      {fraud_rate:.1%} (target: {TARGET_FRAUD_RATE:.0%})")
    print(f"  Fraud types:     {fraud_types} / 12")
    print(f"  Languages:       {languages} / 7")
    print(f"  Phantom hosp:    {phantom_rate:.1%}")
    print()

    # Fraud type breakdown
    fraud_dist = claims_df[claims_df["fraud_label"] == 1]["fraud_type"].value_counts()
    print("  Fraud Distribution:")
    for ft, count in fraud_dist.items():
        pct = count / claims_df["fraud_label"].sum() * 100
        print(f"    {ft:25s} {count:6,} ({pct:5.1f}%)")

    # Language breakdown
    print()
    print("  Language Distribution:")
    lang_dist = patients_df["language"].value_counts()
    for lang, count in lang_dist.items():
        pct = count / len(patients_df) * 100
        print(f"    {lang:15s} {count:6,} ({pct:5.1f}%)")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Generate IndiaClaimGuard dataset")
    parser.add_argument(
        "--full", action="store_true",
        help="Full mode: 100K claims (3-5 min). Default: 500 sample rows.",
    )
    args = parser.parse_args()

    # Set sizes
    if args.full:
        n_patients = N_PATIENTS_FULL
        n_hospitals = N_HOSPITALS_FULL
        n_claims = N_CLAIMS_FULL
        print("Mode: FULL (100K claims)")
    else:
        n_patients = N_PATIENTS
        n_hospitals = N_HOSPITALS
        n_claims = N_CLAIMS
        print("Mode: SAMPLE (500 claims)")

    # RNG
    rng = np.random.default_rng(RANDOM_SEED)

    # Create output dir
    os.makedirs("data", exist_ok=True)

    # Step 1: Generate patients
    print("\n[1/5] Generating patients...")
    t0 = time.time()
    patients_df = generate_patients(n_patients, rng)
    print(f"  -> {len(patients_df):,} patients ({time.time()-t0:.1f}s)")

    # Step 2: Generate hospitals
    print("[2/5] Generating hospitals...")
    t0 = time.time()
    hospitals_df = generate_hospitals(n_hospitals, rng)
    print(f"  -> {len(hospitals_df):,} hospitals ({time.time()-t0:.1f}s)")

    # Step 3: Generate claims
    print("[3/5] Generating claims...")
    t0 = time.time()
    claims_df = generate_claims(n_claims, patients_df, hospitals_df, rng)
    print(f"  -> {len(claims_df):,} claims ({time.time()-t0:.1f}s)")

    # Step 4: Inject fraud signals
    print("[4/5] Injecting fraud signals...")
    t0 = time.time()
    claims_df, hospitals_df = inject_fraud_signals(claims_df, hospitals_df, rng)
    print(f"  -> fraud signals injected ({time.time()-t0:.1f}s)")

    # Step 5: Generate documents
    print("[5/5] Generating documents...")
    t0 = time.time()
    documents_df = generate_documents(claims_df, rng)
    print(f"  -> {len(documents_df):,} documents ({time.time()-t0:.1f}s)")

    # Update patient aggregate stats
    patients_df = update_patient_stats(patients_df, claims_df)

    # Save
    claims_df.to_csv("data/claims.csv", index=False)
    patients_df.to_csv("data/patients.csv", index=False)
    hospitals_df.to_csv("data/hospitals.csv", index=False)
    documents_df.to_csv("data/documents.csv", index=False)
    print("\nSaved to data/")

    # Summary
    print_summary(claims_df, patients_df, hospitals_df, documents_df)

    return claims_df


if __name__ == "__main__":
    main()
