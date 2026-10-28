"""
config.py
Central configuration for IndiaClaimGuard dataset generator.
All tunable parameters live here. Never hardcode values in generators.
"""

# ─── Dataset Size ────────────────────────────────────────────────────────────
# Default = sample mode. Override with generate_dataset.py --full
N_PATIENTS = 5000
N_HOSPITALS = 200
N_CLAIMS = 5000

N_PATIENTS_FULL = 15000
N_HOSPITALS_FULL = 800
N_CLAIMS_FULL = 100000

# ─── Fraud Configuration ─────────────────────────────────────────────────────
TARGET_FRAUD_RATE = 0.18
FRAUD_RATE_TOLERANCE = 0.02

# Fraud taxonomy — IRDAI 2025 aligned (12 types + legitimate)
FRAUD_TYPES = {
    0: "legitimate",
    1: "bill_inflation",
    2: "phantom_provider",
    3: "identity_fraud",
    4: "staged_accident",
    5: "coordinated_ring",
    6: "duplicate_claim",
    7: "unnecessary_procedure",
    8: "icd_upcoding",
    9: "fake_policy",
    10: "pre_existing_hidden",
    11: "readmission_fraud",
    12: "pharmacy_fraud",
}

# Fraud type name → int code reverse lookup
FRAUD_TYPE_CODES = {v: k for k, v in FRAUD_TYPES.items()}

# Distribution of fraud among fraudulent claims (must sum to 1.0)
FRAUD_DISTRIBUTION = {
    "bill_inflation":        0.25,
    "unnecessary_procedure": 0.15,
    "icd_upcoding":          0.12,
    "phantom_provider":      0.10,
    "coordinated_ring":      0.10,
    "duplicate_claim":       0.08,
    "pharmacy_fraud":        0.08,
    "readmission_fraud":     0.05,
    "staged_accident":       0.03,
    "pre_existing_hidden":   0.02,
    "identity_fraud":        0.01,
    "fake_policy":           0.01,
}

# Confidence ranges — ground truth certainty per fraud type
# Core research contribution — never remove
CONFIDENCE_RANGES = {
    "legitimate":            (0.75, 0.99),
    "bill_inflation":        (0.65, 0.95),
    "phantom_provider":      (0.85, 0.99),
    "identity_fraud":        (0.70, 0.92),
    "staged_accident":       (0.55, 0.85),
    "coordinated_ring":      (0.80, 0.98),
    "duplicate_claim":       (0.88, 0.99),
    "unnecessary_procedure": (0.50, 0.80),
    "icd_upcoding":          (0.60, 0.88),
    "fake_policy":           (0.80, 0.97),
    "pre_existing_hidden":   (0.55, 0.82),
    "readmission_fraud":     (0.75, 0.95),
    "pharmacy_fraud":        (0.65, 0.90),
}

# ─── Reward Function ─────────────────────────────────────────────────────────
# Paper core contribution — never change without paper update
REWARD_CORRECT_CALIBRATED    =  1.0
REWARD_CORRECT_OVERCONFIDENT =  0.3
REWARD_INCORRECT_UNCERTAIN   =  0.0
REWARD_INCORRECT_OVERCONFIDENT = -0.8
REWARD_ESCALATED             = -0.3

# ─── Language Configuration ──────────────────────────────────────────────────
# Population-representative weights (must sum to 1.0)
LANGUAGE_WEIGHTS = {
    "hindi":    0.30,
    "marathi":  0.12,
    "telugu":   0.12,
    "tamil":    0.15,
    "bengali":  0.10,
    "gujarati": 0.10,
    "punjabi":  0.11,
}

# ─── ICD-10 Codes ────────────────────────────────────────────────────────────
# India's top 20 health insurance diagnosis codes
ICD10_CODES = {
    "J18.9": "Pneumonia",
    "K80.2": "Gallbladder calculus",
    "I21.9": "Acute myocardial infarction",
    "N20.0": "Kidney calculus",
    "K35.2": "Acute appendicitis",
    "O80":   "Normal delivery",
    "S72.0": "Femur fracture",
    "I63.9": "Cerebral infarction",
    "K92.1": "Gastrointestinal bleed",
    "J44.1": "COPD exacerbation",
    "N18.9": "Chronic kidney disease",
    "E11.9": "Type 2 diabetes complications",
    "C34.9": "Lung cancer",
    "G35":   "Multiple sclerosis",
    "M16.9": "Hip replacement",
    "H26.9": "Cataract",
    "K57.3": "Diverticular disease",
    "I10":   "Essential hypertension",
    "Z51.1": "Chemotherapy session",
    "S06.3": "Traumatic brain injury",
}

