"""Hints of Bermuda's looks on the tree: at about 800 lights it cannot show Bermuda's pictures, so
these are slow, soft-edged shapes in Bermuda's palettes (palette.py), moved by its modulators and
their timing (motion.py), most of them using the angle round the trunk. Each light's brightness is
how much of the shape covers it, so motion glides instead of stepping from light to light. Their
knobs sweep as the Curved knobs of control.py's patterns do, on the hint's clock, so a hint keeps
changing over the minute."""
import math

from pytweening import easeOutBack

from colors import BaseColor, Color
from control import CURVES, DIRECTIONS, BlendFeature, Control, Feature, Option, ToggleControl, WiredPattern
from motion import Modulator, Running, Target, wave
from palette import COSINES, Palette, Vec3, oklch_to_linear, palette_at, stops_from_cosine
from param import Curve, Param, getv
from utils import coverage, mk_bounce, mk_bump

# The stops a cosine preset is sampled at
STOPS = 8
# A slice's share of its slot, the rest dark between
FILL = 0.5
# How far the wash dims at its wave's trough
DIP = 0.6
# The wash's tide: how fast its palette climbs the tree (with Axis round, drifts round it), in
# palettes a beat, how far it wobbles either way round the trunk (round, up the tree), as a share
# of the palette, the wobble turning once in WOBBLE_PERIOD beats, and with Axis round, the
# palette's turns round the trunk for a Span of 1
CLIMB = 1/20
WOBBLE = 0.3
WOBBLE_PERIOD = 9
ROUND = 2
# Slices: with Axis leaned, the arms' turns round the trunk up the tree before their lean; with
# Axis up, how far the rings tilt, in slots either way, for each slot of Lean; and how far the
# palette runs up each slice
TWIST = 1
TILT = 1/4
PALETTE_UP = 0.3
# The hidden field: a star's outer radius, as a share of the lattice's spacing, how deep its points
# are cut, its soft edge (of the base's radius), the share of Twinkles a light sparkles in and how
# sharp a sparkle is, hidden, the sharpness the stars stand solid at, the share of Twinkles a light
# fades in over as the share grows, and how much faster the field turns once revealed
STAR = 0.34
STAR_CUT = 0.45
STAR_EDGE = 0.08
SPARKLES = 0.25
SPARKLE = 4
SOLID = 1/2
SHARE_EDGE = 0.2
FASTER = 1
# The beat wave's harmonics, for a hint's Wave control
HARMONICS = (1, 2)
# How long a hint's clock takes to draw onto the music's beat, in seconds
LOCK = 1.0
# A tick's step, as a share of its beat
TICK = 0.35

PALETTES = [Option(name, name) for name in COSINES]
WAVES = [Option(name, name) for name in ["cos", "tri", "beat"]]
BEATS = [Option(str(v), v) for v in [16, 32, 64]]
# a swept knob's periods: in beats while music plays, so its turns land on bar lines, else seconds
SWEEPS = [Option(str(v), v) for v in [16, 32, 48, 64]]
# a soft edge's width, as a share of the lit part of a slot: at 1 a light is only full at its middle
SOFTNESS = [Option(n, v) for n, v in [("1/2", 1/2), ("3/4", 3/4), ("1", 1)]]

def preset(name: str) -> Palette:
    return Palette(stops_from_cosine(name, STOPS))

def slot(u: float, softness: float) -> tuple[float, int]:
    """For a light at u, counted in slots (slices round the trunk, up it or winding up it), how
    much of its slot's lit part covers it, its edges softness of it wide, and which slot it is in, the
    slots meeting halfway across the dark between."""
    k = math.floor(u + ((1 - FILL) / 2))
    return coverage(u - k, 0, FILL, softness * FILL, wrap=False), k

def tick(clock: float) -> float:
    """A clock that steps once a beat (a second without music) and holds: its whole beats, and the
    step on its way, taking TICK of the beat and overshooting as it lands."""
    n = math.floor(clock)
    return n + easeOutBack(min(1.0, (clock - n) / TICK))

