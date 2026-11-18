# Adaptive State Compression for Communication-Efficient Vehicular Digital Twins

Cloud Computing course project. It compares five ways for vehicles to send their
state (position, speed, heading, acceleration) to a roadside unit (RSU) that keeps a
digital twin of each car, and asks whether adapting the compression to how a car is
driving can cut V2I communication overhead without losing meaningful twin accuracy
or freshness. Everything runs in a SUMO traffic simulation controlled from Python
through TraCI.

Parameter choices and field definitions: [`design_spec.md`](design_spec.md).
The written report: [`report/report.pdf`](report/report.pdf).

## Headline result

All 20 setups (4 driving situations x 5 traffic densities), 300 simulated seconds each:

| Strategy | % of raw bytes | Compression | Position error (m) | Peak AoI (s) | Packets delivered* | Max vehicles per RSU* |
|---|---|---|---|---|---|---|
| Raw (baseline) | 100% | 1.00:1 | 0 | 0 | 95.7% | 10 |
| Quantization (32-bit) | 100% | 1.00:1 | 0 | 0 | 95.7% | 10 |
| Quantization (16-bit) | 58.3% | 1.71:1 | 0.005 | 0 | 99.8% | 17 |
| Delta encoding | 58.3% | 1.71:1 | 0.001 | 0 | 99.8% | 17 |
| Quantization (12-bit) | 50.0% | 2.00:1 | 0.069 | 0 | 100% | 20 |
| Event-triggered | 65.5% | 1.53:1 | 0.092 | 44 | 98.8% | 15 |
| Quantization (8-bit) | 37.5% | 2.67:1 | 1.334 | 0 | 100% | 27 |
| **Adaptive** | **26.7%** | **3.74:1** | **1.218** | **1** | **100%** | **39** |

\* Under an *assumed* budget of 250 bytes/sec per RSU (see "Metrics" below).

Adaptive uses 73% less data than Raw, keeps worst-case staleness to 1 second
(Event-triggered: 44 s), and lets one RSU support about 3.9 times as many vehicles.
It combines event-triggering with quantization that changes with driving mode,
instead of applying one fixed setting everywhere.

### By driving situation

| Situation | Adaptive: % of raw bytes | Adaptive: position error (m) | Event-triggered: % of raw bytes | Event-triggered: peak AoI (s) |
|---|---|---|---|---|
| Constant speed | 25.3% | 1.373 | 71.2% | 10 |
| Acceleration / deceleration | 27.8% | 1.194 | 63.9% | 40 |
| Junction / turning | 29.3% | 1.059 | 64.2% | 44 |
| Lane changing | 25.2% | 1.231 | 63.4% | 29 |

Adaptive is the cheapest strategy in every situation, and spends the most in
junction turns, where cars manoeuvre most. Full tables for all strategies:
`analysis/results_by_scenario.csv` and `analysis/results_by_density.csv`.

## Repo structure

```
network/             SUMO road networks, traffic generation, all 20 run configs
  run_configs/       .rou.xml + .sumocfg for every (situation, density) pair
traci_scripts/       reads true car states from SUMO + nearest-RSU assignment
strategies/          the 5 strategies + shared RSU reconstruction logic
experiments/         experiment_runner.py (main) and lane_aware_experiment.py (extra)
results/             all_results.csv (~410k rows) and lane_aware_comparison.csv (extra)
analysis/            plots.py, verify_results.py, results_by_scenario.py
  plots/             6 charts
report/              generate_report.py and the final report.pdf
design_spec.md       field definitions, strategy parameters, thresholds
requirements.txt     pinned Python packages (SUMO itself comes from pip)
```

## Setup

Python 3.10+ is required. SUMO is installed by pip (the `eclipse-sumo` package), so
no separate SUMO installer is needed, and no environment variables must be set.

Windows (PowerShell), from the repo folder:

