Data: 1000 unique reports (2023-01-01 to 2023-01-02), 36.3% serious. Train 750 / test 250.

**Outcome-restating reaction terms removed (main analysis)**

| Model | AUROC [95% CI] | AUPRC [95% CI] | Precision | Recall | F1 | Bal. acc. |
|---|---|---|---|---|---|---|
| Majority class (baseline) | 0.500 [0.500–0.500] | 0.364 [0.304–0.428] | 0.000 | 0.000 | 0.000 | 0.500 |
| Logistic regression (class-weighted) | 0.896 [0.850–0.932] | 0.875 [0.819–0.919] | 0.679 | 0.813 | 0.740 | 0.796 |
| Random forest (class-weighted) | 0.894 [0.840–0.940] | 0.893 [0.839–0.935] | 0.732 | 0.780 | 0.755 | 0.808 |
| Random forest + SMOTE | 0.893 [0.840–0.937] | 0.893 [0.840–0.934] | 0.755 | 0.780 | 0.768 | 0.818 |

**All reaction terms kept (ablation)**

| Model | AUROC [95% CI] | AUPRC [95% CI] | Precision | Recall | F1 | Bal. acc. |
|---|---|---|---|---|---|---|
| Logistic regression (class-weighted) | 0.918 [0.875–0.953] | 0.908 [0.858–0.944] | 0.771 | 0.813 | 0.791 | 0.837 |
| Random forest (class-weighted) | 0.893 [0.840–0.937] | 0.890 [0.836–0.933] | 0.729 | 0.769 | 0.749 | 0.803 |
| Random forest + SMOTE | 0.888 [0.835–0.933] | 0.887 [0.834–0.931] | 0.812 | 0.758 | 0.784 | 0.829 |

**Signals** (0 of 0 drug–reaction pairs with ≥ 3 reports)

| Drug | Reaction | Reports | PRR | ROR [95% CI] | χ² |
|---|---|---|---|---|---|
