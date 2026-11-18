from common import StepResult, compute_errors, extrapolate, heading_diff
import math

RAW_BYTES = 24  # full-precision packet, same as Raw -- the saving comes from *skipping* steps

THRESHOLDS = dict(pos=1.0, speed=0.5, heading=5.0, accel=0.5)


class EventTriggeredStrategy:
    """Only transmit when position, speed, heading, or acceleration has moved
    past its threshold since the last transmitted update."""

    def __init__(self, thresholds=None):
        self.thresholds = thresholds or THRESHOLDS
        self.last_sent = None

    def _should_transmit(self, true_state):
        if self.last_sent is None:
            return True
        # Compare against where the RSU would PREDICT the vehicle to be
        # (constant-velocity extrapolation from the last sent state), not the
        # raw last-sent coordinates. A vehicle cruising steadily covers many
        # meters every second from motion alone -- that's not "an event", it's
        # exactly what the prediction already accounts for. Only a deviation
        # from the prediction (braking, turning, etc.) should count.
        predicted = extrapolate(self.last_sent, true_state.t)
        dpos = math.hypot(true_state.x - predicted.x, true_state.y - predicted.y)
        dspeed = abs(true_state.speed - self.last_sent.speed)
        dheading = heading_diff(self.last_sent.heading, true_state.heading)
        daccel = abs(true_state.accel - self.last_sent.accel)
        return (dpos > self.thresholds["pos"] or dspeed > self.thresholds["speed"]
                or dheading > self.thresholds["heading"] or daccel > self.thresholds["accel"])

    def step(self, true_state):
        transmit = self._should_transmit(true_state)
        if transmit:
            self.last_sent = true_state

        twin_state = extrapolate(self.last_sent, true_state.t)
        pos_err, spd_err, hdg_err = compute_errors(true_state, twin_state)
        aoi = true_state.t - self.last_sent.t

        return StepResult(
            t=true_state.t, transmitted=transmit, bytes_sent=RAW_BYTES if transmit else 0,
            position_error=pos_err, speed_error=spd_err, heading_error=hdg_err,
            age_of_information=aoi,
        )
