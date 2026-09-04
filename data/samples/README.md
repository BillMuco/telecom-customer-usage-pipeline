# Synthetic Telco Churn Sample

`telco_customer_churn_synthetic.csv` contains 100 deterministic, fictional
customer records. It follows the 21-column IBM Telco Customer Churn schema so a
fresh clone can exercise the complete local pipeline without downloading or
redistributing the external dataset.

- Every customer identifier starts with `SYNTH-`.
- No row represents a real person or account.
- Values are generated for demonstration and must not be treated as research or
  production evidence.
- The published 7,043-customer KPIs in the main README come from the separately
  downloaded IBM sample, not this file.

Regenerate the committed sample deterministically:

```powershell
python .\scripts\generate_sample_data.py --rows 100 --seed 42 --force
```
