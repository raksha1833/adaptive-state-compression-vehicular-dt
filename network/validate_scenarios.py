import os
import sys
import statistics as stats

if "SUMO_HOME" not in os.environ:
    import sumo
    os.environ["SUMO_HOME"] = os.path.dirname(sumo.__file__)
sys.path.append(os.path.join(os.environ["SUMO_HOME"], "tools"))
import traci  # noqa: E402
import sumolib  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def heading_diff(a, b):
    # smallest signed difference between two compass headings, handling 0/360 wraparound
    d = (b - a + 180) % 360 - 180
    return abs(d)


def run_and_measure(cfg):
    traci.start([sumolib.checkBinary("sumo"), "-c", cfg, "--no-step-log", "true"])

    accels = []
    speeds = []
    lane_changes = 0
    last_lane = {}
    first_heading = {}
    last_heading = {}

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        for vid in traci.vehicle.getIDList():
            h = traci.vehicle.getAngle(vid)
            if vid not in first_heading:
                first_heading[vid] = h
            last_heading[vid] = h

            accels.append(traci.vehicle.getAcceleration(vid))
            speeds.append(traci.vehicle.getSpeed(vid))
            lane = traci.vehicle.getLaneID(vid)
            if vid in last_lane and last_lane[vid] != lane:
                lane_changes += 1
            last_lane[vid] = lane

    traci.close()

    # per-vehicle heading change (start of trip vs end of trip) -- this is what
    # actually tells us whether a vehicle turned, unlike pooling instantaneous
    # headings across vehicles going in different compass directions.
    per_vehicle_turn = [heading_diff(first_heading[v], last_heading[v]) for v in first_heading]
    turned_fraction = sum(1 for d in per_vehicle_turn if d > 45) / len(per_vehicle_turn) if per_vehicle_turn else 0

    return {
        "avg_heading_change_per_vehicle": round(stats.mean(per_vehicle_turn), 1) if per_vehicle_turn else 0,
        "fraction_of_vehicles_that_turned": round(turned_fraction, 2),
        "accel_stdev": round(stats.pstdev(accels), 2) if len(accels) > 1 else 0,
        "avg_speed": round(stats.mean(speeds), 2) if speeds else 0,
        "lane_changes": lane_changes,
        "vehicle_count": len(first_heading),
    }


if __name__ == "__main__":
    for scenario in ["steady_speed", "lane_change", "accel_decel", "turning"]:
        cfg = os.path.join(HERE, "run_configs", f"{scenario}_20.sumocfg")
        result = run_and_measure(cfg)
        print(f"{scenario:15s} -> {result}")
