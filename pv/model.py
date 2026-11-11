"""Seriousness prediction for FAERS reports with leakage-free preprocessing, resampling and tuning.

Everything that learns from data (vocabularies of drugs and reactions, imputation, scaling, SMOTE)
is a step of one imblearn ``Pipeline``. Cross-validation and grid search therefore refit these steps
on each training fold, and SMOTE never creates synthetic samples from validation or test reports.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, balanced_accuracy_score, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# MedDRA preferred terms that restate a seriousness criterion. If they stay in the features, the
# model can partly "read" the label. They are removed in the main analysis (see README).
OUTCOME_TERMS = {"Death", "Sudden death", "Cardiac death", "Completed suicide", "Foetal death",
                 "Hospitalisation", "Life threatening", "Disability"}

NUMERIC = ["age_years", "weight_kg", "n_drugs", "n_reactions"]
CATEGORICAL = ["sex", "reporter", "country"]


def _identity(tokens):
    return tokens


def add_text_columns(df: pd.DataFrame, drop_outcome_terms: bool) -> pd.DataFrame:
    df = df.copy()
    reactions = df["reactions"]
    if drop_outcome_terms:
        reactions = reactions.apply(lambda r: [t for t in r if t not in OUTCOME_TERMS])
        df["n_reactions"] = reactions.apply(len)
    df["reaction_list"] = reactions
    df["drug_list"] = df["suspect_drugs"]
    return df


def preprocessor(min_df: int = 5) -> ColumnTransformer:
    multi_hot = dict(analyzer=_identity, lowercase=False, binary=True, min_df=min_df)
    return ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True)),
                          ("scale", StandardScaler())]), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=10), CATEGORICAL),
        ("reactions", CountVectorizer(**multi_hot), "reaction_list"),
        ("drugs", CountVectorizer(**multi_hot), "drug_list"),
    ], sparse_threshold=0.0)


def candidate_models(seed: int = 42) -> dict[str, tuple[Pipeline, dict]]:
    """name -> (pipeline, parameter grid for GridSearchCV)."""
    rf = dict(n_jobs=-1, random_state=seed)
    return {
        "Majority class (baseline)": (
            Pipeline([("prep", preprocessor()), ("clf", DummyClassifier(strategy="prior"))]), {}),
        "Logistic regression (class-weighted)": (
            Pipeline([("prep", preprocessor()),
                      ("clf", LogisticRegression(class_weight="balanced", max_iter=3000))]),
            {"clf__C": [0.03, 0.1, 0.3, 1.0]}),
        "Random forest (class-weighted)": (
            Pipeline([("prep", preprocessor()),
                      ("clf", RandomForestClassifier(class_weight="balanced_subsample", **rf))]),
            {"clf__n_estimators": [300], "clf__max_depth": [None, 20], "clf__min_samples_leaf": [1, 3]}),
        "Random forest + SMOTE": (
            Pipeline([("prep", preprocessor()), ("smote", SMOTE(random_state=seed)),
                      ("clf", RandomForestClassifier(**rf))]),
            {"clf__n_estimators": [300], "clf__max_depth": [None, 20], "clf__min_samples_leaf": [1, 3]}),
    }


def tune(pipe: Pipeline, grid: dict, X: pd.DataFrame, y: np.ndarray, seed: int = 42) -> GridSearchCV:
    cv = StratifiedKFold(5, shuffle=True, random_state=seed)
    search = GridSearchCV(pipe, grid or {"clf__strategy": ["prior"]}, cv=cv, scoring="average_precision",
                          n_jobs=1, refit=True)
    return search.fit(X, y)


def best_threshold(y: np.ndarray, p: np.ndarray) -> float:
    """Threshold that maximises F1 (chosen on out-of-fold training predictions, never on the test set)."""
    grid = np.unique(np.round(p, 4))
    scores = [f1_score(y, p >= t, zero_division=0) for t in grid]
    return float(grid[int(np.argmax(scores))])


def metrics(y: np.ndarray, p: np.ndarray, threshold: float) -> dict:
    pred = p >= threshold
    return {"AUROC": roc_auc_score(y, p), "AUPRC": average_precision_score(y, p),
            "balanced_accuracy": balanced_accuracy_score(y, pred), "precision": precision_score(y, pred, zero_division=0),
            "recall": recall_score(y, pred), "F1": f1_score(y, pred, zero_division=0)}


def bootstrap_ci(y: np.ndarray, p: np.ndarray, threshold: float, n_boot: int = 1000, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    draws = {k: [] for k in ("AUROC", "AUPRC", "F1")}
    for _ in range(n_boot):
        idx = rng.integers(0, len(y), len(y))
        if y[idx].min() == y[idx].max():
            continue
        m = metrics(y[idx], p[idx], threshold)
        for k in draws:
            draws[k].append(m[k])
    return {k: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) for k, v in draws.items()}
