"""Disproportionality analysis: is a reaction reported more often with one drug than with all others?

For every (suspect drug, reaction) pair a 2 x 2 table is built over reports:

                     reaction   other reactions
    drug                 a            b
    other drugs          c            d

    PRR = [a / (a + b)] / [c / (c + d)]            proportional reporting ratio
    ROR = (a / b) / (c / d)                         reporting odds ratio, with a 95% CI on log scale

A pair is flagged as a signal with the criteria of Evans et al. (2001): a >= 3, PRR >= 2 and
chi-square (with Yates' correction) >= 4. A signal is a hypothesis for review, not proof that the
drug causes the reaction.

If any cell is zero, 0.5 is added to all four cells before computing PRR, ROR and the CI.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

# MedDRA terms about product quality, device handling or the use process rather than a clinical
# reaction of the patient. They are excluded from signal detection by default.
NON_CLINICAL = re.compile(r"^(Product |Intercepted |Device |Drug ineffective|Off label use|Intentional product|"
                          r"Inappropriate schedule|Wrong |Incorrect |Drug dose omission|Expired product|"
                          r"No adverse event|Therapy interrupted|Treatment noncompliance|Drug administered|"
                          r"Accidental exposure|Exposure via|Circumstance or information)", re.I)


def contingency(df: pd.DataFrame, drug_col: str = "suspect_drugs") -> pd.DataFrame:
    """Counts a, b, c, d for every (drug, reaction) pair that occurs in at least one report."""
    n = len(df)
    drug_reports = df[drug_col].explode().dropna()
    n_drug = drug_reports.value_counts()                      # reports mentioning the drug
    n_reac = df["reactions"].explode().dropna().value_counts()  # reports mentioning the reaction
    long = (df[[drug_col, "reactions"]].reset_index(drop=True).explode(drug_col).explode("reactions")
            .dropna().reset_index().drop_duplicates())          # one row per (report, drug, reaction)
    pairs = long.groupby([drug_col, "reactions"]).size().rename("a").reset_index()
    pairs.columns = ["drug", "reaction", "a"]
    pairs["n_drug"] = pairs["drug"].map(n_drug)
    pairs["n_reaction"] = pairs["reaction"].map(n_reac)
    pairs["b"] = pairs["n_drug"] - pairs["a"]
    pairs["c"] = pairs["n_reaction"] - pairs["a"]
    pairs["d"] = n - pairs["a"] - pairs["b"] - pairs["c"]
    return pairs


def disproportionality(pairs: pd.DataFrame) -> pd.DataFrame:
    a0, b0, c0, d0 = (pairs[k].astype(float) for k in "abcd")
    # Haldane continuity correction: if any cell is 0, add 0.5 to all four cells for the ratios,
    # otherwise PRR and ROR are infinite (e.g. a reaction reported only with this drug).
    corr = ((pairs[list("abcd")] == 0).any(axis=1)).astype(float) * 0.5
    a, b, c, d = a0 + corr, b0 + corr, c0 + corr, d0 + corr
    out = pairs.copy()
    with np.errstate(divide="ignore", invalid="ignore"):
        out["PRR"] = (a / (a + b)) / (c / (c + d))
        out["ROR"] = (a * d) / (b * c)
        se = np.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
        out["ROR_low"] = np.exp(np.log(out["ROR"]) - 1.96 * se)
        out["ROR_high"] = np.exp(np.log(out["ROR"]) + 1.96 * se)
        a, b, c, d = a0, b0, c0, d0  # chi-square on the observed counts
        n = a + b + c + d
        out["chi2_yates"] = n * (np.abs(a * d - b * c) - n / 2).clip(lower=0) ** 2 / (
            (a + b) * (c + d) * (a + c) * (b + d))
    out["signal"] = (out["a"] >= 3) & (out["PRR"] >= 2) & (out["chi2_yates"] >= 4)
    return out


def detect_signals(df: pd.DataFrame, min_reports: int = 3, clinical_only: bool = True) -> pd.DataFrame:
    if clinical_only:
        df = df.assign(reactions=df["reactions"].apply(lambda r: [t for t in r if not NON_CLINICAL.match(t)]))
    res = disproportionality(contingency(df))
    res = res[res["a"] >= min_reports].sort_values(["signal", "ROR_low", "a"], ascending=[False, False, False])
    return res.reset_index(drop=True)
