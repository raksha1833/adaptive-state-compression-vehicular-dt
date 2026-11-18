"""
EXTRA, kept separate from the submitted results.

The project brief says Adaptive should react to "acceleration, braking, lane
changes, or junction movements". The submitted Adaptive strategy reacts to strong
acceleration/braking and to heading changes (which catches junction turns), but
it does not look at lane changes directly.

This variant is identical to Adaptive except that a lane change also counts as
"maneuvering". It is a subclass, so adaptive.py itself is untouched.
The experiment runner tells it about a lane change by setting `lane_changed`
before every step() call.
"""
from adaptive import AdaptiveStrategy


class AdaptiveLaneAwareStrategy(AdaptiveStrategy):
    def __init__(self):
        super().__init__()
        self.lane_changed = False  # set by the runner before each step()

    def _classify(self, true_state):
        mode = super()._classify(true_state)
        return "maneuvering" if self.lane_changed else mode