```
python -m venv .venv
.venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

If PowerShell refuses to run `Activate.ps1`, run
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first.

Linux / macOS / WSL:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Check it worked:

```
sumo --version
python -c "import traci, sumolib, pandas, matplotlib; print('ok')"
```

Tested on Windows (PowerShell, Python 3.14) and on Linux (Python 3.12).

## Running everything, in order

Run from the repo root with the virtual environment active. SUMO prints a few
harmless "Retrying in 1 seconds" lines at startup.

| # | Command | What it does | You should see |
|---|---|---|---|
| 1 | `python network/generate_all.py` | (optional) rebuilds the 20 traffic setups, already included | `Generated 20 run configs` |
| 2 | `python network/validate_scenarios.py` | checks each driving situation behaves as intended | only `turning` shows `1.0` cars that turned |
| 3 | `python traci_scripts/extract_state_rsu.py --cfg network/run_configs/turning_20.sumocfg --out results/turning_20_states.csv` | logs true car states with nearest RSU for one setup | `Logged 1185 records` |
| 4 | `python strategies/test_strategies.py results/turning_20_states.csv intersection` | compares the strategies on that one setup | Raw 1422 bytes, Adaptive about 413 |
| 5 | `python experiments/experiment_runner.py` | **main experiment**: all 20 setups x all strategies | 20 progress lines, then `Done` (1-3 min) |
| 6 | `python analysis/plots.py` | computes every metric, writes 2 tables + 6 charts | two tables printed |
| 7 | `python analysis/verify_results.py` | checks the results (see below) | `ALL SANITY CHECKS PASSED` |
| 8 | `python analysis/results_by_scenario.py` | results per driving situation and per density | 4 tables |
| 9 | `python experiments/lane_aware_experiment.py` | (extra) lane-change-aware Adaptive | `SAME (submitted results ...)` |

Optional: to rebuild the PDF, type your name, roll number, group, mentor and date
into the five `FILL THESE IN` lines at the top of `report/generate_report.py`, then
run `python report/generate_report.py` (this overwrites `report/report.pdf`).

To watch a setup run visually: `sumo-gui -c network/run_configs/turning_20.sumocfg`,
then press the green play button.

## Metrics: every item in the project brief, and where to find it

| Metric from the brief | Where |
|---|---|
| Total data transmitted (bytes) | `analysis/summary_by_strategy.csv` (`total_bytes`) |
| Communication overhead (bytes/sec/vehicle) | `summary_by_strategy.csv`; `plots/overhead_vs_density.png` |
| Packet transmission rate | `summary_by_strategy.csv` (`packets_per_sec_per_vehicle`, `pct_transmitted`) |
| Compression ratio | `summary_by_strategy.csv` (`compression_ratio`, `pct_of_raw_bytes`) |
| V2I channel utilization | `analysis/bandwidth_analysis.csv`; `plots/channel_utilization.png` |
| Average Age of Information | `summary_by_strategy.csv` (`avg_aoi`); `plots/aoi_vs_density.png` |
| Peak Age of Information | `summary_by_strategy.csv` (`peak_aoi`); `plots/aoi_vs_density.png` |
| Position / speed / heading error | `summary_by_strategy.csv`; `plots/tradeoff.png` |
| Packet delivery ratio | `bandwidth_analysis.csv` (`packet_delivery_ratio_pct`) |
| Max supported vehicles under a bandwidth constraint | `bandwidth_analysis.csv` (`max_vehicles_per_rsu`); `plots/max_vehicles.png` |
| Freshness-accuracy-communication trade-off | `plots/tradeoff.png` |
| Results per driving situation / per density | `analysis/results_by_scenario.csv`, `analysis/results_by_density.csv` |

How they are defined (details at the top of `analysis/plots.py`): one row of the
results is one car on the road for one simulated second, so "per vehicle" means per
car *while it is on the road*. For the bandwidth metrics, each RSU is given a fixed
budget of bytes per second for twin-sync traffic. The budgets (250, 500 and 1000
bytes/sec) are **assumptions** sized to this small simulation; edit
`BANDWIDTH_BUDGETS` in `analysis/plots.py` to try others. Utilization = bytes offered
to an RSU in one second / budget. Packet delivery ratio = packets that fit in the
budget / packets sent (excess packets dropped evenly). Max supported vehicles =
budget / bytes-per-second-per-vehicle.

## Verifying the results

`python analysis/verify_results.py` runs 21 sanity checks that need no reference
numbers - for example: Raw sends 24 bytes every second with zero error; each
quantization level sends exactly the packet size its format implies; a quantizer is
never wrong by more than half a step (8-bit position error peaks at 2.70 m against a
limit of 2.77 m); Age of Information is 0 exactly when a packet is sent; Adaptive never
goes 2 seconds without an update. It then compares 11 headline numbers with the
reference results. Corrupting the results file in five different ways made it fail
each time, so the checks do catch errors. If the reference numbers differ but the
sanity checks pass, the usual cause is a different SUMO version (pinned: 1.27.1).

## Extra: lane-change-aware Adaptive

The brief lists lane changes as a trigger for Adaptive. The submitted Adaptive reacts
to strong acceleration/braking and to heading changes (which catches junction turns),
but not to lane changes directly. `experiments/lane_aware_experiment.py` tests a
variant that also treats a lane change as manoeuvring. It made almost no difference
(26.8% vs 26.7% of raw bytes; 1.208 m vs 1.218 m error), because only 318 lane changes
occurred in about 51,000 car-seconds. This extra run does not touch
`results/all_results.csv`; it checks that its own `adaptive` numbers reproduce the
submitted ones exactly.

## Two bugs worth knowing about (and why the fixes matter)

- **Coordinate offset**: `netconvert` shifts a network's internal coordinates so
  nothing is negative - it does not keep the coordinates used to design the network.
  RSU positions are defined in the design coordinates and converted at load time with
  `sumolib`'s `getLocationOffset()` (see `traci_scripts/extract_state_rsu.py`).
- **Event-trigger reference point**: comparing a car's new position with its last
  *transmitted* position does not work - a car at 15 m/s moves ~15 m every second,
  which always exceeds a 1 m threshold. The threshold instead compares against where
  the RSU would *predict* the car to be (constant-velocity extrapolation) - see
  `_should_transmit` in `strategies/event_triggered.py` and `strategies/adaptive.py`.

## Known limitations

- The bandwidth budgets are assumptions, not measurements of a real V2I link, and the
  utilization / packet-delivery results depend on them.
- Packet delivery is analysed on top of the logged traffic: dropped packets are not fed
  back into the twin, so the error and Age-of-Information figures assume every packet a
  strategy sends is received. There is no radio model; "nearest RSU" means distance only.
- "Max supported vehicles" is calculated from the average per-vehicle rate. The busiest
  RSU in our tests held 22 cars at once, so larger values are extrapolations.
- The Raw packet is 24 bytes: x, y, speed, heading, acceleration plus a 4-byte header that
  stands in for vehicle id and timestamp; the timestamp is not a separate field.
- Quantization field ranges (speed, heading, accel, position relative to RSU) are fixed
  assumptions documented in `design_spec.md` (`FIELD_RANGES` in `strategies/common.py`).
- One random seed per setup; at most 100 vehicles on two small road layouts.
- SciPy is installed because the project brief lists it, but no script uses it.