class Sweep:
    """A hint's knob as the Curved knobs of control.py's patterns are: its control's value, or
    Curved, a Curve each Period of the hint's clock from rest to the value and back (as mk_bump), or
    with mk_bounce and a rest of 0, to the value, back through 0 to its negative and back."""
    def __init__(self, name: str, options: list[Option], rest: float=0.0, shape=mk_bump):
        self.control = Control(name, options)
        self.curved = ToggleControl(f"{name} Curved")
        self.curve = Control(f"{name} Curve", CURVES)
        self.period = Control(f"{name} Period", SWEEPS)
        self.controls = [self.control, self.curved, self.curve, self.period]
        self.rest = rest
        self.shape = shape

    @property
    def value(self) -> Param:
        if not self.curved.value:
            return self.control.value
        return Curve(self.curve.value, self.shape(self.period.value, self.rest, self.control.value))

class PaletteColor(Color):
    """A palette's colour as the tree takes it: OKLCh to linear R, G and B (the LEDs are linear PWM),
    never through the HSL wheel, which would lose the palette's even steps. Its l is a Color's: -1
    off, 0 the palette's colour, and on up to 1 white, as the beat flash lifts it."""
    def __init__(self, lch: tuple[float, float, float]):
        super(PaletteColor, self).__init__(l=0.0)
        self.lch = lch

    def as_wrgb(self) -> tuple[float, float, float, float]:
        if self.l == -1.0:
            return (self.w * 255, 0, 0, 0)
        L, C, h = self.lch
        rgb = oklch_to_linear((L, C * self.s, h + (360 * self.h)))
        if self.l < 0:
            rgb = [c * (1 + self.l) for c in rgb]
        else:
            rgb = [c + ((1 - c) * self.l) for c in rgb]
        return (self.w * 255, *(255 * c for c in rgb))

class Hint(BaseColor):
    """A hint's light, from its feature: each of its layers' palette colour, at the layer's
    lightness, as much as the layer covers the light, and off for the rest. The palette is the
    hint's own, off the base hue's clock as a BaseColor with blend off is, unless the hint rides it:
    then it turns with the base hue."""
    def __init__(self, feature: "HintFeature"):
        super(Hint, self).__init__()
        self.feature = feature

    def frame(self, beats: float, dt: float):
        self.feature.frame(beats, dt)

    def __call__(self, t: float, blend: float, spread: float, pixel_t: float, pixel_y: float, pixel):
        out = []
        total = 0.0
        for cover, lch, l in self.feature.layers(pixel_t % 1, pixel_y):
            if cover > 0:
                color = PaletteColor(lch)
                color.l = l
                if self.feature.ride:
                    color.h = blend
                out.append((cover, color, []))
                total += cover
        return out + [(1 - total, Color(), [])]

class HintFeature(Feature):
    """A hint's controls and its shape: layers gives, for a light at an angle round the trunk (0 to
    1) and a height, how much of each of the shape's layers covers it (their covers summing to 1 at
    most), its colour from the palette and its lightness; one layer, light's, unless the hint gives
    more. Its clock and its modulators run on each frame's beats: the beat clock's while music
    plays, else one a second, and its sweeps on its clock. Its value sets them from the controls and
    gives the same Hint each time, so their phases run on through a change of control, as
    Bermuda's do."""
    def __init__(self, name: str, controls: list[Control], runnings: list[Running], sweeps: list[Sweep] | None=None):
        super(HintFeature, self).__init__(name, controls)
        self.runnings = runnings
        self.sweeps = sweeps if sweeps is not None else []
        self.palette = Palette([])
        self.ride = False
        self.clock = 0.0
        self.dt = 0.0
        self.hint = Hint(self)

    def frame(self, beats: float, dt: float):
        self.clock += beats
        self.dt = dt
        for running in self.runnings:
            running.advance(beats, dt)

    def lock(self, beat: float):
        """Draws the clock onto the music's beat, its place in a bar, so a tick lands on a beat and a
        sweep turns on a bar line."""
        self.clock += (((beat - self.clock + 2) % 4) - 2) * (1 - math.exp(-self.dt / LOCK))

    def light(self, x: float, y: float) -> tuple[float, Vec3]:
        raise NotImplementedError

    def layers(self, x: float, y: float) -> list[tuple[float, Vec3, float]]:
        cover, lch = self.light(x, y)
        return [(cover, lch, 0.0)]

    def visible_controls(self) -> list[Control]:
        # a sweep's Curve and Period only while it's Curved
        hidden = [c for sweep in self.sweeps if not sweep.curved.value for c in (sweep.curve, sweep.period)]
        return [c for c in self.controls if c not in hidden]

    @property
    def value(self) -> dict:
        return {"base_color": self.hint}

