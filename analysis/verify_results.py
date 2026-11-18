"""
Checks the experiment results two ways.   Run from the repo root:

    python analysis/verify_results.py
    python analysis/verify_results.py --results some_other_results.csv

A. SANITY CHECKS - nothing to compare against. They test the results against
   arithmetic and maths that MUST be true if the code is right (packet sizes,
   "a quantizer can never be wrong by more than half a step", bookkeeping rules).
   A wrong strategy implementation would break these.

B. COMPARISON WITH THE REFERENCE RESULTS - the numbers this project reported.
   If they differ, the likely cause is a different SUMO version (the project
   pins eclipse-sumo 1.27.1; check with `pip show eclipse-sumo`).

Exit code is 0 when every sanity check passes, 1 otherwise.
"""
import argparse
import math
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RESULTS = os.path.join(os.path.dirname(HERE), "results", "all_results.csv")

COLUMNS = ["t", "vehicle_id", "density", "scenario", "strategy", "rsu_id", "transmitted",
           "bytes_sent", "position_error", "speed_error", "heading_error", "age_of_information"]

# The CSV stores errors rounded to 4 decimals, so allow a little slack in every bound.
ROUNDING_SLACK = 5e-4

# Packet size in bytes = ceil(bits * 5 fields / 8) + 4-byte header (see strategies/common.py).
SEND_EVERY_SECOND = {          # strategy -> expected bytes per packet
    "raw": 24, "delta": 14,
    "quantization_8bit": 9, "quantization_12bit": 12,
    "quantization_16bit": 14, "quantization_32bit": 24,
}
QUANT_BITS = {"quantization_8bit": 8, "quantization_12bit": 12,
              "quantization_16bit": 16, "quantization_32bit": 32}

# Reference numbers reported by the project: (% of raw bytes, average position error in m)
REFERENCE = {
    "raw": (100.0, 0.000), "quantization_32bit": (100.0, 0.000),
    "delta": (58.3, 0.001), "quantization_16bit": (58.3, 0.005),
    "quantization_12bit": (50.0, 0.069), "event_triggered": (65.5, 0.092),
    "quantization_8bit": (37.5, 1.334), "adaptive": (26.7, 1.218),
}
REFERENCE_ROWS = 410136
REFERENCE_PEAK_AOI = {"event_triggered": 44, "adaptive": 1}

failures = 0


