"""Hints of Bermuda's looks on the tree: at about 800 lights it cannot show Bermuda's pictures, so
these are slow, soft-edged shapes in Bermuda's palettes (palette.py), moved by its modulators and
their timing (motion.py), most of them using the angle round the trunk. Each light's brightness is
how much of the shape covers it, so motion glides instead of stepping from light to light."""
import math

from colors import BaseColor, Color
from control import DIRECTIONS, BlendFeature, Control, Feature, Option, WiredPattern
from motion import Modulator, Running, Target
from palette import COSINES, Palette, oklch_to_linear, palette_at, stops_from_cosine
from utils import coverage

# The stops a cosine preset is sampled at
STOPS = 8
# A sector's, band's or spiral arm's share of its slot, the rest dark between
FILL = 0.5
# How far the wash and the palette drift dim at their wave's trough
DIP = 0.6
# The hidden field: a star's outer radius, as a share of the lattice's spacing, how deep its points
# are cut, its soft edge (of the base's radius), the share of Twinkles a light sparkles in, and how
# sharp a sparkle is
STAR = 0.34
STAR_CUT = 0.45
STAR_EDGE = 0.08
SPARKLES = 0.5
SPARKLE = 4
# The beat wave's harmonics, for a hint's Wave control
HARMONICS = (1, 2)

PALETTES = [Option(name, name) for name in COSINES]
WAVES = [Option(name, name) for name in ["cos", "tri", "beat"]]
BEATS = [Option(str(v), v) for v in [16, 32, 64]]
# a soft edge's width, as a share of the lit part of a slot: at 1 a light is only full at its middle
SOFTNESS = [Option(n, v) for n, v in [("1/2", 1/2), ("3/4", 3/4), ("1", 1)]]

def preset(name: str) -> Palette:
    return Palette(stops_from_cosine(name, STOPS))

def slot(u: float, softness: float) -> tuple[float, int]:
    """For a light at u, counted in slots (sectors round the trunk, bands up it, a spiral's arms), how
    much of its slot's lit part covers it, its edges softness of it wide, and which slot it is in, the
    slots meeting halfway across the dark between."""
    k = math.floor(u + ((1 - FILL) / 2))
    return coverage(u - k, 0, FILL, softness * FILL, wrap=False), k

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
    """A hint's light, from its feature: as much of its palette's colour as its shape covers the
    light, and off for the rest. The palette is the hint's own, off the base hue's clock, as a
    BaseColor with blend off is."""
    def __init__(self, feature: "HintFeature"):
        super(Hint, self).__init__()
        self.feature = feature

    def frame(self, beats: float, dt: float):
        self.feature.frame(beats, dt)

    def __call__(self, t: float, blend: float, spread: float, pixel_t: float, pixel_y: float, pixel):
        cover, lch = self.feature.light(pixel_t % 1, pixel_y)
        return [(cover, PaletteColor(lch), []), (1 - cover, Color(), [])]

class HintFeature(Feature):
    """A hint's controls and its shape: light gives, for a light at an angle round the trunk (0 to 1)
    and a height, how much of the shape covers it (0 to 1) and its colour from the palette. Its
    modulators run on each frame's beats: the beat clock's while music plays, else one a second. Its
    value sets them from the controls and gives the same Hint each time, so their phases run on
    through a change of control, as Bermuda's do."""
    def __init__(self, name: str, controls: list[Control], runnings: list[Running]):
        super(HintFeature, self).__init__(name, controls)
        self.runnings = runnings
        self.palette = Palette([])
        self.hint = Hint(self)

    def frame(self, beats: float, dt: float):
        for running in self.runnings:
            running.advance(beats, dt)

    def light(self, x: float, y: float) -> tuple[float, tuple[float, float, float]]:
        raise NotImplementedError

    @property
    def value(self) -> dict:
        return {"base_color": self.hint}

class WashFeature(HintFeature):
    """The palette running up the tree, a wave of brightness travelling round it."""
    def __init__(self):
        self._palette = Control("Palette", PALETTES)
        self._period = Control("Period", BEATS)
        self._span = Control("Span", [Option(n, v) for n, v in [("1/4", 1/4), ("1/2", 1/2), ("1", 1)]])
        self._wave = Control("Wave", WAVES)
        self._spread = Control("Spread round", [Option(str(v), v) for v in [0, 1, 2, 3]])
        self.running = Running(Modulator("wash", "cos", 16, harmonics=HARMONICS), Target("brightness", 1))
        super(WashFeature, self).__init__("Wash", [
            self._palette,
            self._period,
            self._span,
            self._wave,
            self._spread,
        ], [self.running])

    @property
    def value(self):
        self.palette = preset(self._palette.value)
        self.running.m.period = self._period.value
        self.running.m.wave = self._wave.value
        self.running.target.phase_spread = self._spread.value
        return super(WashFeature, self).value

    def light(self, x, y):
        return 1 - (DIP * (1 - self.running.at(x))), palette_at(self.palette, (y * self._span.value) - self.running.phase)

