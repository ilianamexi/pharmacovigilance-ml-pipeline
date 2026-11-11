"""Download and parse openFDA FAERS adverse-event reports.

Two input formats are supported:
- JSON lines (``*.jsonl.gz``), written by ``fetch_reports``: one raw openFDA report per line.
- The legacy flattened CSV of the first version of this project (``pd.json_normalize`` output, in
  which the drug and reaction lists are stored as Python literals).

``parse_reports`` turns either into one tidy row per report.
"""
from __future__ import annotations

import ast
import gzip
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd

API_URL = "https://api.fda.gov/drug/event.json"

# openFDA / ICH E2B codes
AGE_UNIT_TO_YEARS = {800: 10.0, 801: 1.0, 802: 1 / 12, 803: 1 / 52.18, 804: 1 / 365.25, 805: 1 / 8766.0}
SEX = {1: "male", 2: "female"}
QUALIFICATION = {1: "physician", 2: "pharmacist", 3: "other health professional", 4: "lawyer", 5: "consumer"}
SERIOUSNESS_FLAGS = ["seriousnessdeath", "seriousnesslifethreatening", "seriousnesshospitalization",
                     "seriousnessdisabling", "seriousnesscongenitalanomali", "seriousnessother"]


# ---------------------------------------------------------------- download
def trim(rep: dict) -> dict:
    """Keep only the fields this project uses, so the stored sample stays small."""
    patient = rep.get("patient") or {}
    keep_drug = lambda d: {"drugcharacterization": d.get("drugcharacterization"),
                           "medicinalproduct": d.get("medicinalproduct"),
                           "activesubstance": d.get("activesubstance"),
                           "openfda": {"generic_name": (d.get("openfda") or {}).get("generic_name")}}
    return {
        **{k: rep.get(k) for k in ["safetyreportid", "serious", "receivedate", "occurcountry", *SERIOUSNESS_FLAGS]},
        "primarysource": {"qualification": (rep.get("primarysource") or {}).get("qualification")},
        "patient": {**{k: patient.get(k) for k in ["patientonsetage", "patientonsetageunit", "patientsex",
                                                   "patientweight"]},
                    "drug": [keep_drug(d) for d in patient.get("drug") or []],
                    "reaction": [{"reactionmeddrapt": r.get("reactionmeddrapt")} for r in patient.get("reaction") or []]},
    }


def fetch_reports(start: str, end: str, per_day: int, out: Path, api_key: str | None = None,
                  pause: float = 0.3) -> int:
    """Download up to ``per_day`` reports received on each day between start and end (YYYYMMDD).

    One small request per day spreads the sample over the whole period. A single large query would
    return reports in the API's default order, which in practice come from only a few days.
    The API key, if given, is passed by the caller from the environment and never stored.
    """
    import requests

    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        for day in pd.date_range(pd.to_datetime(start), pd.to_datetime(end), freq="D"):
            params = {"search": f"receivedate:{day:%Y%m%d}", "limit": per_day}
            if api_key:
                params["api_key"] = api_key
            for attempt in range(4):
                r = requests.get(API_URL, params=params, timeout=60)
                if r.status_code in (200, 404):  # 404 = no reports that day (e.g. weekends)
                    break
                time.sleep(3 * (attempt + 1))
            results = r.json().get("results", []) if r.status_code == 200 else []
            if r.status_code not in (200, 404):
                print(f"{day:%Y-%m-%d}: HTTP {r.status_code}, skipped", flush=True)
            for rep in results:
                fh.write(json.dumps(trim(rep)) + "\n")
            n += len(results)
            time.sleep(pause)
    return n


# ---------------------------------------------------------------- parsing helpers
def _num(v) -> float:
    try:
        f = float(v)
        return f if np.isfinite(f) else np.nan
    except (TypeError, ValueError):
        return np.nan


def _code(v) -> int | None:
    f = _num(v)
    return None if np.isnan(f) else int(f)


def age_in_years(age, unit) -> float:
    a, u = _num(age), _code(unit)
    if np.isnan(a) or u not in AGE_UNIT_TO_YEARS:
        return np.nan
    years = a * AGE_UNIT_TO_YEARS[u]
    return years if 0 <= years <= 120 else np.nan


