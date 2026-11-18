from common import (
    StepResult, VehicleState, compute_errors, extrapolate, heading_diff,
    quantize_value, dequantize_value, quantized_bytes, FIELD_RANGES,
)

# Mode classification: a vehicle is "maneuvering" if it's accelerating/braking
# hard or turning; otherwise it's "stable". See design_spec.md.
MANEUVER_ACCEL_CUTOFF = 1.5   # m/s^2
MANEUVER_HEADING_CUTOFF = 5.0  # degrees change in the last ~1s

MODES = {
    "stable": dict(
        thresholds=dict(pos=2.0, speed=1.0, heading=10.0, accel=1.0),  # 2x base
        bits=8,
        freshness_floor=2.0,
    ),
    "maneuvering": dict(
        thresholds=dict(pos=1.0, speed=0.5, heading=5.0, accel=0.5),  # base
        bits=16,
        freshness_floor=0.5,
    ),
}


class AdaptiveStrategy:
    """Combines event-triggering, quantization, and a freshness floor, all
    tuned by whether the vehicle is currently 'stable' or 'maneuvering'."""

    def __init__(self):
        self.last_sent = None
        self.prev_heading = None

    def _classify(self, true_state):
        heading_change = heading_diff(self.prev_heading, true_state.heading) if self.prev_heading is not None else 0.0
        maneuvering = abs(true_state.accel) > MANEUVER_ACCEL_CUTOFF or heading_change > MANEUVER_HEADING_CUTOFF
        return "maneuvering" if maneuvering else "stable"

    def _should_transmit(self, true_state, cfg):
        if self.last_sent is None:
            return True
        predicted = extrapolate(self.last_sent, true_state.t)
        dpos = ((true_state.x - predicted.x) ** 2 + (true_state.y - predicted.y) ** 2) ** 0.5
        dspeed = abs(true_state.speed - self.last_sent.speed)
        dheading = heading_diff(self.last_sent.heading, true_state.heading)
        daccel = abs(true_state.accel - self.last_sent.accel)
        age = true_state.t - self.last_sent.t
        t = cfg["thresholds"]
        return (dpos > t["pos"] or dspeed > t["speed"] or dheading > t["heading"]
                or daccel > t["accel"] or age >= cfg["freshness_floor"])

    def step(self, true_state, rsu_x, rsu_y):
        mode = self._classify(true_state)
        self.prev_heading = true_state.heading
        cfg = MODES[mode]

        transmit = self._should_transmit(true_state, cfg)
        bytes_sent = 0

        if transmit:
            bits = cfg["bits"]
            dx, dy = true_state.x - rsu_x, true_state.y - rsu_y
            qx, sx = quantize_value(dx, *FIELD_RANGES["pos"], bits)
            qy, sy = quantize_value(dy, *FIELD_RANGES["pos"], bits)
            qspeed, ss = quantize_value(true_state.speed, *FIELD_RANGES["speed"], bits)
            qheading, sh = quantize_value(true_state.heading, *FIELD_RANGES["heading"], bits)
            qaccel, sa = quantize_value(true_state.accel, *FIELD_RANGES["accel"], bits)

            self.last_sent = VehicleState(
                vehicle_id=true_state.vehicle_id,
                t=true_state.t,
                x=dequantize_value(qx, FIELD_RANGES["pos"][0], sx) + rsu_x,
                y=dequantize_value(qy, FIELD_RANGES["pos"][0], sy) + rsu_y,
                speed=dequantize_value(qspeed, FIELD_RANGES["speed"][0], ss),
                heading=dequantize_value(qheading, FIELD_RANGES["heading"][0], sh),
                accel=dequantize_value(qaccel, FIELD_RANGES["accel"][0], sa),
            )
            bytes_sent = quantized_bytes(bits)

        twin_state = extrapolate(self.last_sent, true_state.t)
        pos_err, spd_err, hdg_err = compute_errors(true_state, twin_state)
        aoi = true_state.t - self.last_sent.t

        return StepResult(
            t=true_state.t, transmitted=transmit, bytes_sent=bytes_sent,
            position_error=pos_err, speed_error=spd_err, heading_error=hdg_err,
            age_of_information=aoi, mode=mode,
        )
