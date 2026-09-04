# Customer Churn Raw Data Profile

- Input file: `data\raw\customer_churn\telco_customer_churn.csv`
- Row count: `7043`
- Column count: `21`

## Schema Check

- Missing expected columns: `None`
- Unexpected columns: `None`

## Missing Values

| Column | Missing rows |
| --- | ---: |
| customerID | 0 |
| gender | 0 |
| SeniorCitizen | 0 |
| Partner | 0 |
| Dependents | 0 |
| tenure | 0 |
| PhoneService | 0 |
| MultipleLines | 0 |
| InternetService | 0 |
| OnlineSecurity | 0 |
| OnlineBackup | 0 |
| DeviceProtection | 0 |
| TechSupport | 0 |
| StreamingTV | 0 |
| StreamingMovies | 0 |
| Contract | 0 |
| PaperlessBilling | 0 |
| PaymentMethod | 0 |
| MonthlyCharges | 0 |
| TotalCharges | 11 |
| Churn | 0 |

## Duplicate Customer IDs

- Duplicate `customerID` values: `0`

## Numeric Checks

| Column | Invalid/blank numeric values | Negative values | Min | Max |
| --- | ---: | ---: | ---: | ---: |
| tenure | 0 | 0 | 0 | 72 |
| MonthlyCharges | 0 | 0 | 18.25 | 118.75 |
| TotalCharges | 11 | 0 | 18.8 | 8684.8 |

## Category Distributions

### gender

| Value | Rows |
| --- | ---: |
| Male | 3555 |
| Female | 3488 |

### SeniorCitizen

| Value | Rows |
| --- | ---: |
| 0 | 5901 |
| 1 | 1142 |

### Contract

| Value | Rows |
| --- | ---: |
| Month-to-month | 3875 |
| Two year | 1695 |
| One year | 1473 |

### InternetService

| Value | Rows |
| --- | ---: |
| Fiber optic | 3096 |
| DSL | 2421 |
| No | 1526 |

### PaymentMethod

| Value | Rows |
| --- | ---: |
| Electronic check | 2365 |
| Mailed check | 1612 |
| Bank transfer (automatic) | 1544 |
| Credit card (automatic) | 1522 |

### Churn

| Value | Rows |
| --- | ---: |
| No | 5174 |
| Yes | 1869 |

## Sample Rows

| customerID | tenure | MonthlyCharges | TotalCharges | Churn |
| --- | ---: | ---: | ---: | --- |
| 7590-VHVEG | 1 | 29.85 | 29.85 | No |
| 5575-GNVDE | 34 | 56.95 | 1889.5 | No |
| 3668-QPYBK | 2 | 53.85 | 108.15 | Yes |
| 7795-CFOCW | 45 | 42.3 | 1840.75 | No |
| 9237-HQITU | 2 | 70.7 | 151.65 | Yes |
