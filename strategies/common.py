"""
Shared building blocks for all five strategies: the vehicle state record,
the RSU-side constant-velocity extrapolation, error computation, and the
generic quantize/dequantize helpers used by Quantization and Adaptive.
"""
from dataclasses import dataclass
import math


@dataclass
class VehicleState:
    vehicle_id: str
    t: float
    x: float
    y: float
    speed: float
    heading: float
    accel: float


@dataclass
class StepResult:
    t: float
    transmitted: bool
    bytes_sent: int
    position_error: float
    speed_error: float
    heading_error: float
    age_of_information: float
    mode: str = ""  # only Adaptive fills this in ("stable" / "maneuvering")


def signed_heading_diff(a, b):
    """Signed smallest difference b - a for compass headings (handles 0/360 wraparound)."""
    return (b - a + 180) % 360 - 180


def heading_diff(a, b):
    """Smallest signed difference between two compass headings (handles 0/360 wraparound)."""
    return abs(signed_heading_diff(a, b))


def extrapolate(last_state: VehicleState, t: float) -> VehicleState:
    """RSU-side estimate of the vehicle's state at time t, given the last update
    it actually received. Assumes constant velocity along the last known heading
    rather than freezing the position outright -- SUMO's heading convention is
    0=north (+y), 90=east (+x), clockwise."""
    dt = t - last_state.t
    heading_rad = math.radians(last_state.heading)
    new_x = last_state.x + last_state.speed * math.sin(heading_rad) * dt
    new_y = last_state.y + last_state.speed * math.cos(heading_rad) * dt
    return VehicleState(
        vehicle_id=last_state.vehicle_id,
        t=t,
        x=new_x,
        y=new_y,
        speed=last_state.speed,
        heading=last_state.heading,
        accel=last_state.accel,
    )


def compute_errors(true_state: VehicleState, twin_state: VehicleState):
    position_error = math.hypot(true_state.x - twin_state.x, true_state.y - twin_state.y)
    speed_error = abs(true_state.speed - twin_state.speed)
    heading_error = heading_diff(true_state.heading, twin_state.heading)
    return position_error, speed_error, heading_error


def quantize_value(value, min_val, max_val, bits):
    """Returns (quantized_int, step_size). step_size is needed by dequantize_value."""
    levels = 2 ** bits - 1
    clipped = max(min_val, min(max_val, value))
    step = (max_val - min_val) / levels
    q = round((clipped - min_val) / step)
    return q, step


def dequantize_value(q, min_val, step):
    return min_val + q * step


# Field ranges used by Quantization and Adaptive. Position is relative to the
# vehicle's assigned RSU (not absolute world coordinates) and allowed to be
# negative since a vehicle can be on either side of its RSU.
FIELD_RANGES = {
    "speed": (0, 40),
    "heading": (0, 360),
    "accel": (-5, 5),
    "pos": (-500, 500),
}


def quantized_bytes(bits, num_fields=5, header_bytes=4):
    """Bytes needed to pack num_fields values at the given bit-depth, rounded
    up to a whole byte, plus a small header for vehicle id/timestamp."""
    return -(-bits * num_fields // 8) + header_bytes
