Data: 6964 reports after removing 331 probable duplicates, received on 365 days (2023-01-01 to 2023-12-31), 59.3% serious. Train 5223 / test 1741.

**Outcome-restating reaction terms removed (main analysis)**

| Model | AUROC [95% CI] | AUPRC [95% CI] | Precision | Recall | F1 | Bal. acc. |
|---|---|---|---|---|---|---|
| Majority class (baseline) | 0.500 [0.500–0.500] | 0.593 [0.572–0.617] | 0.593 | 1.000 | 0.744 | 0.500 |
| Logistic regression (class-weighted) | 0.947 [0.936–0.955] | 0.965 [0.957–0.972] | 0.891 | 0.889 | 0.890 | 0.866 |
| Random forest (class-weighted) | 0.938 [0.926–0.947] | 0.952 [0.937–0.963] | 0.875 | 0.911 | 0.893 | 0.861 |
| Random forest + SMOTE | 0.937 [0.924–0.946] | 0.951 [0.935–0.963] | 0.892 | 0.885 | 0.888 | 0.864 |

**All reaction terms kept (ablation)**

| Model | AUROC [95% CI] | AUPRC [95% CI] | Precision | Recall | F1 | Bal. acc. |
|---|---|---|---|---|---|---|
| Logistic regression (class-weighted) | 0.956 [0.947–0.964] | 0.971 [0.962–0.977] | 0.889 | 0.913 | 0.901 | 0.873 |
| Random forest (class-weighted) | 0.940 [0.929–0.949] | 0.956 [0.943–0.966] | 0.885 | 0.901 | 0.893 | 0.865 |
| Random forest + SMOTE | 0.940 [0.928–0.949] | 0.953 [0.939–0.964] | 0.895 | 0.895 | 0.895 | 0.872 |

**Signals** (1800 of 2103 drug–reaction pairs with ≥ 3 reports)

| Drug | Reaction | Reports | PRR | ROR [95% CI] | χ² |
|---|---|---|---|---|---|
| FELODIPINE | Cardiospasm | 3 | 12183.5 | 97461.0 [1685.1–5636991.5] | 4835.3 |
| FELODIPINE | Palmoplantar keratoderma | 3 | 12183.5 | 97461.0 [1685.1–5636991.5] | 4835.3 |
| FENTANYL\FENTANYL CITRATE | Drug use disorder | 3 | 12183.5 | 97461.0 [1685.1–5636991.5] | 4835.3 |
| ISOSORBIDE DINITRATE | Cardiospasm | 3 | 12183.5 | 97461.0 [1685.1–5636991.5] | 4835.3 |
| ISOSORBIDE DINITRATE | Palmoplantar keratoderma | 3 | 12183.5 | 97461.0 [1685.1–5636991.5] | 4835.3 |
| AXICABTAGENE CILOLEUCEL | Immune effector cell-associated neurotoxicity syndrome | 4 | 4176.6 | 41757.0 [1492.5–1168305.1] | 4264.0 |
| HUMAN C1-ESTERASE INHIBITOR | Hereditary angioedema | 4 | 10440.0 | 41757.0 [1492.5–1168305.1] | 4264.0 |
| FELODIPINE | Atrial tachycardia | 3 | 4061.2 | 32482.3 [1119.5–942510.5] | 3625.7 |
| FELODIPINE | Carotid artery occlusion | 3 | 4061.2 | 32482.3 [1119.5–942510.5] | 3625.7 |
| FELODIPINE | Facial pain | 3 | 4061.2 | 32482.3 [1119.5–942510.5] | 3625.7 |
| FELODIPINE | Sleep terror | 3 | 4061.2 | 32482.3 [1119.5–942510.5] | 3625.7 |
| FELODIPINE | Tension headache | 3 | 4061.2 | 32482.3 [1119.5–942510.5] | 3625.7 |
| ISOSORBIDE DINITRATE | Atrial tachycardia | 3 | 4061.2 | 32482.3 [1119.5–942510.5] | 3625.7 |
| ISOSORBIDE DINITRATE | Carotid artery occlusion | 3 | 4061.2 | 32482.3 [1119.5–942510.5] | 3625.7 |
| ISOSORBIDE DINITRATE | Facial pain | 3 | 4061.2 | 32482.3 [1119.5–942510.5] | 3625.7 |
