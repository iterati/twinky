import math

from control import (
    BasicBitch,
    CircusTent,
    CoiledSpring,
    Confetti,
    FallingSnow,
    Galaxus,
    Groovy,
    RainbowStorm,
    SlidingDoor,
    SpiralTop,
    WiredPattern,
)
from core import Blender
from sim import SimLights

PATTERNS = [BasicBitch, CircusTent, CoiledSpring, Confetti, FallingSnow,
            Galaxus, Groovy, RainbowStorm, SlidingDoor, SpiralTop]
FRAME = 1/16
EFFECTS = ["Flash", "Flicker", "Flitter", "Flux", "Sparkles"]

def quiet(pattern: WiredPattern, streamers: bool=False) -> WiredPattern:
    """Turns the pattern's noisy effects off (and its streamers, unless asked), and saves it as
    configured so a change doesn't randomize it again."""
    for feature in pattern.features:
        for control in feature.controls:
            if (feature.name in EFFECTS and control.name == "Enabled") or (
                    control.name == "Streamers" and not streamers):
                control.set(1)
    pattern.update(set_dirty=False)
    pattern.configured = True
    return pattern

def blender(patterns: list[WiredPattern], start_idx: int=0) -> Blender:
    b = Blender(patterns, SimLights(), start_idx, False)
    b.init(0.0)
    return b

def frames(b: Blender, start: float, end: float):
    """Renders and writes every frame from start to end seconds, yielding each (t, frame)."""
    for k in range(round(start / FRAME), round(end / FRAME)):
        t = k * FRAME
        frame = b.render(t)
        b.write(frame)
        yield t, frame

def in_range(frame) -> bool:
    # a light's layers' weights sum to 1 give or take a rounding error, which its byte rounds away
    return all(math.isfinite(c) and -1e-9 <= c <= 255 + 1e-9 for light in frame for c in light)

def delta(a: bytes, b: bytes) -> float:
    """How far the tree moved between two frames' bytes: the mean absolute change."""
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)

def tree_bytes(b: Blender) -> bytes:
    return b"".join(interface.frames[-1] for interface in b.lights.interfaces)