# Amount ranges by diagnosis (INR)
# Bill inflation fraud multiplies by 1.5-3.0x
ICD10_AMOUNTS = {
    "J18.9": (25000, 80000),
    "K80.2": (80000, 200000),
    "I21.9": (150000, 500000),
    "N20.0": (40000, 120000),
    "K35.2": (60000, 150000),
    "O80":   (30000, 80000),
    "S72.0": (150000, 400000),
    "I63.9": (100000, 350000),
    "K92.1": (30000, 90000),
    "J44.1": (20000, 60000),
    "N18.9": (50000, 150000),
    "E11.9": (15000, 45000),
    "C34.9": (200000, 800000),
    "G35":   (80000, 250000),
    "M16.9": (180000, 450000),
    "H26.9": (30000, 80000),
    "K57.3": (40000, 100000),
    "I10":   (15000, 40000),
    "Z51.1": (100000, 400000),
    "S06.3": (120000, 600000),
}

# ─── TPA & Insurance ─────────────────────────────────────────────────────────
TPA_LIST = [
    "Medi Assist",
    "Paramount Health Services",
    "Raksha TPA",
    "Vidal Health",
    "FHPL (Family Health Plan)",
    "Heritage Health",
    "MD India",
    "Medsave Health",
    "Anytime Health",
    "Good Health TPA",
]

POLICY_TYPES = ["individual", "family", "group_corporate"]
POLICY_TYPE_WEIGHTS = [0.45, 0.35, 0.20]

KYC_TYPES = ["aadhaar", "pan_card", "voter_id", "passport"]
KYC_TYPE_WEIGHTS = [0.60, 0.25, 0.10, 0.05]

# ─── Hospital Configuration ──────────────────────────────────────────────────
CITY_TIER_WEIGHTS = [0.30, 0.40, 0.30]  # Tier1, Tier2, Tier3
PHANTOM_HOSPITAL_RATE = 0.08
CASHLESS_RATE = 0.65

# ─── Patient Configuration ───────────────────────────────────────────────────
AGE_MEAN = 45
AGE_STD = 18
AGE_MIN = 1
AGE_MAX = 95

# Pre-existing conditions by age bracket
PRE_EXISTING_CONDITIONS = [
    "diabetes_mellitus",
    "hypertension",
    "coronary_artery_disease",
    "asthma",
    "thyroid_disorder",
    "chronic_kidney_disease",
    "arthritis",
    "obesity",
]

# ─── Date Configuration ──────────────────────────────────────────────────────
# Claims generated within this date window
CLAIM_START_DATE = "2023-01-01"
CLAIM_END_DATE = "2025-12-31"

# Length of stay ranges (days)
LOS_RANGE = (1, 30)

# Processing time (days after discharge to claim filing)
PROCESSING_DAYS_LEGIT = (7, 21)
PROCESSING_DAYS_FRAUD = (2, 5)

# ─── Ground Truth Sources ────────────────────────────────────────────────────
GROUND_TRUTH_SOURCES = ["rule_engine", "expert_review", "pattern_detection"]

# ─── Specializations ─────────────────────────────────────────────────────────
HOSPITAL_SPECIALIZATIONS = [
    "multi_speciality",
    "cardiac",
    "oncology",
    "orthopaedic",
    "maternity",
    "general_medicine",
    "nephrology",
    "neurology",
    "gastroenterology",
    "pulmonology",
]

# Tier1 hospitals more likely to have super-specialities
SPECIALIZATION_WEIGHTS_TIER1 = [0.25, 0.15, 0.12, 0.10, 0.08, 0.05, 0.08, 0.07, 0.05, 0.05]
SPECIALIZATION_WEIGHTS_TIER2 = [0.35, 0.08, 0.05, 0.10, 0.12, 0.15, 0.05, 0.03, 0.04, 0.03]
SPECIALIZATION_WEIGHTS_TIER3 = [0.15, 0.03, 0.02, 0.05, 0.15, 0.40, 0.03, 0.02, 0.05, 0.10]

# ─── Random Seed ──────────────────────────────────────────────────────────────
RANDOM_SEED = 42
