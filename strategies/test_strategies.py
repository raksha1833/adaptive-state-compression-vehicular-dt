"""
Runs all five strategies against a real vehicle-state CSV (the output of
phase 3's extract_state_rsu.py) and prints a comparison: total bytes sent,
mean errors, and mean Age of Information -- per vehicle, then averaged
across all vehicles in the run.

First create a state CSV (run from the repo root):
    python traci_scripts/extract_state_rsu.py --cfg network/run_configs/turning_20.sumocfg --net intersection --out results/turning_20_states.csv
Then compare the strategies on it:
    python strategies/test_strategies.py results/turning_20_states.csv intersection
"""
import csv
import statistics as stats
import sys
from collections import defaultdict

import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "traci_scripts"))
from extract_state_rsu import resolve_rsu_positions  # noqa: E402

from common import VehicleState  # noqa: E402
from raw import RawStrategy  # noqa: E402
from delta import DeltaStrategy  # noqa: E402
from quantization import QuantizationStrategy  # noqa: E402
from event_triggered import EventTriggeredStrategy  # noqa: E402
from adaptive import AdaptiveStrategy  # noqa: E402


def load_trajectories(csv_path):
    by_vehicle = defaultdict(list)
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            state = VehicleState(
                vehicle_id=row["vehicle_id"], t=float(row["t"]),
                x=float(row["x"]), y=float(row["y"]),
                speed=float(row["speed"]), heading=float(row["heading"]),
                accel=float(row["accel"]),
            )
            by_vehicle[row["vehicle_id"]].append((state, row["rsu_id"]))
    return by_vehicle


def run_strategy_on_vehicle(make_strategy, needs_rsu, trajectory, rsu_lookup):
    strategy = make_strategy()
    results = []
    for state, rsu_id in trajectory:
        if needs_rsu:
            rx, ry = rsu_lookup[rsu_id]
            results.append(strategy.step(state, rx, ry))
        else:
            results.append(strategy.step(state))
    return results


def summarize(results):
    return {
        "total_bytes": sum(r.bytes_sent for r in results),
        "pct_transmitted": round(100 * sum(r.transmitted for r in results) / len(results), 1),
        "avg_position_error": round(stats.mean(r.position_error for r in results), 3),
        "avg_speed_error": round(stats.mean(r.speed_error for r in results), 3),
        "avg_heading_error": round(stats.mean(r.heading_error for r in results), 2),
        "avg_aoi": round(stats.mean(r.age_of_information for r in results), 2),
    }


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO_ROOT, "results", "turning_20_states.csv")
    net_key = sys.argv[2] if len(sys.argv) > 2 else "intersection"

    rsus = resolve_rsu_positions(net_key)
    rsu_lookup = {r["id"]: (r["x"], r["y"]) for r in rsus}

    by_vehicle = load_trajectories(csv_path)

    strategies = {
        "raw": (lambda: RawStrategy(), False),
        "delta": (lambda: DeltaStrategy(), False),
        "quantization_8bit": (lambda: QuantizationStrategy(8), True),
        "quantization_16bit": (lambda: QuantizationStrategy(16), True),
        "event_triggered": (lambda: EventTriggeredStrategy(), False),
        "adaptive": (lambda: AdaptiveStrategy(), True),
    }

    print(f"Loaded {len(by_vehicle)} vehicles from {csv_path}\n")

    for name, (make_strategy, needs_rsu) in strategies.items():
        per_vehicle_summaries = []
        for vid, trajectory in by_vehicle.items():
            results = run_strategy_on_vehicle(make_strategy, needs_rsu, trajectory, rsu_lookup)
            per_vehicle_summaries.append(summarize(results))

        avg = {
            key: round(stats.mean(s[key] for s in per_vehicle_summaries), 2)
            for key in per_vehicle_summaries[0]
        }
        print(f"{name:20s} -> {avg}")


if __name__ == "__main__":
    main()
