from common import StepResult, compute_errors, signed_heading_diff, quantize_value, dequantize_value, quantized_bytes

# Deltas over a single ~1s timestep are small, so a 16-bit fixed-point value
# per field is precise enough to be effectively lossless while using less
# than half the bytes of sending full 32-bit floats (see DELTA_BYTES below).
DELTA_RANGES = {
    "pos": (-50, 50),       # meters moved per step (comfortably covers max speed x step)
    "speed": (-10, 10),     # m/s change per step
    "heading": (-180, 180), # degrees change per step
    "accel": (-10, 10),     # m/s^2 change per step
}
DELTA_BITS = 16
DELTA_BYTES = quantized_bytes(DELTA_BITS)  # 5 fields x 16-bit + header = 14 bytes


class DeltaStrategy:
    """Send the change since the last transmitted state instead of absolute values."""

    def __init__(self):
        self.last_sent = None

    def step(self, true_state):
        if self.last_sent is None:
            reconstructed = true_state  # first packet has nothing to delta against
        else:
            dx = true_state.x - self.last_sent.x
            dy = true_state.y - self.last_sent.y
            dspeed = true_state.speed - self.last_sent.speed
            dheading = signed_heading_diff(self.last_sent.heading, true_state.heading)
            daccel = true_state.accel - self.last_sent.accel

            qx, sx = quantize_value(dx, *DELTA_RANGES["pos"], DELTA_BITS)
            qy, sy = quantize_value(dy, *DELTA_RANGES["pos"], DELTA_BITS)
            qspeed, ss = quantize_value(dspeed, *DELTA_RANGES["speed"], DELTA_BITS)
            qheading, sh = quantize_value(dheading, *DELTA_RANGES["heading"], DELTA_BITS)
            qaccel, sa = quantize_value(daccel, *DELTA_RANGES["accel"], DELTA_BITS)

            reconstructed = type(true_state)(
                vehicle_id=true_state.vehicle_id,
                t=true_state.t,
                x=self.last_sent.x + dequantize_value(qx, DELTA_RANGES["pos"][0], sx),
                y=self.last_sent.y + dequantize_value(qy, DELTA_RANGES["pos"][0], sy),
                speed=self.last_sent.speed + dequantize_value(qspeed, DELTA_RANGES["speed"][0], ss),
                heading=(self.last_sent.heading + dequantize_value(qheading, DELTA_RANGES["heading"][0], sh)) % 360,
                accel=self.last_sent.accel + dequantize_value(qaccel, DELTA_RANGES["accel"][0], sa),
            )

        self.last_sent = reconstructed
        pos_err, spd_err, hdg_err = compute_errors(true_state, self.last_sent)
        return StepResult(
            t=true_state.t, transmitted=True, bytes_sent=DELTA_BYTES,
            position_error=pos_err, speed_error=spd_err, heading_error=hdg_err,
            age_of_information=0.0,
        )