def report(ok, name, detail=""):
    global failures
    if not ok:
        failures += 1
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def sanity_checks(df):
    print("A. Sanity checks (these must hold if the code is right)")

    missing = [c for c in COLUMNS if c not in df.columns]
    report(not missing and not df.isna().any().any(),
           "File has every expected column and no missing values", f"missing columns: {missing}" if missing else "")
    if missing:
        return

    sizes = df.groupby("strategy").size()
    report(sizes.nunique() == 1,
           "Every strategy has the same number of rows (they all watch the same car-seconds)",
           f"{sizes.nunique()} different counts" if sizes.nunique() != 1 else f"{sizes.iloc[0]:,} each")

    # Time step must be exactly 1 s, otherwise every "per second" metric would be wrong.
    raw = df[df.strategy == "raw"].sort_values(["scenario", "density", "vehicle_id", "t"])
    step = raw.groupby(["scenario", "density", "vehicle_id"]).t.diff().dropna()
    report((step == 1.0).all(), "Time advances exactly 1 second per row for every car (so 'per second' is valid)")

    r = df[df.strategy == "raw"]
    report(r.transmitted.eq(1).all() and r.bytes_sent.eq(24).all()
           and (r[["position_error", "speed_error", "heading_error", "age_of_information"]] == 0).all().all(),
           "Raw: every row sent, 24 bytes each, and zero error and zero Age of Information")
    report(r.bytes_sent.sum() == 24 * len(r), "Raw total bytes = 24 x number of car-seconds")

    for strategy, expected in SEND_EVERY_SECOND.items():
        d = df[df.strategy == strategy]
        ok = d.transmitted.eq(1).all() and d.bytes_sent.eq(expected).all() and d.age_of_information.eq(0).all()
        report(ok, f"{strategy}: sends every second, always {expected} bytes, Age of Information always 0")

    ev = df[df.strategy == "event_triggered"]
    report(set(ev.bytes_sent.unique()) <= {0, 24} and ((ev.bytes_sent > 0) == (ev.transmitted == 1)).all(),
           "event_triggered: a packet is 24 bytes when sent and 0 bytes when not")
    ad = df[df.strategy == "adaptive"]
    report(set(ad.bytes_sent.unique()) <= {0, 9, 14} and ((ad.bytes_sent > 0) == (ad.transmitted == 1)).all(),
           "adaptive: a packet is 9 bytes (stable) or 14 bytes (maneuvering) when sent, 0 when not")

    for name, d in (("event_triggered", ev), ("adaptive", ad)):
        report(d[d.transmitted == 1].age_of_information.eq(0).all()
               and d[d.transmitted == 0].age_of_information.gt(0).all(),
               f"{name}: Age of Information is 0 exactly when a packet is sent, above 0 otherwise")

    report(ad.age_of_information.max() <= 1.0 + 1e-9,
           "adaptive: never goes 2 seconds without an update (its staleness rule), so Age of Information <= 1 s",
           f"worst seen {ad.age_of_information.max():g} s")

    # A quantizer can never be wrong by more than half a step.
    for strategy, bits in QUANT_BITS.items():
        d = df[df.strategy == strategy]
        levels = 2 ** bits - 1
        limits = {"position_error": math.sqrt(2) * (1000 / levels) / 2,   # +-500 m range, 2 axes
                  "speed_error": (40 / levels) / 2,                        # 0-40 m/s range
                  "heading_error": (360 / levels) / 2}                     # 0-360 deg range
        ok = all(d[col].max() <= lim + ROUNDING_SLACK for col, lim in limits.items())
        report(ok, f"{strategy}: errors never exceed half a quantization step",
               f"worst position {d.position_error.max():.4f} m vs limit {limits['position_error']:.4f} m")

    # Delta sends 16-bit changes, so each step's error is at most half of that step.
    d = df[df.strategy == "delta"]
    limits = {"position_error": math.sqrt(2) * (100 / 65535) / 2,
              "speed_error": (20 / 65535) / 2,
              "heading_error": (360 / 65535) / 2}
    report(all(d[col].max() <= lim + ROUNDING_SLACK for col, lim in limits.items()),
           "delta: errors never exceed half a 16-bit step (so errors do not pile up over time)",
           f"worst position {d.position_error.max():.4f} m vs limit {limits['position_error']:.4f} m")


def reference_comparison(df):
    print("\nB. Comparison with the reference results this project reported")
    differences = 0

    def line(ok, text):
        nonlocal differences
        if not ok:
            differences += 1
        print(f"  {'MATCH    ' if ok else 'DIFFERENT'}  {text}")

    line(len(df) == REFERENCE_ROWS, f"total rows: {len(df):,} (reference {REFERENCE_ROWS:,})")
    raw_bytes = df[df.strategy == "raw"].bytes_sent.sum()
    for strategy, (ref_pct, ref_err) in REFERENCE.items():
        d = df[df.strategy == strategy]
        pct = 100 * d.bytes_sent.sum() / raw_bytes
        err = d.position_error.mean()
        line(abs(pct - ref_pct) <= 0.2 and abs(err - ref_err) <= 0.01,
             f"{strategy:19s} {pct:5.1f}% of raw bytes, {err:.3f} m error  "
             f"(reference {ref_pct:.1f}%, {ref_err:.3f} m)")
    for strategy, ref in REFERENCE_PEAK_AOI.items():
        peak = df[df.strategy == strategy].age_of_information.max()
        line(abs(peak - ref) <= 1, f"{strategy:19s} peak Age of Information {peak:g} s (reference {ref} s)")
    return differences


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default=DEFAULT_RESULTS)
    args = parser.parse_args()

    if not os.path.exists(args.results):
        sys.exit(f"Results file not found: {args.results}\nRun  python experiments/experiment_runner.py  first.")
    df = pd.read_csv(args.results)
    print(f"Results file: {args.results}  ({len(df):,} rows)\n")

    sanity_checks(df)
    differences = reference_comparison(df)

    print()
    if failures == 0:
        print("RESULT: ALL SANITY CHECKS PASSED - the numbers obey the arithmetic and maths they must obey.")
    else:
        print(f"RESULT: {failures} SANITY CHECK(S) FAILED - something in the pipeline or the file is wrong.")
    if differences:
        print(f"NOTE: {differences} reference number(s) differ. If the sanity checks pass, the usual cause is a "
              "different SUMO version (project pins eclipse-sumo 1.27.1).")
    else:
        print("Reference comparison: every number matches the project's reported results.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
