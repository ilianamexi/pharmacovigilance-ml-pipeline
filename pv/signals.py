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
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def contingency(df: pd.DataFrame, drug_col: str = "suspect_drugs") -> pd.DataFrame:
    """Counts a, b, c, d for every (drug, reaction) pair that occurs in at least one report."""
    n = len(df)
    drug_reports = df[drug_col].explode().dropna()
    n_drug = drug_reports.value_counts()                      # reports mentioning the drug
    n_reac = df["reactions"].explode().dropna().value_counts()  # reports mentioning the reaction
    pairs = (df[[drug_col, "reactions"]].explode(drug_col).explode("reactions").dropna()
             .drop_duplicates().value_counts().rename("a").reset_index())
    pairs.columns = ["drug", "reaction", "a"]
    pairs["n_drug"] = pairs["drug"].map(n_drug)
    pairs["n_reaction"] = pairs["reaction"].map(n_reac)
    pairs["b"] = pairs["n_drug"] - pairs["a"]
    pairs["c"] = pairs["n_reaction"] - pairs["a"]
    pairs["d"] = n - pairs["a"] - pairs["b"] - pairs["c"]
    return pairs


def disproportionality(pairs: pd.DataFrame) -> pd.DataFrame:
    a, b, c, d = (pairs[k].astype(float) for k in "abcd")
    out = pairs.copy()
    with np.errstate(divide="ignore", invalid="ignore"):
        out["PRR"] = (a / (a + b)) / (c / (c + d))
        out["ROR"] = (a * d) / (b * c)
        se = np.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
        out["ROR_low"] = np.exp(np.log(out["ROR"]) - 1.96 * se)
        out["ROR_high"] = np.exp(np.log(out["ROR"]) + 1.96 * se)
        n = a + b + c + d
        out["chi2_yates"] = n * (np.abs(a * d - b * c) - n / 2).clip(lower=0) ** 2 / (
            (a + b) * (c + d) * (a + c) * (b + d))
    out["signal"] = (out["a"] >= 3) & (out["PRR"] >= 2) & (out["chi2_yates"] >= 4)
    return out


def detect_signals(df: pd.DataFrame, min_reports: int = 3) -> pd.DataFrame:
    res = disproportionality(contingency(df))
    res = res[res["a"] >= min_reports].sort_values(["signal", "PRR", "a"], ascending=[False, False, False])
    return res.reset_index(drop=True)