class WashFeature(HintFeature):
    """The palette running up the tree (or with Axis round, round the trunk, as Palette Drift's did),
    a wave of brightness travelling across it, as a tide: its span and spread swept, the palette
    climbing and wobbling, and with Ride, turning with the base hue."""
    def __init__(self):
        self._palette = Control("Palette", PALETTES)
        self._axis = Control("Axis", [Option(n, n) for n in ["up", "round"]])
        self._period = Control("Period", BEATS)
        self._span = Sweep("Span", [Option(n, v) for n, v in [("1/4", 1/4), ("1/2", 1/2), ("1", 1)]], rest=3/2)
        self._wave = Control("Wave", WAVES)
        self._spread = Sweep("Spread", [Option(str(v), v) for v in [0, 1, 2, 3]], rest=3)
        self._ride = ToggleControl("Ride")
        self.span: Param = 0.0
        self.spread: Param = 0.0
        self.swept = (0.0, 0.0)
        self.running = Running(Modulator("wash", "cos", 16, harmonics=HARMONICS), Target("brightness", 1))
        super(WashFeature, self).__init__("Wash", [
            self._palette,
            self._axis,
            self._period,
            *self._span.controls,
            self._wave,
            *self._spread.controls,
            self._ride,
        ], [self.running], [self._span, self._spread])

    @property
    def value(self):
        self.palette = preset(self._palette.value)
        self.running.m.period = self._period.value
        self.running.m.wave = self._wave.value
        self.span = self._span.value
        self.spread = self._spread.value
        self.ride = self._ride.value
        return super(WashFeature, self).value

    def frame(self, beats, dt):
        super(WashFeature, self).frame(beats, dt)
        self.swept = (getv(self.span, self.clock), getv(self.spread, self.clock))

    def layers(self, x, y):
        span, spread = self.swept
        clock = self.clock
        phase = self.running.phase

        def dim(level: float) -> float:
            return 1 - (DIP * (1 - level))

        if self._axis.value == "round":
            # the palette round the trunk in whole turns, the two either side of its span's crossfaded
            # so angle 0 is no edge, the wave travelling up the tree
            turns = span * ROUND
            k = math.floor(turns)
            f = turns - k
            index = -phase - (clock * CLIMB) + (WOBBLE * math.sin(2 * math.pi * (y + (clock / WOBBLE_PERIOD))))
            brightness = dim(wave(self.running.m, phase + (spread * y)))
            return [
                (brightness * (1 - f), palette_at(self.palette, (k * x) + index), 0.0),
                (brightness * f, palette_at(self.palette, ((k + 1) * x) + index), 0.0),
            ]
        # the wave round the trunk in whole turns of its spread, the two either side crossfaded
        k = math.floor(spread)
        f = spread - k
        level = ((1 - f) * wave(self.running.m, phase + (k * x))) + (f * wave(self.running.m, phase + ((k + 1) * x)))
        index = (y * span) - phase - (clock * CLIMB) + (WOBBLE * math.sin(2 * math.pi * (x + (clock / WOBBLE_PERIOD))))
        return [(dim(level), palette_at(self.palette, index), 0.0)]

