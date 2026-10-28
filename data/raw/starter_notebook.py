# %% [markdown]
# # IndiaClaimGuard — Starter Notebook
# **Synthetic Indian Health Insurance Fraud Dataset (IRDAI-aligned, 100K)**
#
# This notebook gives you a working baseline in under 5 minutes:
# 1. Load and explore the dataset
# 2. Visualise fraud distribution
# 3. Train an XGBoost fraud detector
# 4. Evaluate with AUC-ROC and calibration (ECE)
#
# Dataset: https://www.kaggle.com/datasets/aniketaslaliya30/adaption-india-health-claim-fraud-audit

# %% [markdown]
# ## 1. Load Data

# %%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import roc_auc_score, classification_report
import warnings
warnings.filterwarnings("ignore")

claims    = pd.read_csv("/kaggle/input/adaption-india-health-claim-fraud-audit/claims.csv")
patients  = pd.read_csv("/kaggle/input/adaption-india-health-claim-fraud-audit/patients.csv")
hospitals = pd.read_csv("/kaggle/input/adaption-india-health-claim-fraud-audit/hospitals.csv")

print(f"Claims:    {len(claims):,} rows x {claims.shape[1]} columns")
print(f"Patients:  {len(patients):,} rows")
print(f"Hospitals: {len(hospitals):,} rows")
print(f"\nFraud rate: {claims['fraud_label'].mean():.1%}  (IRDAI target: 18%)")
claims.head(3)

# %% [markdown]
# ## 2. Fraud Distribution

# %%
fraud_only = claims[claims["fraud_label"] == 1]
dist = fraud_only["fraud_type"].value_counts()

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Fraud type bar chart
axes[0].barh(dist.index, dist.values, color="#4C72B0")
axes[0].set_xlabel("Number of Claims")
axes[0].set_title("Fraud Type Distribution (18% of dataset)")
axes[0].invert_yaxis()

# Confidence score by fraud type
conf_means = claims.groupby("fraud_type")["fraud_confidence"].mean().sort_values()
axes[1].barh(conf_means.index, conf_means.values, color="#DD8452")
axes[1].set_xlabel("Mean Confidence Score")
axes[1].set_title("Ground Truth Certainty by Fraud Type")
axes[1].axvline(0.75, color="red", linestyle="--", alpha=0.6, label="0.75 threshold")
axes[1].legend()

plt.tight_layout()
plt.savefig("fraud_distribution.png", dpi=150, bbox_inches="tight")
plt.show()

# %% [markdown]
# ## 3. Feature Engineering

# %%
df = claims.merge(
    patients[["patient_id", "age", "language", "identity_verified",
              "number_of_claims_lifetime", "number_of_claims_last_12m"]],
    on="patient_id", how="left"
).merge(
    hospitals[["hospital_id", "tier", "is_phantom", "blacklisted",
               "fraud_claims_ratio"]],
    on="hospital_id", how="left"
)

FEATURES = [
    "claim_amount_requested_inr",
    "claim_amount_approved_inr",
    "length_of_stay_days",
    "days_since_policy_start",
    "num_insurers_same_event",
    "discharge_readmit_gap_days",
    "pharmacy_bill_ratio",
    "provider_blacklist_flag",
    "previous_fraud_on_policy",
    "icd_code_matches_procedure",
    "is_cashless",
    "age",
    "identity_verified",
    "number_of_claims_lifetime",
    "number_of_claims_last_12m",
    "tier",
    "is_phantom",
    "blacklisted",
    "fraud_claims_ratio",
]

for col in ["provider_blacklist_flag", "previous_fraud_on_policy",
            "icd_code_matches_procedure", "is_cashless",
            "identity_verified", "is_phantom", "blacklisted"]:
    df[col] = df[col].astype(int)

X = df[FEATURES].fillna(0)
y = df["fraud_label"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Train: {len(X_train):,}  |  Test: {len(X_test):,}")
print(f"Train fraud rate: {y_train.mean():.1%}  |  Test fraud rate: {y_test.mean():.1%}")

# %% [markdown]
# ## 4. XGBoost Baseline

# %%
try:
    from xgboost import XGBClassifier
    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=(y_train == 0).sum() / (y_train == 1).sum(),
        random_state=42,
        eval_metric="auc",
        verbosity=0,
    )
except ImportError:
    from sklearn.ensemble import GradientBoostingClassifier
    model = GradientBoostingClassifier(n_estimators=200, random_state=42)

model.fit(X_train, y_train)
probs = model.predict_proba(X_test)[:, 1]
preds = (probs >= 0.5).astype(int)

auc = roc_auc_score(y_test, probs)
print(f"\nXGBoost AUC-ROC: {auc:.4f}")
print("\nClassification Report:")
print(classification_report(y_test, preds, target_names=["Legit", "Fraud"]))

# %% [markdown]
# ## 5. Calibration Error (ECE) — The Paper's Key Metric

# %%
def expected_calibration_error(y_true, y_prob, n_bins=10):
    """ECE measures how well predicted probabilities match actual outcomes."""
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (y_prob >= bins[i]) & (y_prob < bins[i + 1])
        if mask.sum() == 0:
            continue
        acc = y_true[mask].mean()
        conf = y_prob[mask].mean()
        ece += mask.sum() * abs(acc - conf)
    return ece / len(y_true)

ece = expected_calibration_error(y_test.values, probs)
print(f"Expected Calibration Error (ECE): {ece:.4f}")
print(f"(Lower is better. 0.0 = perfect calibration. ClaimCourt targets < 0.05)")

# %% [markdown]
# ## 6. Feature Importance

# %%
if hasattr(model, "feature_importances_"):
    importance = pd.Series(model.feature_importances_, index=FEATURES).sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(8, 7))
    importance.plot(kind="barh", ax=ax, color="#4C72B0")
    ax.set_title("XGBoost Feature Importance")
    ax.set_xlabel("Importance Score")
    plt.tight_layout()
    plt.savefig("feature_importance.png", dpi=150, bbox_inches="tight")
    plt.show()

# %% [markdown]
# ## Summary
#
# | Metric | Score |
# |--------|-------|
# | AUC-ROC (XGBoost baseline) | see above |
# | ECE (calibration error) | see above |
# | Fraud rate | 18% (IRDAI-aligned) |
# | Fraud types | 12 |
# | Languages | 7 Indian |
#
# **Beat this baseline with ClaimCourt** — the calibrated RL agent described
# in the companion paper *CalibFraud: Calibrated Reinforcement Learning for
# Sequential Insurance Claim Adjudication in India*.
#
# Citation:
# ```bibtex
# @dataset{aslaliya2026indiaclaimguard,
#   title={IndiaClaimGuard: Synthetic Indian Health Insurance Fraud Dataset},
#   author={Aslaliya, Aniket},
#   year={2026},
#   url={https://www.kaggle.com/datasets/aniketaslaliya30/adaption-india-health-claim-fraud-audit}
# }
# ```
