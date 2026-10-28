# IndiaClaimGuard — Data Dictionary

Complete field documentation for all CSV files in the dataset.

---

## claims.csv (Primary File)

| # | Field | Type | Description | Example |
|---|-------|------|-------------|---------|
| 1 | claim_id | str | Unique claim identifier | C0000001 |
| 2 | patient_id | str | FK to patients.csv | P000001 |
| 3 | hospital_id | str | FK to hospitals.csv | H0001 |
| 4 | diagnosis_primary | str | ICD-10 code | K80.2 |
| 5 | diagnosis_description | str | Human readable diagnosis | Gallbladder calculus |
| 6 | date_of_admission | date | Hospital admission date | 2024-03-15 |
| 7 | date_of_discharge | date | Hospital discharge date (≥ admission) | 2024-03-19 |
| 8 | date_of_claim | date | Claim filing date (≥ discharge) | 2024-03-28 |
| 9 | length_of_stay_days | int | Days in hospital (1-30) | 4 |
| 10 | claim_amount_requested_inr | int | Amount claimed in INR | 125000 |
| 11 | claim_amount_approved_inr | int | Amount approved (≤ requested) | 112000 |
| 12 | policy_type | str | individual / family / group_corporate | family |
| 13 | is_cashless | bool | Cashless treatment flag | True |
| 14 | tpa | str | Third Party Administrator name | Medi Assist |
| 15 | provider_blacklist_flag | bool | Hospital on insurer watchlist | False |
| 16 | previous_fraud_on_policy | bool | Prior fraud finding on this policy | False |
| 17 | days_since_policy_start | int | Days from policy start to admission | 450 |
| 18 | num_insurers_same_event | int | Number of insurers for same event (>1 = duplicate claim signal) | 1 |
| 19 | icd_code_matches_procedure | bool | Diagnosis matches procedure (False = upcoding signal) | True |
| 20 | discharge_readmit_gap_days | int | Days between discharge and next admission (0-1 = readmission fraud) | 45 |
| 21 | pharmacy_bill_ratio | float | Pharmacy cost / total bill (>0.60 = pharmacy fraud signal) | 0.22 |
| 22 | agent_id | str | Insurance agent ID (links fraud ring members) | A001 |
| 23 | fraud_label | int | Ground truth: 0 = clean, 1 = fraud | 0 |
| 24 | fraud_type | str | Fraud category (see taxonomy below) | legitimate |
| 25 | fraud_confidence | float | Ground truth certainty (0.0-1.0) | 0.92 |
| 26 | ground_truth_source | str | How label was determined | rule_engine |

---

## patients.csv

| # | Field | Type | Description | Example |
|---|-------|------|-------------|---------|
| 1 | patient_id | str | Unique patient identifier | P000001 |
| 2 | name | str | Patient name (native script or romanized) | राहुल शर्मा |
| 3 | language | str | Primary language | hindi |
| 4 | age | int | Age in years (1-95) | 45 |
| 5 | gender | str | male / female | male |
| 6 | state | str | Indian state | Uttar Pradesh |
| 7 | policy_start_date | date | Policy inception date | 2021-06-15 |
| 8 | pre_existing_conditions | str | Comma-separated conditions or "none" | diabetes_mellitus,hypertension |
| 9 | number_of_claims_lifetime | int | Total claims ever filed | 5 |
| 10 | number_of_claims_last_12m | int | Claims in last 12 months | 2 |
| 11 | average_claim_amount | float | Mean claim amount (INR) | 85000.00 |
| 12 | identity_verified | bool | KYC verification status | True |
| 13 | kyc_type | str | KYC document used | aadhaar |

---

## hospitals.csv

| # | Field | Type | Description | Example |
|---|-------|------|-------------|---------|
| 1 | hospital_id | str | Unique hospital identifier | H0001 |
| 2 | name | str | Hospital name (regional language) | श्री शर्मा मेडिकल सेंटर |
| 3 | region | str | Geographic region | hindi_belt |
| 4 | city | str | City name | Lucknow |
| 5 | tier | int | City tier (1/2/3) | 2 |
| 6 | is_phantom | bool | Phantom hospital flag | False |
| 7 | rohini_id | str | ROHINI registration (valid: ROHINI-[1-8]XXXXX) | ROHINI-345678 |
| 8 | empanelment_date | date | Date empanelled with insurers | 2018-05-01 |
| 9 | specialization | str | Primary specialization | multi_speciality |
| 10 | total_claims_filed | int | Total claims from this hospital | 125 |
| 11 | fraud_claims_ratio | float | Fraction of fraud claims (0.0-1.0) | 0.08 |
| 12 | blacklisted | bool | On insurer blacklist | False |

