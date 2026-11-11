import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pv import data as pvdata  # noqa: E402
from pv import model as pvmodel  # noqa: E402
from pv.signals import detect_signals, disproportionality  # noqa: E402


def report(rid, serious, drugs, reactions, age="40", unit="801", sex="2", qual="1"):
    return {"safetyreportid": rid, "serious": serious, "receivedate": "20230105", "occurcountry": "US",
            "primarysource": {"qualification": qual},
            "patient": {"patientonsetage": age, "patientonsetageunit": unit, "patientsex": sex,
                        "drug": [{"drugcharacterization": "1", "activesubstance": {"activesubstancename": d}}
                                 for d in drugs] + [{"drugcharacterization": "2", "medicinalproduct": "concomitant x"}],
                        "reaction": [{"reactionmeddrapt": r} for r in reactions]}}


def test_parsing_units_duplicates_and_suspect_drugs():
    recs = [report("1", "1", ["Drug A"], ["Nausea"], age="18", unit="802"),  # 18 months
            report("2", "2", ["drug b."], ["Rash", "rash"], age="3", unit="800"),  # 3 decades
            report("2", "2", ["DRUG B"], ["Rash"]),  # duplicate id: last version kept
            report("3", "x", ["Drug C"], ["Headache"])]  # invalid seriousness -> dropped
    df = pvdata.parse_reports(recs)
    assert df.report_id.tolist() == ["1", "2"]
    assert np.isclose(df.age_years[0], 1.5)
    assert df.suspect_drugs[1] == ["DRUG B"] and df.all_drugs[1] == ["CONCOMITANT X", "DRUG B"]
    assert df.serious.tolist() == [1, 0] and df.sex[0] == "female" and df.reporter[0] == "physician"


def test_disproportionality_matches_hand_calculation():
    pairs = pd.DataFrame({"drug": ["A"], "reaction": ["R"], "a": [10], "b": [90], "c": [20], "d": [880]})
    r = disproportionality(pairs).iloc[0]
    assert np.isclose(r.PRR, (10 / 100) / (20 / 900))           # 4.5
    assert np.isclose(r.ROR, (10 * 880) / (90 * 20))             # 4.89
    se = np.sqrt(1 / 10 + 1 / 90 + 1 / 20 + 1 / 880)
    assert np.isclose(r.ROR_low, r.ROR * np.exp(-1.96 * se))
    assert r.signal


def test_signal_detection_finds_planted_pair_and_skips_product_terms():
    recs = [report(str(i), "2", ["D1"], ["Liver injury", "Product quality issue"]) for i in range(6)]
    recs += [report(str(100 + i), "2", [f"D{2 + i % 5}"], ["Nausea"]) for i in range(60)]
    sig = detect_signals(pvdata.parse_reports(recs))
    flagged = set(zip(sig[sig.signal].drug, sig[sig.signal].reaction))
    assert ("D1", "Liver injury") in flagged
    assert not any(r.startswith("Product") for _, r in flagged)


def test_outcome_terms_removed_and_smote_only_inside_pipeline():
    rng = np.random.default_rng(0)
    recs = []
    for i in range(160):
        serious = rng.random() < 0.3
        reactions = (["Liver injury"] if serious else ["Rash"]) + (["Death"] if serious and i % 2 else [])
        recs.append(report(str(i), "1" if serious else "2", [f"D{i % 4}"], reactions, age=str(20 + i % 50)))
    df = pvdata.parse_reports(recs)
    X = pvmodel.add_text_columns(df, drop_outcome_terms=True)
    assert not any("Death" in r for r in X.reaction_list)
    pipe, grid = pvmodel.candidate_models()["Random forest + SMOTE"]
    pipe.fit(X, df.serious)
    # SMOTE is a sampler in the pipeline: it is applied in fit only, so predict returns one row per report
    assert pipe.predict_proba(X).shape == (len(df), 2)
    assert "smote" in pipe.named_steps


def test_deduplication_and_trim():
    recs = [report("1", "1", ["Drug A"], ["Nausea"]), report("2", "1", ["DRUG A"], ["nausea"]),
            report("3", "1", ["Drug A"], ["Nausea"], age="41")]
    df, removed = pvdata.deduplicate(pvdata.parse_reports(recs))
    assert removed == 1 and df.report_id.tolist() == ["1", "3"]
    t = pvdata.trim({**recs[0], "patient": {**recs[0]["patient"], "summary": {"x": 1}}, "companynumb": "C"})
    assert "companynumb" not in t and "summary" not in t["patient"]
    assert pvdata.parse_reports([t]).equals(pvdata.parse_reports([recs[0]]))
