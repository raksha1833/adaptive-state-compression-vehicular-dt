"""
Generates all 20 (scenario x density) run configs for the experiment matrix:
4 scenarios x 5 densities = 20 combinations.

Run from anywhere:  python network/generate_all.py
It (re)creates network/run_configs/ with a .rou.xml and .sumocfg for every
combination, ready to feed into experiments/experiment_runner.py.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

DENSITIES = [5, 10, 20, 50, 100]
SCENARIOS = {
    "steady_speed": "straight_road.net.xml",
    "lane_change": "straight_road.net.xml",
    "accel_decel": "intersection.net.xml",
    "turning": "intersection.net.xml",
}

OUT_DIR = os.path.join(HERE, "run_configs")

SUMOCFG_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <input>
        <net-file value="../{net}"/>
        <route-files value="{route_file}"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="300"/>
    </time>
</configuration>
"""


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for scenario, net in SCENARIOS.items():
        for density in DENSITIES:
            name = f"{scenario}_{density}"
            route_path = os.path.join(OUT_DIR, f"{name}.rou.xml")
            cfg_path = os.path.join(OUT_DIR, f"{name}.sumocfg")

            subprocess.run(
                [sys.executable, os.path.join(HERE, "generate_scenario.py"),
                 "--scenario", scenario, "--density", str(density),
                 "--out", route_path],
                check=True,
            )

            with open(cfg_path, "w") as f:
                f.write(SUMOCFG_TEMPLATE.format(net=net, route_file=f"{name}.rou.xml"))

    print(f"\nGenerated {len(SCENARIOS) * len(DENSITIES)} run configs in {OUT_DIR}")
    print("Each has a matching .rou.xml and .sumocfg -- point your experiment runner at the .sumocfg files.")


if __name__ == "__main__":
    main()
