"""
Shows the results split by driving situation (mobility condition) and by vehicle
density, which is how the project brief says the strategies should be evaluated.

Run from the repo root:
    python analysis/results_by_scenario.py

Prints one table per driving situation, and writes
    analysis/results_by_scenario.csv   (scenario x strategy)
    analysis/results_by_density.csv    (density x strategy)
Nothing in the submitted results is changed - this only reads results/all_results.csv.
"""
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_CSV = os.path.join(os.path.dirname(HERE), "results", "all_results.csv")

STRATEGY_ORDER = ["raw", "quantization_32bit", "delta", "quantization_16bit",
                  "quantization_12bit", "event_triggered", "quantization_8bit", "adaptive"]
SCENARIOS = {
    "steady_speed": "constant-speed movement",
    "accel_decel": "acceleration / deceleration (traffic light)",
    "turning": "junction / turning",
    "lane_change": "lane changing (slow cars force overtakes)",
}


def summarize(df, group_col):
    raw_bytes = df[df.strategy == "raw"].groupby(group_col).bytes_sent.sum()
    out = df.groupby([group_col, "strategy"]).agg(
        total_bytes=("bytes_sent", "sum"),
        packets_per_sec_per_vehicle=("transmitted", "mean"),
        avg_position_error_m=("position_error", "mean"),
        avg_speed_error=("speed_error", "mean"),
        avg_heading_error_deg=("heading_error", "mean"),
        avg_aoi_s=("age_of_information", "mean"),
        peak_aoi_s=("age_of_information", "max"),
    ).reset_index()
    out["pct_of_raw_bytes"] = (100 * out["total_bytes"] / out[group_col].map(raw_bytes)).round(1)
    out["strategy"] = pd.Categorical(out["strategy"], STRATEGY_ORDER, ordered=True)
    cols = [group_col, "strategy", "pct_of_raw_bytes", "total_bytes", "packets_per_sec_per_vehicle",
            "avg_position_error_m", "avg_speed_error", "avg_heading_error_deg", "avg_aoi_s", "peak_aoi_s"]
    return out.sort_values([group_col, "strategy"])[cols].reset_index(drop=True)


def main():
    df = pd.read_csv(RESULTS_CSV)

    by_scenario = summarize(df, "scenario")
    by_scenario.to_csv(os.path.join(HERE, "results_by_scenario.csv"), index=False)
    by_density = summarize(df, "density")
    by_density.to_csv(os.path.join(HERE, "results_by_density.csv"), index=False)

    show = ["strategy", "pct_of_raw_bytes", "avg_position_error_m", "avg_aoi_s", "peak_aoi_s"]
    for scenario, label in SCENARIOS.items():
        print(f"\n=== {scenario}: {label} ===")
        print(by_scenario[by_scenario.scenario == scenario][show].round(3).to_string(index=False))

    print(f"\nWritten: {os.path.join(HERE, 'results_by_scenario.csv')}")
    print(f"         {os.path.join(HERE, 'results_by_density.csv')}")


if __name__ == "__main__":
    main()