class SlicesFeature(HintFeature):
    """Soft slices of the palette, each its own colour: round the trunk (as sectors), up it (as
    rings) or leaned (as arms winding up), turning round it or climbing it, gliding or ticking a step
    a beat, and leaning, the rings tilting, one way and the other as they go."""
    def __init__(self):
        self._palette = Control("Palette", PALETTES)
        self._axis = Control("Axis", [Option(n, n) for n in ["around", "up", "leaned"]])
        self._count = Control("Count", [Option(str(v), v) for v in range(2, 7)])
        self._period = Control("Period", BEATS)
        self._direction = Control("Direction", DIRECTIONS)
        self._motion = Control("Motion", [Option(n, n) for n in ["glide", "tick"]])
        # slots of lean over the tree's height
        self._lean = Sweep("Lean", [Option(str(v), v) for v in [1, 2, 4]], shape=mk_bounce)
        self._softness = Control("Softness", SOFTNESS)
        self.lean: Param = 0.0
        self.turn = 0.0  # the turn round the trunk, or with Axis up the climb up the tree
        self.stepped = 0.0  # the clock as the turn last stepped on it, ticked or not
        self.swept = 0.0
        super(SlicesFeature, self).__init__("Slices", [
            self._palette,
            self._axis,
            self._count,
            self._period,
            self._direction,
            self._motion,
            *self._lean.controls,
            self._softness,
        ], [], [self._lean])

    @property
    def value(self):
        self.palette = preset(self._palette.value)
        self.lean = self._lean.value
        return super(SlicesFeature, self).value

    def frame(self, beats, dt):
        super(SlicesFeature, self).frame(beats, dt)
        # a whole turn each period, run on from where it is, so it moves on through a change of control
        stepped = tick(self.clock) if self._motion.value == "tick" else self.clock
        self.turn = (self.turn + ((stepped - self.stepped) * self._direction.value / self._period.value)) % 1
        self.stepped = stepped
        self.swept = getv(self.lean, self.clock)

    def light(self, x, y):
        turn, lean = self.turn, self.swept
        count = self._count.value
        axis = self._axis.value
        if axis == "up":
            u = (count * (y - turn)) + (lean * TILT * math.cos(2 * math.pi * x))
        else:
            twist = count * TWIST if axis == "leaned" else 0
            u = (((x - turn) % 1) * count) + ((twist + lean) * y)
        cover, k = slot(u, self._softness.value)
        return cover, palette_at(self.palette, ((k % count) / count) + (y * PALETTE_UP))

