"""
Phase 3: roadside units (RSUs) + "which RSU is closest to each car".

What this script does, in plain words:
  1. Places fixed RSUs on the map (3 along the straight road, 1 on each arm
     of the crossroads).
  2. Runs one SUMO setup (a .sumocfg file) and, every simulated second, reads
     each car's true position, speed, heading and acceleration (via TraCI).
  3. For every car at every second, works out which RSU is nearest and how far
     away it is.
  4. Saves everything to a CSV file -- this is the "truth" the compression
     strategies in later phases will be compared against.

Usage -- run from the folder that holds this file, the two .net.xml maps and
the run_configs folder (your phase-2 folder):
    python extract_state_rsu.py --cfg run_configs/turning_20.sumocfg
    python extract_state_rsu.py --cfg run_configs/steady_speed_20.sumocfg --out my_states.csv

--net is optional: the script reads which map the .sumocfg uses by itself.
(The full repo layout also works: maps in network/, this file in traci_scripts/.)
"""
import argparse
import csv
import math
import os
import sys
import xml.etree.ElementTree as ET
from collections import Counter

if "SUMO_HOME" not in os.environ:
    import sumo
    os.environ["SUMO_HOME"] = os.path.dirname(sumo.__file__)
sys.path.append(os.path.join(os.environ["SUMO_HOME"], "tools"))
import traci  # noqa: E402
import sumolib  # noqa: E402

# RSU coordinates below are in the ORIGINAL design coordinates (the ones used
# when the maps were drawn: road centre / crossroads centre = (0, 0)).
# netconvert silently shifts a map's internal coordinates so nothing is negative
# (see netOffset in the .net.xml <location> tag), and traci.vehicle.getPosition()
# returns positions in that SHIFTED system. Get this wrong and every RSU distance
# is off by a constant, silently. So we read the offset from the map file itself
# and apply it to the RSU positions below.
RSU_DESIGN_POSITIONS = {
    "straight_road": [
        {"id": "RSU_0", "x": 0, "y": 0},
        {"id": "RSU_1", "x": 500, "y": 0},
        {"id": "RSU_2", "x": 1000, "y": 0},
    ],
    "intersection": [
        {"id": "RSU_N", "x": 0, "y": 150},
        {"id": "RSU_S", "x": 0, "y": -150},
        {"id": "RSU_E", "x": 150, "y": 0},
        {"id": "RSU_W", "x": -150, "y": 0},
    ],
}

MAP_FILENAMES = {
    "straight_road": "straight_road.net.xml",
    "intersection": "intersection.net.xml",
}

HERE = os.path.dirname(os.path.abspath(__file__))


def find_map(net_key):
    """Look for the map next to this script (phase folder), then in ../network (repo)."""
    name = MAP_FILENAMES[net_key]
    for folder in (HERE, os.path.join(os.path.dirname(HERE), "network")):
        path = os.path.join(folder, name)
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        f"Could not find {name}. Put it in the same folder as this script "
        f"(or in a 'network' folder one level up)."
    )


def detect_net_key(cfg_path):
    """Read the .sumocfg and work out which of our two maps it uses."""
    node = ET.parse(cfg_path).getroot().find("./input/net-file")
    if node is None:
        return None
    base = os.path.basename(node.get("value"))
    for key, name in MAP_FILENAMES.items():
        if base == name:
            return key
    return None


def map_offset(net_key):
    return sumolib.net.readNet(find_map(net_key)).getLocationOffset()


def resolve_rsu_positions(net_key):
    offset_x, offset_y = map_offset(net_key)
    return [
        {"id": rsu["id"], "x": rsu["x"] + offset_x, "y": rsu["y"] + offset_y}
        for rsu in RSU_DESIGN_POSITIONS[net_key]
    ]


def nearest_rsu(x, y, rsus):
    best_id, best_dist = None, float("inf")
    for rsu in rsus:
        d = math.hypot(x - rsu["x"], y - rsu["y"])
        if d < best_dist:
            best_id, best_dist = rsu["id"], d
    return best_id, round(best_dist, 2)


def print_rsu_table(net_key):
    offset_x, offset_y = map_offset(net_key)
    print(f"Map: {net_key}  (SUMO shifted this map's coordinates by x+{offset_x:g}, y+{offset_y:g})")
    print(f"  {'RSU':8s} {'designed at':>16s}   {'actually at (what TraCI uses)':>30s}")
    for design, actual in zip(RSU_DESIGN_POSITIONS[net_key], resolve_rsu_positions(net_key)):
        d = f"({design['x']:g}, {design['y']:g})"
        a = f"({actual['x']:g}, {actual['y']:g})"
        print(f"  {design['id']:8s} {d:>16s}   {a:>30s}")
    print()


def run(cfg, net_key, out_csv):
    rsus = resolve_rsu_positions(net_key)
    print_rsu_table(net_key)
    traci.start([sumolib.checkBinary("sumo"), "-c", cfg, "--no-step-log", "true"])

    rows = []
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        t = traci.simulation.getTime()
        for vid in traci.vehicle.getIDList():
            x, y = traci.vehicle.getPosition(vid)
            speed = traci.vehicle.getSpeed(vid)
            heading = traci.vehicle.getAngle(vid)
            accel = traci.vehicle.getAcceleration(vid)
            rsu_id, dist = nearest_rsu(x, y, rsus)
            rows.append([t, vid, x, y, speed, heading, accel, rsu_id, dist])

    traci.close()

    out_dir = os.path.dirname(os.path.abspath(out_csv))
    os.makedirs(out_dir, exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["t", "vehicle_id", "x", "y", "speed", "heading", "accel", "rsu_id", "dist_to_rsu"])
        writer.writerows(rows)

    print(f"\nLogged {len(rows)} records (one row = one car at one second) to {out_csv}")

    print("\nHow many of those rows each RSU is responsible for:")
    for rsu_id, count in sorted(Counter(r[7] for r in rows).items()):
        print(f"  {rsu_id}: {count}")

    if rows:
        first_car = rows[0][1]
        print(f"\nExample - the first car ({first_car}) switches to a new nearest RSU like this:")
        previous = None
        for r in rows:
            if r[1] == first_car and r[7] != previous:
                print(f"  t={r[0]:g}s  at map position ({r[2]:.0f}, {r[3]:.0f})  ->  nearest RSU is {r[7]}")
                previous = r[7]
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cfg", required=True, help="a .sumocfg file, e.g. run_configs/turning_20.sumocfg")
    parser.add_argument("--net", choices=RSU_DESIGN_POSITIONS.keys(), default=None,
                        help="optional; detected from the .sumocfg when left out")
    parser.add_argument("--out", default=None, help="CSV to write (default: states_<config name>.csv)")
    args = parser.parse_args()

    detected = detect_net_key(args.cfg)
    if args.net and detected and args.net != detected:
        parser.error(f"--net {args.net} does not match this config, which uses the '{detected}' map")
    net_key = args.net or detected
    if net_key is None:
        parser.error("could not tell which map this config uses; add --net straight_road or --net intersection")

    out_csv = args.out or f"states_{os.path.splitext(os.path.basename(args.cfg))[0]}.csv"
    run(args.cfg, net_key, out_csv)
