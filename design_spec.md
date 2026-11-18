# Adaptive State Compression — Design Spec

Starting numbers below are reasonable defaults, not fixed. Tune thresholds and bit-depths once you have a few test runs — the tuning process itself is worth a paragraph in your report.

## Vehicle state

Fields tracked per vehicle per timestep, pulled via TraCI:

| Field | TraCI source | Type | Units |
|---|---|---|---|
| vehicle_id | `traci.vehicle.getIDList()` | string | — |
| t | `traci.simulation.getTime()` | float | seconds |
| x, y | `getPosition()` | float | meters |
| speed | `getSpeed()` | float | m/s |
| heading | `getAngle()` | float | degrees (0–360) |
| accel | `getAcceleration()` | float | m/s² |

## Strategy 1 — Raw

Send the full state every timestep as float32 fields. Baseline packet size ≈ 24 bytes (8 for x/y, 4 each for speed, heading, accel, plus a small header/id).

## Strategy 2 — Delta encoding

Send `(x - last_x, y - last_y, speed - last_speed, heading - last_heading, accel - last_accel)` instead of absolute values, every timestep. Only saves bytes if you also quantize the deltas (recommended — deltas are usually small, so they compress well).

## Strategy 3 — Quantization

Map each continuous field to a fixed-size integer. Starting ranges and resulting resolution:

| Field | Assumed range | 8-bit | 12-bit | 16-bit |
|---|---|---|---|---|
| speed | 0–40 m/s | 0.16 m/s | 0.01 m/s | 0.0006 m/s |
| heading | 0–360° | 1.4° | 0.09° | 0.005° |
| accel | −5–5 m/s² | 0.04 m/s² | 0.002 m/s² | 0.0002 m/s² |
| x, y (relative to RSU) | 0–500 m | 2 m | 0.12 m | 0.008 m |

Test all four bit-depths the brief lists (8/12/16/32) and report resolution vs. bytes saved for each.

## Strategy 4 — Event-triggered

Send an update only when at least one of these changes past threshold since the last sent update:

- Δposition > 1.0 m
- Δspeed > 0.5 m/s
- Δheading > 5°
- Δaccel > 0.5 m/s²

## Strategy 5 — Adaptive

Classify each vehicle every timestep:

- **Maneuvering** if `|accel| > 1.5 m/s²` OR heading changed more than 5° in the last 1 second
- **Stable** otherwise

Behavior by mode:

| Mode | Thresholds | Quantization | Freshness floor |
|---|---|---|---|
| Stable | 2× the event-triggered values above | 8-bit | forced update at least every 2s |
| Maneuvering | base event-triggered values | 16-bit | forced update at least every 0.5s |

## RSU-side reconstruction

When no update is received, extrapolate with constant velocity rather than freezing the last value:

```
new_x = last_x + last_speed * cos(last_heading) * dt
new_y = last_y + last_speed * sin(last_heading) * dt
```

Noticeably more accurate than a flat hold, and barely more code.

## Metrics logged per timestep per vehicle

```
t, vehicle_id, density, scenario, strategy,
bytes_sent_this_step, position_error, speed_error,
heading_error, age_of_information
```

## Experiment matrix

5 densities × 4 scenarios × 5 strategies = 100 runs. Suggest ~300 simulated seconds per run — long enough to capture several full maneuvers per scenario.

## Repo structure

```
project-root/
  network/              SUMO .net.xml / .rou.xml per density & scenario
  traci_scripts/
    extract_state.py
  strategies/
    common.py           shared VehicleState dataclass + RSU reconstruction
    raw.py
    delta.py
    quantization.py
    event_triggered.py
    adaptive.py
  experiments/
    run_all.py           sweep runner
  results/                logged CSVs
  analysis/
    plots.py
  report/
  README.md
```

## Shared data interface

```python
from dataclasses import dataclass

@dataclass
class VehicleState:
    vehicle_id: str
    t: float
    x: float
    y: float
    speed: float
    heading: float
    accel: float
```
