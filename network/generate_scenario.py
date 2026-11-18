"""
Generates a SUMO route file (.rou.xml) for one (scenario, density) combination.

Two networks are used:
  - straight_road.net.xml   -> "steady_speed" and "lane_change" scenarios
  - intersection.net.xml    -> "accel_decel" and "turning" scenarios

Usage:
    python generate_scenario.py --scenario steady_speed --density 20 --out steady_speed_20.rou.xml
    python generate_scenario.py --scenario lane_change  --density 50 --out lane_change_50.rou.xml
    python generate_scenario.py --scenario accel_decel  --density 10 --out accel_decel_10.rou.xml
    python generate_scenario.py --scenario turning      --density 5  --out turning_5.rou.xml

Densities used in the assignment: 5, 10, 20, 50, 100
Duration is fixed at 300 simulated seconds for every scenario/density.
"""
import argparse
import random

DURATION = 300  # seconds, same for every run so results are comparable

VTYPES = """    <vType id="car" accel="2.6" decel="4.5" length="5" maxSpeed="16.7" sigma="0.5"/>
    <vType id="fast" accel="2.8" decel="4.5" length="5" maxSpeed="20.0" sigma="0.5"/>
    <vType id="slow" accel="1.5" decel="3.5" length="5" maxSpeed="6.0" sigma="0.5"/>
"""

STRAIGHT_ROUTES = {"through": ["road"]}

INTERSECTION_THROUGH_ROUTES = {
    "we": ["w_in", "e_out"],
    "ew": ["e_in", "w_out"],
    "ns": ["n_in", "s_out"],
    "sn": ["s_in", "n_out"],
}

INTERSECTION_TURN_ROUTES = {
    "w_n": ["w_in", "n_out"],
    "w_s": ["w_in", "s_out"],
    "n_e": ["n_in", "e_out"],
    "n_w": ["n_in", "w_out"],
    "e_n": ["e_in", "n_out"],
    "e_s": ["e_in", "s_out"],
    "s_e": ["s_in", "e_out"],
    "s_w": ["s_in", "w_out"],
}


def depart_times(density, seed):
    rng = random.Random(seed)
    # Spread departures across the full duration so higher densities don't
    # all pile up at t=0 -- keeps "density" meaning concurrent traffic load,
    # not a startup burst.
    times = sorted(rng.uniform(0, DURATION * 0.9) for _ in range(density))
    return times


def build_steady_speed(density, seed):
    times = depart_times(density, seed)
    body = ['    <route id="through" edges="road"/>']
    for i, t in enumerate(times):
        body.append(f'    <vehicle id="v{i}" type="car" route="through" depart="{t:.2f}"/>')
    return body


def build_lane_change(density, seed):
    rng = random.Random(seed)
    times = depart_times(density, seed)
    body = ['    <route id="through" edges="road"/>']
    for i, t in enumerate(times):
        # 1 in 5 vehicles is a deliberately slow "obstacle" -- forces the
        # fast majority to change lanes to overtake it.
        vtype = "slow" if i % 5 == 0 else "fast"
        body.append(f'    <vehicle id="v{i}" type="{vtype}" route="through" depart="{t:.2f}"/>')
    return body


def build_accel_decel(density, seed):
    rng = random.Random(seed)
    times = depart_times(density, seed)
    body = []
    for name, edges in INTERSECTION_THROUGH_ROUTES.items():
        body.append(f'    <route id="{name}" edges="{" ".join(edges)}"/>')
    route_names = list(INTERSECTION_THROUGH_ROUTES.keys())
    for i, t in enumerate(times):
        route = rng.choice(route_names)
        body.append(f'    <vehicle id="v{i}" type="car" route="{route}" depart="{t:.2f}"/>')
    return body


def build_turning(density, seed):
    rng = random.Random(seed)
    times = depart_times(density, seed)
    body = []
    for name, edges in INTERSECTION_TURN_ROUTES.items():
        body.append(f'    <route id="{name}" edges="{" ".join(edges)}"/>')
    route_names = list(INTERSECTION_TURN_ROUTES.keys())
    for i, t in enumerate(times):
        route = rng.choice(route_names)
        body.append(f'    <vehicle id="v{i}" type="car" route="{route}" depart="{t:.2f}"/>')
    return body


BUILDERS = {
    "steady_speed": build_steady_speed,
    "lane_change": build_lane_change,
    "accel_decel": build_accel_decel,
    "turning": build_turning,
}

NETWORKS = {
    "steady_speed": "straight_road.net.xml",
    "lane_change": "straight_road.net.xml",
    "accel_decel": "intersection.net.xml",
    "turning": "intersection.net.xml",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True, choices=BUILDERS.keys())
    parser.add_argument("--density", required=True, type=int, help="Number of vehicles, e.g. 5/10/20/50/100")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", required=True, help="Output .rou.xml path")
    args = parser.parse_args()

    body = BUILDERS[args.scenario](args.density, args.seed)

    with open(args.out, "w") as f:
        f.write("<routes>\n")
        f.write(VTYPES)
        f.write("\n".join(body))
        f.write("\n</routes>\n")

    print(f"Wrote {args.out}  (scenario={args.scenario}, density={args.density})")
    print(f"Use with network: {NETWORKS[args.scenario]}")


if __name__ == "__main__":
    main()
