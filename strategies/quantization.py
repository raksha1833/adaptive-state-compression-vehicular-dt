from common import StepResult, VehicleState, compute_errors, quantize_value, dequantize_value, quantized_bytes, FIELD_RANGES


class QuantizationStrategy:
    """Send the absolute state every step, but each field reduced to `bits` bits.
    RSU position is passed per-step (not fixed at init) since a vehicle's
    nearest RSU can hand off mid-trip."""

    def __init__(self, bits):
        self.bits = bits
        self.bytes_per_update = quantized_bytes(bits)
        self.last_sent = None

    def step(self, true_state, rsu_x, rsu_y):
        dx, dy = true_state.x - rsu_x, true_state.y - rsu_y

        qx, sx = quantize_value(dx, *FIELD_RANGES["pos"], self.bits)
        qy, sy = quantize_value(dy, *FIELD_RANGES["pos"], self.bits)
        qspeed, ss = quantize_value(true_state.speed, *FIELD_RANGES["speed"], self.bits)
        qheading, sh = quantize_value(true_state.heading, *FIELD_RANGES["heading"], self.bits)
        qaccel, sa = quantize_value(true_state.accel, *FIELD_RANGES["accel"], self.bits)

        self.last_sent = VehicleState(
            vehicle_id=true_state.vehicle_id,
            t=true_state.t,
            x=dequantize_value(qx, FIELD_RANGES["pos"][0], sx) + rsu_x,
            y=dequantize_value(qy, FIELD_RANGES["pos"][0], sy) + rsu_y,
            speed=dequantize_value(qspeed, FIELD_RANGES["speed"][0], ss),
            heading=dequantize_value(qheading, FIELD_RANGES["heading"][0], sh),
            accel=dequantize_value(qaccel, FIELD_RANGES["accel"][0], sa),
        )

        pos_err, spd_err, hdg_err = compute_errors(true_state, self.last_sent)
        return StepResult(
            t=true_state.t, transmitted=True, bytes_sent=self.bytes_per_update,
            position_error=pos_err, speed_error=spd_err, heading_error=hdg_err,
            age_of_information=0.0,
        )
