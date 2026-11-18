from common import StepResult, compute_errors

RAW_BYTES = 24  # 4 bytes each for x, y, speed, heading, accel + 4-byte header/id


class RawStrategy:
    """Baseline: transmit the complete state, every timestep, full precision."""

    def __init__(self):
        self.last_sent = None

    def step(self, true_state):
        self.last_sent = true_state  # exact copy -- no loss at all
        pos_err, spd_err, hdg_err = compute_errors(true_state, self.last_sent)
        return StepResult(
            t=true_state.t, transmitted=True, bytes_sent=RAW_BYTES,
            position_error=pos_err, speed_error=spd_err, heading_error=hdg_err,
            age_of_information=0.0,
        )
