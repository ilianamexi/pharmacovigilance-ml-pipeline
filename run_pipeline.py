"""Pharmacovigilance pipeline on openFDA FAERS reports: data preparation, signal detection and
seriousness prediction.

Usage:
    python run_pipeline.py fetch --start 20230101 --end 20231231 --per-day 20   # optional download
    python run_pipeline.py run                      # uses the bundled sample data/faers_reports.jsonl.gz
    python run_pipeline.py run --data my_reports.jsonl.gz

The openFDA API key, if you have one, is read from the OPENFDA_API_KEY environment variable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_predict, StratifiedKFold, train_test_split

from pv import data as pvdata
from pv import model as pvmodel
from pv.signals import detect_signals

ROOT = Path(__file__).resolve().parent
DEFAULT_JSONL = ROOT / "data" / "faers_reports.jsonl.gz"


def fetch(args) -> None:
    n = pvdata.fetch_reports(args.start, args.end, args.per_day, Path(args.out), pvdata.api_key_from_env())
    print(f"Saved {n} reports to {args.out}")


# ---------------------------------------------------------------- figures
def eda_figures(df: pd.DataFrame, out: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    rates = df.groupby("reporter")["serious"].agg(["mean", "size"]).sort_values("size", ascending=False)
    axes[0].barh(rates.index, rates["mean"] * 100, color="#4C72B0")
    for i, (m, s) in enumerate(zip(rates["mean"], rates["size"])):
        axes[0].text(m * 100 + 1, i, f"n={s}", va="center", fontsize=8)
    axes[0].set(xlabel="% serious", title="Serious reports by reporter type", xlim=(0, 110))
    axes[0].invert_yaxis()

    for flag, label in [(1, "serious"), (0, "non-serious")]:
        axes[1].hist(df.loc[df.serious == flag, "age_years"].dropna(), bins=range(0, 105, 5), alpha=0.6, label=label)
    axes[1].set(xlabel="Age (years)", ylabel="Reports", title="Age distribution")
    axes[1].legend()

    top = df["suspect_drugs"].explode().value_counts().head(12)[::-1]
    axes[2].barh(top.index, top.values, color="#55A868")
    axes[2].set(xlabel="Reports (as suspect drug)", title="Most reported suspect drugs")
    axes[2].tick_params(axis="y", labelsize=8)
    fig.tight_layout()
    fig.savefig(out / "eda.png", dpi=140)
    plt.close(fig)


def top_signals(sig: pd.DataFrame, min_reports: int = 10, top: int = 15) -> pd.DataFrame:
    """Signals with the most reports. Pairs seen in only 3-9 reports get huge, unstable ratios in a
    sample of this size, so the summary shows the better-supported ones."""
    return sig[sig.signal & (sig.a >= min_reports)].sort_values("a", ascending=False).head(top)


def signal_figure(sig: pd.DataFrame, out: Path) -> None:
    s = top_signals(sig)[::-1]
    if s.empty:
        return
    fig, ax = plt.subplots(figsize=(10, 0.4 * len(s) + 1.4))
    y = np.arange(len(s))
    ax.errorbar(s["ROR"], y, xerr=[s["ROR"] - s["ROR_low"], s["ROR_high"] - s["ROR"]], fmt="o", color="#C44E52",
                capsize=3)
    ax.set_yticks(y, [f"{d.title()} – {r} (n={a})" for d, r, a in zip(s.drug, s.reaction, s.a)], fontsize=8)
    ax.set_xscale("log")
    ax.axvline(1, color="grey", lw=0.8)
    ax.set_xlabel("Reporting odds ratio (95% CI, log scale)")
    ax.set_title("Signals with the most reports (Evans criteria, n ≥ 10)", loc="left")
    fig.tight_layout()
    fig.savefig(out / "signals.png", dpi=140)
    plt.close(fig)


# ---------------------------------------------------------------- main analysis
def run(args) -> None:
    path = Path(args.data) if args.data else DEFAULT_JSONL
    if not path.exists():
        raise SystemExit(f"{path} not found: run `python run_pipeline.py fetch` first")
    results, figures = ROOT / "results", ROOT / "figures"
    results.mkdir(exist_ok=True)
    figures.mkdir(exist_ok=True)

    df = pvdata.parse_reports(pvdata.load_raw(path))
    n_unique_ids = len(df)
    df, n_dupes = pvdata.deduplicate(df)
    dates = pd.to_datetime(df["receivedate"], format="%Y%m%d", errors="coerce")
    print(f"{n_unique_ids} reports, {n_dupes} probable duplicate cases removed -> {len(df)} reports from {path.name} ({dates.min():%Y-%m-%d} to {dates.max():%Y-%m-%d}), "
          f"{df.serious.mean():.1%} serious")
    summary = {"data_file": path.name, "n_report_ids": n_unique_ids, "duplicates_removed": n_dupes,
               "n_reports": len(df), "days_covered": int(dates.dt.normalize().nunique()), "serious_rate": round(float(df.serious.mean()), 4),
               "date_range": [f"{dates.min():%Y-%m-%d}", f"{dates.max():%Y-%m-%d}"],
               "age_missing": round(float(df.age_years.isna().mean()), 4),
               "reports_without_suspect_drug": int((df.n_drugs == 0).sum())}
    eda_figures(df, figures)

    # 1. signal detection
    sig = detect_signals(df)
    sig.to_csv(results / "signals.csv", index=False)
    signal_figure(sig, figures)
    summary["signals"] = {"pairs_with_3plus_reports": int(len(sig)), "signals": int(sig.signal.sum())}
    print(f"{int(sig.signal.sum())} drug-reaction signals among {len(sig)} pairs with >= 3 reports")

    # 2. seriousness prediction: hold out 25% for the final test
    train_df, test_df = train_test_split(df, test_size=0.25, stratify=df.serious, random_state=args.seed)
    summary["split"] = {"train": len(train_df), "test": len(test_df)}
    rows = []
    for drop_terms in (True, False):
        Xtr = pvmodel.add_text_columns(train_df, drop_terms)
        Xte = pvmodel.add_text_columns(test_df, drop_terms)
        ytr, yte = train_df.serious.to_numpy(), test_df.serious.to_numpy()
        models = pvmodel.candidate_models(args.seed)
        if not drop_terms:  # ablation: only re-run the models, not the baseline
            models = {k: v for k, v in models.items() if "baseline" not in k}
        for name, (pipe, grid) in models.items():
            search = pvmodel.tune(pipe, grid, Xtr, ytr, args.seed)
            oof = cross_val_predict(search.best_estimator_, Xtr, ytr, method="predict_proba",
                                    cv=StratifiedKFold(5, shuffle=True, random_state=args.seed))[:, 1]
            thr = pvmodel.best_threshold(ytr, oof) if "baseline" not in name else 0.5
            p = search.predict_proba(Xte)[:, 1]
            m = pvmodel.metrics(yte, p, thr)
            ci = pvmodel.bootstrap_ci(yte, p, thr)
            row = {"model": name, "outcome_terms_removed": drop_terms, "cv_AUPRC": round(search.best_score_, 4),
                   "threshold": round(thr, 4), "best_params": json.dumps(search.best_params_),
                   **{k: round(v, 4) for k, v in m.items()},
                   **{f"{k}_ci": [round(a, 3), round(b, 3)] for k, (a, b) in ci.items()}}
            rows.append(row)
            print(f"[{'no outcome terms' if drop_terms else 'all terms'}] {name}: AUROC {m['AUROC']:.3f} "
                  f"AUPRC {m['AUPRC']:.3f} F1 {m['F1']:.3f} (CV AUPRC {search.best_score_:.3f})", flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(results / "model_results.csv", index=False)
    summary["models"] = rows
    (results / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_markdown(summary, res, sig, results / "summary.md")


def write_markdown(summary: dict, res: pd.DataFrame, sig: pd.DataFrame, path: Path) -> None:
    def fmt(r, k):
        lo, hi = r[f"{k}_ci"]
        return f"{r[k]:.3f} [{lo:.3f}–{hi:.3f}]"
    lines = [f"Data: {summary['n_reports']} reports after removing {summary['duplicates_removed']} probable duplicates, "
             f"received on {summary['days_covered']} days ({summary['date_range'][0]} to {summary['date_range'][1]}), "
             f"{summary['serious_rate']:.1%} serious. Train {summary['split']['train']} / test {summary['split']['test']}.", ""]
    for flag, title in [(True, "Outcome-restating reaction terms removed (main analysis)"),
                        (False, "All reaction terms kept (ablation)")]:
        lines += [f"**{title}**", "", "| Model | AUROC [95% CI] | AUPRC [95% CI] | Precision | Recall | F1 | Bal. acc. |",
                  "|---|---|---|---|---|---|---|"]
        for _, r in res[res.outcome_terms_removed == flag].iterrows():
            lines.append(f"| {r.model} | {fmt(r, 'AUROC')} | {fmt(r, 'AUPRC')} | {r.precision:.3f} | {r.recall:.3f} | "
                         f"{r.F1:.3f} | {r.balanced_accuracy:.3f} |")
        lines.append("")
    top = top_signals(sig)
    lines += [f"**Signals**: {int(sig.signal.sum())} of {len(sig)} drug–reaction pairs with ≥ 3 reports meet the "
              f"Evans criteria. The {len(top)} with the most reports (≥ 10):", "",
              "| Drug | Reaction | Reports | PRR | ROR [95% CI] | χ² |", "|---|---|---|---|---|---|"]
    for _, r in top.iterrows():
        lines.append(f"| {r.drug} | {r.reaction} | {int(r.a)} | {r.PRR:.1f} | {r.ROR:.1f} [{r.ROR_low:.1f}–{r.ROR_high:.1f}] "
                     f"| {r.chi2_yates:.1f} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + "\n".join(lines))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--start", default="20230101")
    f.add_argument("--end", default="20231231")
    f.add_argument("--per-day", type=int, default=20)
    f.add_argument("--out", default=str(DEFAULT_JSONL))
    r = sub.add_parser("run")
    r.add_argument("--data", default=None)
    r.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    fetch(args) if args.cmd == "fetch" else run(args)


if __name__ == "__main__":
    main()
