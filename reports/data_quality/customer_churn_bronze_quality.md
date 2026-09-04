# Bronze Customer Churn Data Quality Report

- Dataset: `bronze.customer_churn`
- Checked at UTC: `2026-09-03T21:48:27.608980+00:00`
- Row count: `7043`
- Column count: `25`
- Failed critical checks: `0`

## Checks

| Check | Dimension | Severity | Status | Observed | Rule |
| --- | --- | --- | --- | ---: | --- |
| required_columns_present | completeness | critical | PASS | None | All expected bronze columns must be present. |
| row_count_positive | completeness | critical | PASS | 7043 | Bronze dataset must contain at least one row. |
| customer_id_not_null | completeness | critical | PASS | 0 | customer_id must not be missing. |
| customer_id_unique | uniqueness | critical | PASS | 0 | customer_id must be unique in the customer baseline dataset. |
| gender_domain_valid | validity | critical | PASS | 0 | gender must be one of: ['Female', 'Male']. |
| senior_citizen_domain_valid | validity | critical | PASS | 0 | senior_citizen must be one of: [0, 1]. |
| partner_domain_valid | validity | critical | PASS | 0 | partner must be one of: ['No', 'Yes']. |
| dependents_domain_valid | validity | critical | PASS | 0 | dependents must be one of: ['No', 'Yes']. |
| phone_service_domain_valid | validity | critical | PASS | 0 | phone_service must be one of: ['No', 'Yes']. |
| internet_service_domain_valid | validity | critical | PASS | 0 | internet_service must be one of: ['DSL', 'Fiber optic', 'No']. |
| contract_domain_valid | validity | critical | PASS | 0 | contract must be one of: ['Month-to-month', 'One year', 'Two year']. |
| paperless_billing_domain_valid | validity | critical | PASS | 0 | paperless_billing must be one of: ['No', 'Yes']. |
| churn_domain_valid | validity | critical | PASS | 0 | churn must be one of: ['No', 'Yes']. |
| tenure_non_negative | accuracy | critical | PASS | 0 | tenure must not be negative. |
| monthly_charges_non_negative | accuracy | critical | PASS | 0 | monthly_charges must not be negative. |
| total_charges_non_negative | accuracy | critical | PASS | 0 | total_charges must not be negative when present. |
| blank_total_charges_only_for_zero_tenure | consistency | critical | PASS | 0 | Blank total_charges is allowed only when tenure is zero. |
| blank_total_charges_tracked | completeness | warning | PASS | 11 | Blank source TotalCharges values must be tracked for silver cleaning. |
| ingestion_metadata_present | timeliness | critical | PASS | 0 | source_file and ingested_at_utc must be populated. |