---

## documents.csv

| # | Field | Type | Description | Example |
|---|-------|------|-------------|---------|
| 1 | doc_id | str | Unique document identifier | D0000001 |
| 2 | claim_id | str | FK to claims.csv | C0000001 |
| 3 | doc_type | str | Document category | discharge_summary |
| 4 | is_present | bool | Document was submitted | True |
| 5 | is_tampered | bool | Document shows signs of tampering | False |
| 6 | tamper_type | str | Type of tampering detected | none |
| 7 | upload_delay_days | int | Days from discharge to upload | 8 |

### Document Types
- `discharge_summary` — Hospital discharge summary
- `bill` — Itemized hospital bill
- `lab_report` — Laboratory test reports
- `prescription` — Doctor's prescription
- `pre_auth` — Pre-authorization letter

### Tamper Types
- `none` — No tampering detected
- `altered_amount` — Financial figures modified
- `forged_signature` — Signature does not match
- `fake_letterhead` — Hospital letterhead is fabricated

---

## Fraud Taxonomy

| Code | Type | % of Fraud Claims | Signal in Data |
|------|------|-------------------|----------------|
| 0 | legitimate | — | Clean claim |
| 1 | bill_inflation | 25% | claim_amount 1.5-3x realistic; docs tampered |
| 2 | phantom_provider | 10% | rohini_id invalid; is_phantom=True |
| 3 | identity_fraud | 1% | days_since_policy_start < 90; KYC unverified |
| 4 | staged_accident | 3% | Trauma ICD codes; no prior history |
| 5 | coordinated_ring | 10% | 3-8 claims, same hospital, 30-day window |
| 6 | duplicate_claim | 8% | num_insurers_same_event > 1 |
| 7 | unnecessary_procedure | 15% | icd_code_matches_procedure = False |
| 8 | icd_upcoding | 12% | icd_code_matches_procedure = False; amount inflated |
| 9 | fake_policy | 1% | previous_fraud_on_policy = True; very new policy |
| 10 | pre_existing_hidden | 2% | Short policy age; condition in history |
| 11 | readmission_fraud | 5% | discharge_readmit_gap_days = 0 or 1 |
| 12 | pharmacy_fraud | 8% | pharmacy_bill_ratio > 0.60 |

---

## Language Distribution

| Language | Weight | States |
|----------|--------|--------|
| Hindi | 30% | UP, MP, Rajasthan, Bihar, Jharkhand, Uttarakhand, Chhattisgarh, Delhi |
| Tamil | 15% | Tamil Nadu, Puducherry |
| Telugu | 12% | Telangana, Andhra Pradesh |
| Marathi | 12% | Maharashtra, Goa |
| Punjabi | 11% | Punjab, Haryana, Chandigarh |
| Bengali | 10% | West Bengal, Tripura |
| Gujarati | 10% | Gujarat, Dadra and Nagar Haveli |

---

## Confidence Ranges

| Fraud Type | Confidence Range | Interpretation |
|------------|-----------------|----------------|
| legitimate | 0.75–0.99 | High certainty of legitimacy |
| bill_inflation | 0.65–0.95 | Moderately high detection confidence |
| phantom_provider | 0.85–0.99 | Very high — phantom status is binary |
| identity_fraud | 0.70–0.92 | Medium-high |
| staged_accident | 0.55–0.85 | Lower — hard to prove definitively |
| coordinated_ring | 0.80–0.98 | High — network patterns are clear |
| duplicate_claim | 0.88–0.99 | Very high — cross-insurer matching |
| unnecessary_procedure | 0.50–0.80 | Lowest — requires medical expertise |
| icd_upcoding | 0.60–0.88 | Medium — coding judgment involved |
| fake_policy | 0.80–0.97 | High — document verification |
| pre_existing_hidden | 0.55–0.82 | Lower — history interpretation |
| readmission_fraud | 0.75–0.95 | High — clear temporal pattern |
| pharmacy_fraud | 0.65–0.90 | Medium-high |