class SectorsFeature(HintFeature):
    """Soft sectors round the trunk, each its own colour, spinning or swaying a sector either way."""
    def __init__(self):
        self._palette = Control("Palette", PALETTES)
        self._count = Control("Count", [Option(str(v), v) for v in range(2, 7)])
        self._period = Control("Period", BEATS)
        self._direction = Control("Direction", DIRECTIONS)
        self._motion = Control("Motion", [Option(n, n) for n in ["spin", "sway"]])
        self._softness = Control("Softness", SOFTNESS)
        self.running = Running(Modulator("turn", "ramp", 16), Target("turn", 1))
        super(SectorsFeature, self).__init__("Sectors", [
            self._palette,
            self._count,
            self._period,
            self._direction,
            self._motion,
            self._softness,
        ], [self.running])

    @property
    def value(self):
        self.palette = preset(self._palette.value)
        self.running.m.period = self._period.value
        # a spin is a ramp, a whole turn each period; a sway a cos, a sector either way
        self.running.m.wave = "ramp" if self._motion.value == "spin" else "cos"
        return super(SectorsFeature, self).value

    def light(self, x, y):
        count = self._count.value
        if self._motion.value == "spin":
            turn = self.running.at(0)
        else:
            turn = self.running.offset(0) / count
        cover, k = slot(((x - (turn * self._direction.value)) % 1) * count, self._softness.value)
        return cover, palette_at(self.palette, k / count)

class BandsFeature(HintFeature):
    """Rings up the tree that climb, fall, or rise and fall back, at the contour's drift."""
    def __init__(self):
        self._palette = Control("Palette", PALETTES)
        self._bands = Control("Bands", [Option(str(v), v) for v in [2, 3, 4, 6]])
        # radians a beat, as Bermuda's contour drift: a band climbs a band's spacing each 2π
        self._drift = Control("Drift", [Option(str(v), v) for v in [0.25, 0.5, 1.0]])
        self._direction = Control("Direction", [Option(n, n) for n in ["↑ ", "↓ ", "⇅ "]])
        self._softness = Control("Softness", SOFTNESS)
        self.drift = 0.0  # the bands' phase, in radians
        self.running = Running(Modulator("bands", "cos", 16), Target("contour.drift", 1))
        super(BandsFeature, self).__init__("Bands", [
            self._palette,
            self._bands,
            self._drift,
            self._direction,
            self._softness,
        ], [self.running])

    @property
    def value(self):
        self.palette = preset(self._palette.value)
        # rising and falling, a band's spacing either way, in the time the drift climbs one
        self.running.m.period = 2 * math.pi / self._drift.value
        return super(BandsFeature, self).value

    def frame(self, beats, dt):
        super(BandsFeature, self).frame(beats, dt)
        self.drift = (self.drift + (self._drift.value * beats)) % (2 * math.pi)

    def light(self, x, y):
        direction = self._direction.value
        if direction == "⇅ ":
            offset = self.running.offset(0)
        else:
            offset = (self.drift / (2 * math.pi)) * (1 if direction == "↑ " else -1)
        bands = self._bands.value
        cover, k = slot((y * bands) - offset, self._softness.value)
        return cover, palette_at(self.palette, k / bands)

class SpiralArmsFeature(HintFeature):
    """Soft arms winding up the tree and turning round it, the palette running up each."""
    def __init__(self):
        self._palette = Control("Palette", PALETTES)
        self._arms = Control("Arms", [Option(str(v), v) for v in [1, 2, 3]])
        self._twist = Control("Twist", [Option(str(v), v) for v in [0.5, 1, 1.5, 2]])
        self._period = Control("Period", BEATS)
        self._direction = Control("Direction", DIRECTIONS)
        self._softness = Control("Softness", SOFTNESS)
        self.running = Running(Modulator("turn", "ramp", 16), Target("turn", 1))
        super(SpiralArmsFeature, self).__init__("Spiral", [
            self._palette,
            self._arms,
            self._twist,
            self._period,
            self._direction,
            self._softness,
        ], [self.running])

    @property
    def value(self):
        self.palette = preset(self._palette.value)
        self.running.m.period = self._period.value
        return super(SpiralArmsFeature, self).value

    def light(self, x, y):
        arms = self._arms.value
        turn = self.running.at(0) * self._direction.value
        cover, k = slot(((x + (self._twist.value * y) - turn) % 1) * arms, self._softness.value)
        return cover, palette_at(self.palette, (k / arms) + (y / 2))