class HiddenFieldFeature(HintFeature):
    """Sparkles that trace a hidden field: a lattice of stars seen from above the treetop, turning
    slowly. As it's revealed the sparkles thicken and soften until the stars stand solid, turning
    faster, then dissolve back into sparse sparkles. A light's place seen from above is its angle and
    height on the cone, so the field has no seam and turns with the spin and the spin ring, and a
    light sparkles only where a star covers it."""
    def __init__(self):
        self._palette = Control("Palette", PALETTES)
        self._points = Control("Points", [Option(str(v), v) for v in [4, 5, 6]])
        self._lattice = Control("Lattice", [Option(n, v) for n, v in [("1/4", 1/4), ("1/3", 1/3), ("1/2", 1/2)]])
        self._period = Control("Period", [Option(str(v), v) for v in [128, 256, 512]])
        self._twinkle = Control("Twinkle", [Option(str(v), v) for v in [4, 6, 8]])
        # how far it's revealed at the sweep's far end: 1 the stars solid
        self._reveal = Sweep("Reveal", [Option(n, v) for n, v in [("1/2", 1/2), ("3/4", 3/4), ("1", 1)]])
        self.reveal: Param = 0.0
        self.share = SPARKLES
        self.sharp = SPARKLE
        self.running = Running(Modulator("turn", "ramp", 32), Target("turn", 1))
        super(HiddenFieldFeature, self).__init__("Hidden Field", [
            self._palette,
            self._points,
            self._lattice,
            self._period,
            self._twinkle,
            *self._reveal.controls,
        ], [self.running], [self._reveal])

    @property
    def value(self):
        self.palette = preset(self._palette.value)
        self.reveal = self._reveal.value
        return super(HiddenFieldFeature, self).value

    def frame(self, beats, dt):
        revealed = getv(self.reveal, self.clock)
        # past a share of 1 by its edge, so every light is fully on once revealed
        self.share = SPARKLES + ((1 + SHARE_EDGE - SPARKLES) * revealed)
        self.sharp = SPARKLE + ((SOLID - SPARKLE) * revealed)
        self.running.m.period = self._period.value / (1 + (FASTER * revealed))
        super(HiddenFieldFeature, self).frame(beats, dt)

    def light(self, x, y):
        # a light sparkles in some Twinkles, at a time in them its height picks, and is dark between;
        # as the share grows, a light fades in over SHARE_EDGE of it
        seed = (math.sin(y * 12345.678) * 43758.5453) % 1
        twinkle = (self.clock / self._twinkle.value) + seed
        pick = (math.sin((math.floor(twinkle) * 91.7) + (seed * 977.3)) * 43758.5453) % 1
        on = min(1.0, (self.share - pick) / SHARE_EDGE)
        if on <= 0:
            return 0.0, (0.0, 0.0, 0.0)
        sparkle = on * (math.sin(math.pi * (twinkle % 1)) ** self.sharp)
        a = 2 * math.pi * (x - self.running.at(0))
        px, pz = (1 - y) * math.cos(a), (1 - y) * math.sin(a)
        # the nearest point of a hexagonal lattice spacing apart, by its column and row
        spacing = self._lattice.value
        row = pz / (spacing * math.sqrt(3) / 2)
        col = (px / spacing) - (row / 2)

        def place(c: int, r: int) -> tuple[float, float]:
            return (c + (r / 2)) * spacing, r * spacing * math.sqrt(3) / 2

        c, r = min((
            (c, r)
            for r in (math.floor(row), math.floor(row) + 1)
            for c in (math.floor(col), math.floor(col) + 1)
        ), key=lambda q: math.hypot(px - place(*q)[0], pz - place(*q)[1]))
        qx, qz = place(c, r)
        dx, dz = px - qx, pz - qz
        rho = math.hypot(dx, dz) / spacing
        edge = STAR * (1 - (STAR_CUT * (0.5 - (0.5 * math.cos(self._points.value * math.atan2(dz, dx))))))
        inside = min(1.0, max(0.0, (((edge - rho) * spacing) / STAR_EDGE) + 0.5))
        # each star its own colour, the golden ratio's steps apart along the palette
        return inside * sparkle, palette_at(self.palette, ((c * 0.381966) + (r * 0.618034)) % 1)

class HintPattern(WiredPattern):
    """A hint and Blend. While the music's tempo is sure, the hint's clock is drawn onto the beat."""
    def __init__(self, feature: HintFeature):
        super(HintPattern, self).__init__(feature.name)
        self.features = [feature, BlendFeature()]

    def step(self, t, pixels, sound, beating, beat, hue):
        if beating:
            self.features[0].lock(sound.beat)

class Wash(HintPattern):
    def __init__(self):
        super(Wash, self).__init__(WashFeature())

class Slices(HintPattern):
    def __init__(self):
        super(Slices, self).__init__(SlicesFeature())

class HiddenField(HintPattern):
    def __init__(self):
        super(HiddenField, self).__init__(HiddenFieldFeature())

HINTS = [Wash, Slices, HiddenField]
