# IndiaClaimGuard
## Synthetic Indian Health Insurance Fraud Dataset (IRDAI-aligned)

**100,000 claims · 7 Indian languages · 12 fraud types · Confidence labels · Reasoning traces**

---

## Why This Dataset Exists

No public dataset covers Indian health insurance fraud with:
- IRDAI 2025 fraud taxonomy alignment
- Regional Indian language diversity (Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Punjabi)
- Ground-truth confidence labels per claim (how certain is the label?)
- Chain-of-thought reasoning traces for each adjudication decision

This fills that gap. Built as part of the CalibFraud research project.

---

## The Core Innovation: Confidence Labels

Every claim has a `fraud_confidence` column (0.0–1.0) representing
how certain the ground truth label is. This enables research into
calibrated models that know when they don't know.

Standard fraud detection research optimizes for accuracy.
CalibFraud optimizes for calibration — a model that is wrong and
uncertain is far less dangerous than one that is wrong and certain.
This is the property that matters in production adjudication.

---

## Files

| File | Rows | Description |
|------|------|-------------|
| claims.csv | 100,000 | One row per claim (primary file) |
| patients.csv | ~15,000 | Claimant profiles |
| hospitals.csv | ~800 | Provider details including phantom flags |
| documents.csv | ~400,000 | Document presence and tampering per claim |
| generate_dataset.py | — | Full reproducible generation code |
| baseline_eda.ipynb | — | EDA + XGBoost baseline to beat |

---

## Fraud Taxonomy (IRDAI-aligned)

| Code | Type | % of Fraud | Notes |
|------|------|-----------|-------|
| 0 | legitimate | 82% | Clean claims |
| 1 | bill_inflation | 25% | Inflated charges, tampered bills |
| 2 | phantom_provider | 10% | Hospital never existed |
| 3 | identity_fraud | 1% | Policy on someone else's name |
| 4 | staged_accident | 3% | Fabricated incident |
| 5 | coordinated_ring | 10% | Multiple claimants, same provider |
| 6 | duplicate_claim | 8% | Same event, multiple insurers |
| 7 | unnecessary_procedure | 15% | Real admission, procedures never done |
| 8 | icd_upcoding | 12% | Expensive diagnosis code substituted |
| 9 | fake_policy | 1% | Policy document forged |
| 10 | pre_existing_hidden | 2% | Condition concealed at policy start |
| 11 | readmission_fraud | 5% | Discharged and readmitted same day |
| 12 | pharmacy_fraud | 8% | Medicines billed, never dispensed |

---

## Key Schema Fields

See DATA_DICTIONARY.md for full field documentation.

Unique fields not in other fraud datasets:
- `fraud_confidence` — ground truth certainty (0.0-1.0)
- `icd_code_matches_procedure` — upcoding detection signal
- `discharge_readmit_gap_days` — readmission fraud signal
- `pharmacy_bill_ratio` — pharmacy fraud signal
- `provider_blacklist_flag` — insurer watchlist status
- `agent_id` — links fraud ring members

---

## Domain Expert Validation

Dataset patterns were validated with an insurance agent with 20+ years
of experience in the Indian health insurance market. Fraud signals, claim
amounts, document patterns, and processing timelines reflect real-world
observations from the Indian insurance ecosystem.

---

## Generation Methodology

1. Python generator produces base synthetic data with realistic
   Indian patient names, regional hospitals, ICD-10 codes, and fraud patterns
2. Adaption's Adaptive Data platform adapts and enriches the dataset,
   adding reasoning traces and quality improvements (82% quality gain)
3. Blueprint specification layer enforces schema constraints throughout
4. Manual validation against IRDAI 2023-24 annual report statistics

---

## Baseline Results

Run `baseline_eda.py` to reproduce.

| Model | AUC-ROC | ECE | Notes |
|-------|---------|-----|-------|
| XGBoost (tabular) | 0.9526 | 0.0105 | Feature-based baseline |
| ClaimCourt (LLaMA 3.3 70B SFT) | 100% win rate vs base | — | Reasoning trace model, 748 steps, 15K rows |

ClaimCourt was trained via Adaption AutoScientist on 15,000 adapted reasoning traces.
Training loss: 0.763 → 0.137. Win rate against base LLaMA 3.3 70B: **100%**.

---

## Citation

If you use this dataset, please cite:

```bibtex
@dataset{aslaliya2026indiaclaimguard,
  title={IndiaClaimGuard: Synthetic Indian Health Insurance Fraud Dataset},
  author={Aslaliya, Aniket},
  year={2026},
  url={https://www.kaggle.com/datasets/aniketaslaliya30/adaption-india-health-claim-fraud-audit},
  note={IRDAI-aligned, 100K claims, 7 Indian languages, 12 fraud types}
}
```

---

## License
CC BY 4.0 — Free for research and commercial use with attribution.

---

## Related Paper
CalibFraud: A Calibrated Reinforcement Learning Benchmark for
Sequential Insurance Claim Adjudication in India
[arXiv link — add after submission]