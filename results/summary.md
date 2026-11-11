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

**Signals**: 1800 of 2103 drug–reaction pairs with ≥ 3 reports meet the Evans criteria. The 15 with the most reports (≥ 10):

| Drug | Reaction | Reports | PRR | ROR [95% CI] | χ² |
|---|---|---|---|---|---|
| DUPILUMAB | Injection site pain | 47 | 10.4 | 11.7 [8.0–17.1] | 244.3 |
| DUPILUMAB | Pruritus | 43 | 7.1 | 7.8 [5.4–11.4] | 156.2 |
| TROFINETIDE | Diarrhoea | 42 | 25.2 | 110.0 [57.1–212.0] | 826.4 |
| ACETAMINOPHEN\OXYCODONE HYDROCHLORIDE | Dependence | 41 | 405.0 | 2245.2 [920.3–5477.9] | 4135.2 |
| ACETAMINOPHEN\HYDROCODONE BITARTRATE | Dependence | 31 | 263.3 | 2973.4 [851.0–10389.0] | 3447.5 |
| DUPILUMAB | Eczema | 31 | 103.1 | 111.8 [43.2–289.2] | 422.6 |
| PIMAVANSERIN TARTRATE | Hallucination | 28 | 73.0 | 92.6 [50.5–169.7] | 804.0 |
| DUPILUMAB | Dry skin | 28 | 19.4 | 20.8 [11.9–36.3] | 218.3 |
| SODIUM CITRATE | Paraesthesia | 27 | 162.0 | 705.3 [298.5–1666.5] | 2307.5 |
| ADALIMUMAB | Pain | 26 | 3.1 | 3.3 [2.2–5.1] | 31.5 |
| RISANKIZUMAB-RZAA | Psoriasis | 24 | 16.2 | 18.3 [11.0–30.5] | 226.0 |
| TROFINETIDE | Underdose | 23 | 117.7 | 204.3 [104.8–398.2] | 1335.0 |
| TROFINETIDE | Vomiting | 23 | 22.6 | 38.7 [22.0–68.2] | 394.6 |
| DUPILUMAB | Rash | 22 | 3.1 | 3.3 [2.0–5.2] | 25.4 |
| DUPILUMAB | Arthralgia | 21 | 2.2 | 2.3 [1.4–3.6] | 11.3 |
