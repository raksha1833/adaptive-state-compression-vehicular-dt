"""
Phase 6: runs every (scenario, density) config through every strategy and
logs everything to one CSV, ready for the analysis/plotting phase.

For each config, SUMO/TraCI is run ONCE (not once per strategy) -- every
strategy watches the same vehicle-state stream in parallel, since re-running
the simulation per strategy would be wasteful and the simulation itself
doesn't depend on which compression strategy you're evaluating.

Usage (run from the repo root):
    python experiments/experiment_runner.py                  # run all 20 configs
    python experiments/experiment_runner.py --limit 3        # quick test on the first 3
"""
import argparse
import csv
import glob
import math
import os
import sys

# All paths are built from this file's own location, so the script works no
# matter which folder you launch it from.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "strategies"))
sys.path.insert(0, os.path.join(REPO_ROOT, "traci_scripts"))

if "SUMO_HOME" not in os.environ:
    import sumo
    os.environ["SUMO_HOME"] = os.path.dirname(sumo.__file__)
sys.path.append(os.path.join(os.environ["SUMO_HOME"], "tools"))
import traci  # noqa: E402
import sumolib  # noqa: E402

from common import VehicleState  # noqa: E402
from raw import RawStrategy  # noqa: E402
from delta import DeltaStrategy  # noqa: E402
from quantization import QuantizationStrategy  # noqa: E402
from event_triggered import EventTriggeredStrategy  # noqa: E402
from adaptive import AdaptiveStrategy  # noqa: E402
from extract_state_rsu import resolve_rsu_positions  # noqa: E402

RUN_CONFIGS_DIR = os.path.join(REPO_ROOT, "network", "run_configs")
OUT_CSV = os.path.join(REPO_ROOT, "results", "all_results.csv")

SCENARIO_NET_KEY = {
    "steady_speed": "straight_road",
    "lane_change": "straight_road",
    "accel_decel": "intersection",
    "turning": "intersection",
}


def make_strategies():
    """A fresh set of strategy instances -- one per vehicle, since each
    strategy is stateful (it remembers what it last sent for THAT vehicle)."""
    return {
        "raw": (RawStrategy(), False),
        "delta": (DeltaStrategy(), False),
        "quantization_8bit": (QuantizationStrategy(8), True),
        "quantization_12bit": (QuantizationStrategy(12), True),
        "quantization_16bit": (QuantizationStrategy(16), True),
        "quantization_32bit": (QuantizationStrategy(32), True),
        "event_triggered": (EventTriggeredStrategy(), False),
        "adaptive": (AdaptiveStrategy(), True),
    }


def nearest_rsu(x, y, rsus):
    best_id, best_dist, best_xy = None, float("inf"), None
    for r in rsus:
        d = math.hypot(x - r["x"], y - r["y"])
        if d < best_dist:
            best_id, best_dist, best_xy = r["id"], d, (r["x"], r["y"])
    return best_id, best_xy


def run_one_config(cfg_path, scenario, density, net_key, writer):
    rsus = resolve_rsu_positions(net_key)
    traci.start([sumolib.checkBinary("sumo"), "-c", cfg_path, "--no-step-log", "true"])

    vehicle_strategies = {}
    row_count = 0

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        t = traci.simulation.getTime()

        for vid in traci.vehicle.getIDList():
            if vid not in vehicle_strategies:
                vehicle_strategies[vid] = make_strategies()

            x, y = traci.vehicle.getPosition(vid)
            state = VehicleState(
                vehicle_id=vid, t=t, x=x, y=y,
                speed=traci.vehicle.getSpeed(vid),
                heading=traci.vehicle.getAngle(vid),
                accel=traci.vehicle.getAcceleration(vid),
            )
            rsu_id, rsu_xy = nearest_rsu(x, y, rsus)

            for strat_name, (strategy, needs_rsu) in vehicle_strategies[vid].items():
                if needs_rsu:
                    result = strategy.step(state, rsu_xy[0], rsu_xy[1])
                else:
                    result = strategy.step(state)

                writer.writerow([
                    t, vid, density, scenario, strat_name, rsu_id,
                    int(result.transmitted), result.bytes_sent,
                    round(result.position_error, 4), round(result.speed_error, 4),
                    round(result.heading_error, 4), round(result.age_of_information, 4),
                ])
                row_count += 1

    traci.close()
    return row_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N configs (for quick testing)")
    args = parser.parse_args()

    cfgs = sorted(glob.glob(os.path.join(RUN_CONFIGS_DIR, "*.sumocfg")))
    if args.limit:
        cfgs = cfgs[:args.limit]

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "t", "vehicle_id", "density", "scenario", "strategy", "rsu_id",
            "transmitted", "bytes_sent", "position_error", "speed_error",
            "heading_error", "age_of_information",
        ])

        for i, cfg_path in enumerate(cfgs):
            name = os.path.basename(cfg_path).replace(".sumocfg", "")
            scenario, density_str = name.rsplit("_", 1)
            density = int(density_str)
            net_key = SCENARIO_NET_KEY[scenario]

            print(f"[{i + 1}/{len(cfgs)}] {scenario:15s} density={density:<4d} ...", end=" ", flush=True)
            n_rows = run_one_config(cfg_path, scenario, density, net_key, writer)
            f.flush()
            print(f"{n_rows} rows")

    print(f"\nDone. All results in {OUT_CSV}")


if __name__ == "__main__":
    main()
