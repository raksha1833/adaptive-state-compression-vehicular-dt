"""
EXTRA experiment - NOT part of the submitted results; it never touches
results/all_results.csv.

Question: does making Adaptive explicitly aware of lane changes (the brief lists
lane changes as a trigger) change the outcome?

It re-runs all 20 configurations once and compares three strategies on the same cars:
    raw                  - the uncompressed baseline
    adaptive             - exactly the submitted Adaptive strategy
    adaptive_lane_aware  - Adaptive, but a lane change also counts as "maneuvering"

Run from the repo root:
    python experiments/lane_aware_experiment.py

Writes results/lane_aware_comparison.csv and prints the comparison. It also
checks that its `adaptive` numbers equal the submitted results, which proves
this extra run did not change the pipeline.
"""
import csv
import glob
import os
from collections import defaultdict

import pandas as pd

# experiment_runner puts strategies/ and traci_scripts/ on the path when imported
from experiment_runner import REPO_ROOT, RUN_CONFIGS_DIR, SCENARIO_NET_KEY, nearest_rsu  # noqa: E402
import traci  # noqa: E402
import sumolib  # noqa: E402
from common import VehicleState  # noqa: E402
from raw import RawStrategy  # noqa: E402
from adaptive import AdaptiveStrategy  # noqa: E402
from adaptive_lane_aware import AdaptiveLaneAwareStrategy  # noqa: E402
from extract_state_rsu import resolve_rsu_positions  # noqa: E402

OUT_CSV = os.path.join(REPO_ROOT, "results", "lane_aware_comparison.csv")
MAIN_RESULTS = os.path.join(REPO_ROOT, "results", "all_results.csv")
STRATEGIES = ["raw", "adaptive", "adaptive_lane_aware"]


def new_stats():
    return dict(rows=0, bytes=0, sent=0, pos=0.0, spd=0.0, hdg=0.0, aoi=0.0, peak_aoi=0.0)


def run_one_config(cfg_path, scenario, net_key, stats, lane_change_counts):
    rsus = resolve_rsu_positions(net_key)
    traci.start([sumolib.checkBinary("sumo"), "-c", cfg_path, "--no-step-log", "true"])
    per_car = {}        # vehicle id -> its own strategy instances
    last_lane = {}      # vehicle id -> (road, lane index) one second ago

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        t = traci.simulation.getTime()
        for vid in traci.vehicle.getIDList():
            if vid not in per_car:
                per_car[vid] = {"raw": RawStrategy(), "adaptive": AdaptiveStrategy(),
                                "adaptive_lane_aware": AdaptiveLaneAwareStrategy()}

            # A lane change = same road, different lane than one second ago.
            road, lane = traci.vehicle.getRoadID(vid), traci.vehicle.getLaneIndex(vid)
            previous = last_lane.get(vid)
            lane_changed = previous is not None and previous[0] == road and previous[1] != lane
            last_lane[vid] = (road, lane)
            if lane_changed:
                lane_change_counts[scenario] += 1
            per_car[vid]["adaptive_lane_aware"].lane_changed = lane_changed

            x, y = traci.vehicle.getPosition(vid)
            state = VehicleState(vehicle_id=vid, t=t, x=x, y=y,
                                 speed=traci.vehicle.getSpeed(vid),
                                 heading=traci.vehicle.getAngle(vid),
                                 accel=traci.vehicle.getAcceleration(vid))
            _, rsu_xy = nearest_rsu(x, y, rsus)

            for name, strategy in per_car[vid].items():
                result = strategy.step(state) if name == "raw" else strategy.step(state, rsu_xy[0], rsu_xy[1])
                for key in (scenario, "ALL"):
                    s = stats[(key, name)]
                    s["rows"] += 1
                    s["bytes"] += result.bytes_sent
                    s["sent"] += int(result.transmitted)
                    s["pos"] += result.position_error
                    s["spd"] += result.speed_error
                    s["hdg"] += result.heading_error
                    s["aoi"] += result.age_of_information
                    s["peak_aoi"] = max(s["peak_aoi"], result.age_of_information)
    traci.close()


def main():
    stats = defaultdict(new_stats)
    lane_change_counts = defaultdict(int)

    cfgs = sorted(glob.glob(os.path.join(RUN_CONFIGS_DIR, "*.sumocfg")))
    for i, cfg_path in enumerate(cfgs, 1):
        scenario = os.path.basename(cfg_path).replace(".sumocfg", "").rsplit("_", 1)[0]
        print(f"[{i}/{len(cfgs)}] {os.path.basename(cfg_path)}", flush=True)
        run_one_config(cfg_path, scenario, SCENARIO_NET_KEY[scenario], stats, lane_change_counts)
    lane_change_counts["ALL"] = sum(lane_change_counts.values())

    rows = []
    for key in ["steady_speed", "lane_change", "accel_decel", "turning", "ALL"]:
        raw_bytes = stats[(key, "raw")]["bytes"]
        for name in STRATEGIES:
            s = stats[(key, name)]
            n = s["rows"]
            rows.append({
                "scenario": key, "strategy": name, "car_seconds": n, "total_bytes": s["bytes"],
                "pct_of_raw_bytes": round(100 * s["bytes"] / raw_bytes, 1),
                "pct_steps_transmitted": round(100 * s["sent"] / n, 1),
                "avg_position_error_m": round(s["pos"] / n, 3),
                "avg_speed_error": round(s["spd"] / n, 3),
                "avg_heading_error_deg": round(s["hdg"] / n, 3),
                "avg_aoi_s": round(s["aoi"] / n, 3), "peak_aoi_s": s["peak_aoi"],
                "lane_changes_seen": lane_change_counts[key],
            })
    comparison = pd.DataFrame(rows)
    comparison.to_csv(OUT_CSV, index=False)

    pd.set_option("display.width", 200)
    cols = ["scenario", "strategy", "pct_of_raw_bytes", "pct_steps_transmitted",
            "avg_position_error_m", "avg_aoi_s", "peak_aoi_s", "lane_changes_seen"]
    print("\n" + comparison[cols].to_string(index=False))

    # Proof that this extra run did not change the pipeline: our `adaptive` must equal the submitted one.
    main_df = pd.read_csv(MAIN_RESULTS)
    submitted = int(main_df[main_df.strategy == "adaptive"].bytes_sent.sum())
    ours = int(stats[("ALL", "adaptive")]["bytes"])
    print(f"\nCheck: this run's `adaptive` total bytes = {ours:,}; submitted results = {submitted:,}  ->  "
          f"{'SAME (the submitted results are untouched and reproduced)' if ours == submitted else 'DIFFERENT - investigate'}")
    print(f"Written to {OUT_CSV}")


if __name__ == "__main__":
    main()