class HiddenFieldFeature(HintFeature):
    """Sparse sparkles that trace a hidden field over a few seconds: a lattice of stars seen from above
    the treetop, turning slowly. A light's place seen from above is its angle and height on the cone,
    so the field has no seam and turns with the spin and the spin ring, and a light sparkles only
    where a star covers it."""
    def __init__(self):
        self._palette = Control("Palette", PALETTES)
        self._points = Control("Points", [Option(str(v), v) for v in [4, 5, 6]])
        self._lattice = Control("Lattice", [Option(n, v) for n, v in [("1/4", 1/4), ("1/3", 1/3), ("1/2", 1/2)]])
        self._period = Control("Period", [Option(str(v), v) for v in [128, 256, 512]])
        self._twinkle = Control("Twinkle", [Option(str(v), v) for v in [4, 6, 8]])
        self.beats = 0.0
        self.running = Running(Modulator("turn", "ramp", 32), Target("turn", 1))
        super(HiddenFieldFeature, self).__init__("Hidden Field", [
            self._palette,
            self._points,
            self._lattice,
            self._period,
            self._twinkle,
        ], [self.running])

    @property
    def value(self):
        self.palette = preset(self._palette.value)
        self.running.m.period = self._period.value
        return super(HiddenFieldFeature, self).value

    def frame(self, beats, dt):
        super(HiddenFieldFeature, self).frame(beats, dt)
        self.beats += beats

    def light(self, x, y):
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
        # a light sparkles in some Twinkles, at a time in them its height picks, and is dark between
        seed = (math.sin(y * 12345.678) * 43758.5453) % 1
        twinkle = (self.beats / self._twinkle.value) + seed
        if (math.sin((math.floor(twinkle) * 91.7) + (seed * 977.3)) * 43758.5453) % 1 >= SPARKLES:
            return 0.0, (0.0, 0.0, 0.0)
        sparkle = math.sin(math.pi * (twinkle % 1)) ** SPARKLE
        # each star its own colour, the golden ratio's steps apart along the palette
        return inside * sparkle, palette_at(self.palette, ((c * 0.381966) + (r * 0.618034)) % 1)

class PaletteDriftFeature(HintFeature):
    """The palette drifting round the trunk at the palette's time, a wave of brightness travelling
    up the tree."""
    def __init__(self):
        self._palette = Control("Palette", PALETTES)
        self._repeats = Control("Repeats", [Option(str(v), v) for v in [1, 2, 3]])
        # cycles of the palette a beat, as Bermuda's palette time
        self._time = Control("Time", [Option(n, v) for n, v in [("1/64", 1/64), ("1/32", 1/32), ("1/16", 1/16)]])
        self._direction = Control("Direction", DIRECTIONS)
        self._wave = Control("Wave", WAVES)
        self._spread = Control("Spread up", [Option(n, v) for n, v in [("1/2", 1/2), ("1", 1), ("2", 2)]])
        self.colour = 0.0  # the palette's running index
        self.running = Running(Modulator("drift", "cos", 16, harmonics=HARMONICS), Target("brightness", 1))
        super(PaletteDriftFeature, self).__init__("Palette Drift", [
            self._palette,
            self._repeats,
            self._time,
            self._direction,
            self._wave,
            self._spread,
        ], [self.running])

    @property
    def value(self):
        self.palette = preset(self._palette.value)
        # the wave takes as long to travel up the tree as the palette takes to drift round once
        self.running.m.period = 1 / self._time.value
        self.running.m.wave = self._wave.value
        self.running.target.phase_spread = self._spread.value
        return super(PaletteDriftFeature, self).value

    def frame(self, beats, dt):
        super(PaletteDriftFeature, self).frame(beats, dt)
        self.colour = (self.colour + (self._time.value * self._direction.value * beats)) % 1

    def light(self, x, y):
        return 1 - (DIP * (1 - self.running.at(y))), palette_at(self.palette, (self._repeats.value * x) + self.colour)

class Wash(WiredPattern):
    def __init__(self):
        super(Wash, self).__init__("Wash")
        self.features = [WashFeature(), BlendFeature()]

class Sectors(WiredPattern):
    def __init__(self):
        super(Sectors, self).__init__("Sectors")
        self.features = [SectorsFeature(), BlendFeature()]

class Bands(WiredPattern):
    def __init__(self):
        super(Bands, self).__init__("Bands")
        self.features = [BandsFeature(), BlendFeature()]

class Spiral(WiredPattern):
    def __init__(self):
        super(Spiral, self).__init__("Spiral")
        self.features = [SpiralArmsFeature(), BlendFeature()]

class HiddenField(WiredPattern):
    def __init__(self):
        super(HiddenField, self).__init__("Hidden Field")
        self.features = [HiddenFieldFeature(), BlendFeature()]

class PaletteDrift(WiredPattern):
    def __init__(self):
        super(PaletteDrift, self).__init__("Palette Drift")
        self.features = [PaletteDriftFeature(), BlendFeature()]

HINTS = [Wash, Sectors, Bands, Spiral, HiddenField, PaletteDrift]
