"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    import math

    problems: list[str] = []
    m = pr.get("manifest", {})
    rows = pr.get("rows", [])
    # Dropped or duplicated rows: every (item, seed) must appear exactly once.
    want = m.get("items", 0) * len(m.get("seeds", []))
    if len(rows) != want:
        problems.append(f"{len(rows)} rows, expected {want} (items x seeds): rows were dropped or duplicated")
    keys = [(r["item_id"], r["seed"]) for r in rows]
    if len(set(keys)) != len(keys):
        problems.append("duplicate (item, seed) rows")
    base_keys = {(r["item_id"], r["seed"]) for r in base.get("rows", [])}
    if set(keys) != base_keys:
        problems.append("(item, seed) set differs from the baseline's: cherry-picked seeds or items")
    # NaN / inf values, and evaluator crashes that silently drop out of the mean.
    for k, v in pr.get("metrics", {}).items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            problems.append(f"metric {k} is {v}")
    if pr.get("evaluator_failures"):
        problems.append(f"{len(pr['evaluator_failures'])} evaluator failure(s): a crashed grader is not a pass")
    graded = [x["id"] for x in spec.get("metrics", [])]
    for r in rows:
        for g in graded:
            if g in r and r[g] is None:
                problems.append(f"{r['item_id']}@{r['seed']}: {g} is None")
                break
    # Slice tags must match the baseline's, item by item.
    base_tags = {r["item_id"]: sorted(r.get("slices") or []) for r in base.get("rows", [])}
    for r in rows:
        if r["item_id"] in base_tags and sorted(r.get("slices") or []) != base_tags[r["item_id"]]:
            problems.append(f"{r['item_id']}: slice tags changed from the baseline's")
            break
    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        problems += ratchet_problems(spec, base_spec)
    return problems


def ratchet_problems(spec: dict, base_spec: dict) -> list[str]:
    """Same eval-set version: thresholds may only get stricter. Report every loosening."""
    out: list[str] = []
    new = {m["id"]: m for m in spec.get("metrics", [])}
    for old in base_spec.get("metrics", []):
        mid = old["id"]
        if mid not in new:
            out.append(f"metric {mid} removed")
            continue
        n, o = new[mid], old
        nt, ot = n.get("threshold", {}), o.get("threshold", {})
        if "max" in ot and nt.get("max", float("inf")) > ot["max"]:
            out.append(f"{mid}: max raised {ot['max']} -> {nt.get('max')}")
        if "min" in ot and nt.get("min", float("-inf")) < ot["min"]:
            out.append(f"{mid}: min lowered {ot['min']} -> {nt.get('min')}")
        if "max_increase" in ot and nt.get("max_increase", float("inf")) > ot["max_increase"]:
            out.append(f"{mid}: max_increase raised")
        if ot.get("no_significant_drop") and not nt.get("no_significant_drop"):
            out.append(f"{mid}: no_significant_drop removed")
        if o.get("blocking") and not n.get("blocking"):
            out.append(f"{mid}: blocking turned off")
    new_slices = {s["name"]: s for s in spec.get("slices", [])}
    for old in base_spec.get("slices", []):
        name = old["name"]
        if name not in new_slices:
            out.append(f"slice {name} removed")
            continue
        n = new_slices[name]
        if "min" in old and n.get("min", float("-inf")) < old["min"]:
            out.append(f"slice {name}: min lowered {old['min']} -> {n.get('min')}")
        if old.get("no_significant_drop") and not n.get("no_significant_drop"):
            out.append(f"slice {name}: no_significant_drop removed")
        if old.get("blocking") and not n.get("blocking"):
            out.append(f"slice {name}: blocking turned off")
    return out


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked: list[str] = []
    lines: list[str] = []
    bs = spec.get("bootstrap", {})
    for s in spec.get("slices", []):
        name, metric = s["name"], s["metric"]
        pv, bv = per_item(pr, metric, slice_name=name), per_item(base, metric, slice_name=name)
        keys = sorted(set(pv) & set(bv))
        if not keys:
            lines.append(f"  slice:{name}/{metric:<12} no items in both reports")
            blocked.append(f"slice:{name}/{metric}")
            continue
        value = sum(pv[k] for k in keys) / len(keys)
        fail, note = False, f"n={len(keys)}"
        if "min" in s and value < s["min"]:
            fail = True
        if s.get("no_significant_drop") and len(keys) >= 2:
            d, lo, hi = stats.paired_bootstrap([pv[k] for k in keys], [bv[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note += f" Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                fail = True
        label = "BLOCK" if fail and s.get("blocking", True) else ("warn" if fail else "ok")
        if fail and s.get("blocking", True):
            blocked.append(f"slice:{name}/{metric}")
        lines.append(f"  slice:{name}/{metric:<12} {value:<8.4f} min {s.get('min', '-')!s:<5} {note:<34} {label}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
