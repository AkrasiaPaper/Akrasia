import json
import pandas as pd
from pathlib import Path
from utils.constants import AttackTypesUtils

# ── Constants ──────────────────────────────────────────────────────────────────
TRIG_TYPES = ["comment", "adaptive", "grammar", "bimodal", "deadcode"]
ATK_TYPES = [
    value.replace(' ', "_") for key, value in vars(AttackTypesUtils).items()
    if not key.startswith('_')
]

BASE_DIR   = Path("results/defence")
DATASET    = "codemmlu"
MODEL      = "o3-mini-2025-01-31"
MODEL      = "gpt-5"


# ── File helpers ───────────────────────────────────────────────────────────────
def get_file_path(defence: str, trig_type: str, atk_type: str, metric: str) -> Path:
    filename = f"{atk_type}_with_{trig_type}_{metric}.json"
    return BASE_DIR / defence / DATASET / MODEL / trig_type / filename


def read_raw(path: Path, metric: str) -> dict | None:
    """Returns dict with n_success, n_total and rate, or None if missing/malformed."""
    if not path.exists():
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        return {
            "n_success": data.get("n_success"),
            "n_total":   data.get("n_total"),
            'n_error':   data.get('n_error'),
            "rate":      data.get(metric)
        }
    except Exception:
        return None


def fmt(result: dict | None) -> str | float:
    if result is None:
        return float("nan")
    rate      = result.get("rate")
    n_success = result.get("n_success")
    n_total   = result.get("n_total")
    n_error   = result.get("n_error") or 0
    if rate is None or n_success is None or n_total is None:
        return float("nan")
    adjusted_total = n_total - n_error
    rate = n_success / adjusted_total if adjusted_total > 0 else float("nan")
    return f"{rate:.4f} ({n_success}/{adjusted_total})"


def agg_fmt(acc: dict) -> str | float:
    """Compute aggregated rate from accumulated counts. NaN only if nothing was accumulated."""
    if acc["n_total"] == 0:
        return float("nan")
    rate = acc["n_success"] / acc["n_total"]
    return f"{rate:.4f} ({acc['n_success']}/{acc['n_total']})"


# ── Core builder ───────────────────────────────────────────────────────────────
def build_table(defence: str) -> tuple[pd.DataFrame, list[str]]:
    missing = []

    # raw[trig][atk][metric] -> {n_success, n_total, rate} | None
    raw: dict = {trig: {atk: {} for atk in ATK_TYPES} for trig in TRIG_TYPES}

    for trig in TRIG_TYPES:
        for atk in ATK_TYPES:
            for metric in ["ASR", "ACC"]:
                path = get_file_path(defence, trig, atk, metric)
                result = read_raw(path, metric)
                if result is None:
                    missing.append(str(path))
                raw[trig][atk][metric] = result

    # ── Trig rows ──────────────────────────────────────────────────────────────
    records = {}

    for trig in TRIG_TYPES:
        row = {}
        agg_col = {"ASR": {"n_success": 0, "n_total": 0},
                   "ACC": {"n_success": 0, "n_total": 0}}

        for atk in ATK_TYPES:
            for metric in ["ASR", "ACC"]:
                result = raw[trig][atk][metric]
                row[f"{atk}_{metric}"] = fmt(result)
                if result is not None and result["n_success"] is not None and result["n_total"] is not None:
                    agg_col[metric]["n_success"] += result["n_success"]
                    agg_col[metric]["n_total"]   += result["n_total"] - (result["n_error"] or 0)

        for metric in ["ASR", "ACC"]:
            row[f"aggregate_{metric}"] = agg_fmt(agg_col[metric])

        records[trig] = row

    # ── Aggregate row ──────────────────────────────────────────────────────────
    agg_row = {}
    grand   = {"ASR": {"n_success": 0, "n_total": 0},
               "ACC": {"n_success": 0, "n_total": 0}}

    for atk in ATK_TYPES:
        agg_atk = {"ASR": {"n_success": 0, "n_total": 0},
                   "ACC": {"n_success": 0, "n_total": 0}}

        for trig in TRIG_TYPES:
            for metric in ["ASR", "ACC"]:
                result = raw[trig][atk][metric]
                if result is not None and result["n_success"] is not None and result["n_total"] is not None:
                    agg_atk[metric]["n_success"] += result["n_success"]
                    agg_atk[metric]["n_total"] += result["n_total"] - (result["n_error"] or 0)
                    grand[metric]["n_success"]   += result["n_success"]
                    grand[metric]["n_total"]   += result["n_total"] - (result["n_error"] or 0)
        for metric in ["ASR", "ACC"]:
            agg_row[f"{atk}_{metric}"] = agg_fmt(agg_atk[metric])

    for metric in ["ASR", "ACC"]:
        agg_row[f"aggregate_{metric}"] = agg_fmt(grand[metric])

    records["aggregate"] = agg_row

    # ── Assemble ───────────────────────────────────────────────────────────────
    df = pd.DataFrame.from_dict(records, orient="index")
    df.index.name = "trig_type"

    ordered_cols = []
    for atk in ATK_TYPES:
        ordered_cols += [f"{atk}_ASR", f"{atk}_ACC"]
    ordered_cols += ["aggregate_ASR", "aggregate_ACC"]
    df = df[ordered_cols]

    return df, missing


# ── Report ─────────────────────────────────────────────────────────────────────
def report(defence: str):
    df, missing = build_table(defence)

    print(f"\n{'='*80}")
    print(f"Defence: {defence}")
    print(f"{'='*80}")
    pd.set_option("display.max_columns", None)
    pd.set_option("display.max_colwidth", 30)
    pd.set_option("display.width", 300)
    print(df.to_string())

    if missing:
        print(f"\n⚠  Missing files ({len(missing)}):")
        for m in missing:
            print(f"   {m}")
    else:
        print("\n✓ No missing files.")

    return df, missing


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    for defence in ["CoS", "ONION", "Shuffle", "Shuffle++"]:
        df, missing = report(defence)