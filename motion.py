"""Modulators, ported from Bermuda's src/motion.ts (a15fad7) with its names in snake_case and its
numbers: the waves, the phase that runs at a modulator's period in beats, the phase spread, the
depth and glide. On the tree a link group's member becomes a light's share of the spread: its angle
round the trunk or its height, 0 to 1, so the phase is a wave travelling round or up the tree."""
from dataclasses import dataclass
import math

# The shares of a spread a gliding target keeps its glided wave at, as Bermuda keeps one for each
# member of a link group; a light reads between the two nearest its own
MEMBERS = 128

@dataclass
class Target:
    knob: str  # the address of the knob it moves, as "levels[hexA].affine.turn"
    depth: float
    phase_spread: float = 0.0

@dataclass
class Modulator:
    id: str
    wave: str  # "cos", "tri", "beat", "ramp" or "steps"
    period: float  # in beats
    phase: float = 0.0  # in cycles
    harmonics: tuple[float, float] | None = None  # the beat wave's
    steps: list[float] | None = None  # the steps wave's
    glide: float = 0.0  # in seconds

def wave(m: Modulator, p: float) -> float:
    """A wave's value at phase p (cycles), 0 to 1; cos and tri start at 1 as the Tapestries' sinT and
    sawT did."""
    f = p - math.floor(p)
    if m.wave == "cos":
        return 0.5 + 0.5 * math.cos(2 * math.pi * f)
    if m.wave == "tri":
        return abs(f - 0.5) * 2
    if m.wave == "beat":
        a, b = m.harmonics
        return abs(math.cos(2 * math.pi * f * a) * math.cos(2 * math.pi * f * b) * 0.5 - 0.5)
    if m.wave == "ramp":
        return f
    if m.wave == "steps":
        steps = m.steps
        return steps[min(len(steps) - 1, math.floor(f * len(steps)))]

def follow(start: float | None, to: float, glide: float, dt: float) -> float:
    return to if start is None or glide <= 0 else to + (start - to) * math.exp(-dt / glide)

class Running:
    """One of a modulator's targets as it runs on the tree, motion.ts's advance for one target: the
    modulator's phase, run on by each frame's beats, and with a glide, the glided wave at MEMBERS + 1
    even shares of the spread."""
    def __init__(self, m: Modulator, target: Target):
        self.m = m
        self.target = target
        self.phase = 0.0
        self.smooth: list[float | None] = [None] * (MEMBERS + 1)

    def advance(self, beats: float, dt: float):
        m = self.m
        self.phase = (self.phase + beats / m.period) % 1
        if m.glide > 0:
            for member in range(MEMBERS + 1):
                self.smooth[member] = follow(self.smooth[member], self.raw(member / MEMBERS), m.glide, dt)

    def raw(self, share: float) -> float:
        m = self.m
        return wave(m, self.phase + m.phase + self.target.phase_spread * share)

    def at(self, share: float) -> float:
        """The glided wave at a light's share of the spread, 0 to 1."""
        if self.m.glide <= 0:
            return self.raw(share)
        x = min(1.0, max(0.0, share)) * MEMBERS
        k = min(MEMBERS - 1, math.floor(x))
        a, b = self.smooth[k], self.smooth[k + 1]
        return a + (b - a) * (x - k)

    def offset(self, share: float) -> float:
        """What it adds to its knob at a light's share: its depth either way of the knob's base."""
        return self.target.depth * (2 * self.at(share) - 1)