def drug_name(drug: dict) -> str | None:
    """Active substance if given, otherwise the openFDA generic name, otherwise the reported product."""
    sub = (drug.get("activesubstance") or {}).get("activesubstancename")
    if not sub:
        generic = (drug.get("openfda") or {}).get("generic_name") or []
        sub = generic[0] if generic else drug.get("medicinalproduct")
    if not sub:
        return None
    return " ".join(str(sub).upper().replace(".", "").split())


def _legacy_record(row: pd.Series) -> dict:
    """Rebuild the nested report structure from a row of the legacy flattened CSV."""
    def lit(v):
        if isinstance(v, str) and v.startswith("["):
            return ast.literal_eval(v)
        return []
    return {
        "safetyreportid": str(row.get("safetyreportid")),
        "serious": row.get("serious"),
        **{f: row.get(f) for f in SERIOUSNESS_FLAGS},
        "receivedate": str(row.get("receivedate", "")).split(".")[0],
        "occurcountry": row.get("occurcountry"),
        "primarysource": {"qualification": row.get("primarysource.qualification")},
        "patient": {"patientonsetage": row.get("patient.patientonsetage"),
                    "patientonsetageunit": row.get("patient.patientonsetageunit"),
                    "patientsex": row.get("patient.patientsex"),
                    "patientweight": row.get("patient.patientweight"),
                    "drug": lit(row.get("patient.drug")),
                    "reaction": lit(row.get("patient.reaction"))},
    }


def load_raw(path: Path) -> list[dict]:
    path = Path(path)
    if path.name.endswith(".jsonl.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]
    if path.suffix == ".csv":
        df = pd.read_csv(path, low_memory=False)
        return [_legacy_record(r) for _, r in df.iterrows()]
    raise ValueError(f"Unsupported file: {path}")


# ---------------------------------------------------------------- tidy table
def parse_reports(records: list[dict]) -> pd.DataFrame:
    """One row per unique report. Columns: identifiers, target, demographics, drug and reaction lists."""
    rows = {}
    for rep in records:
        rid = str(rep.get("safetyreportid"))
        patient = rep.get("patient") or {}
        drugs = patient.get("drug") or []
        suspect = sorted({n for d in drugs if str(d.get("drugcharacterization", "")).split(".")[0] == "1"
                          and (n := drug_name(d))})
        all_drugs = sorted({n for d in drugs if (n := drug_name(d))})
        reactions = sorted({str(r["reactionmeddrapt"]).strip().capitalize()
                            for r in (patient.get("reaction") or []) if r.get("reactionmeddrapt")})
        serious = _code(rep.get("serious"))
        row = {
            "report_id": rid,
            "receivedate": str(rep.get("receivedate", "")),
            "serious": {1: 1, 2: 0}.get(serious, np.nan),
            "death": int(_code(rep.get("seriousnessdeath")) == 1),
            "hospitalization": int(_code(rep.get("seriousnesshospitalization")) == 1),
            "age_years": age_in_years(patient.get("patientonsetage"), patient.get("patientonsetageunit")),
            "sex": SEX.get(_code(patient.get("patientsex")), "unknown"),
            "weight_kg": _num(patient.get("patientweight")),
            "reporter": QUALIFICATION.get(_code((rep.get("primarysource") or {}).get("qualification")), "unknown"),
            "country": rep.get("occurcountry") if isinstance(rep.get("occurcountry"), str) else "unknown",
            "suspect_drugs": suspect,
            "all_drugs": all_drugs,
            "reactions": reactions,
            "n_drugs": len(all_drugs),
            "n_reactions": len(reactions),
        }
        rows[rid] = row  # duplicates of the same report id: keep the last occurrence
    df = pd.DataFrame(list(rows.values()))
    return df.dropna(subset=["serious"]).astype({"serious": int}).reset_index(drop=True)


def deduplicate(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Remove probable duplicate cases: different report ids with the same suspect drugs, reactions,
    age, sex and country (a simple version of FAERS case deduplication). Returns (df, n_removed)."""
    key = df.apply(lambda r: (tuple(r.suspect_drugs), tuple(r.reactions),
                              None if pd.isna(r.age_years) else round(r.age_years, 1), r.sex, r.country), axis=1)
    keep = ~key.duplicated()
    return df[keep].reset_index(drop=True), int((~keep).sum())


def api_key_from_env() -> str | None:
    return os.environ.get("OPENFDA_API_KEY") or None
