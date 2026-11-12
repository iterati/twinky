"""OKLCh palettes, ported from Bermuda's src/colour.ts (a15fad7) with its names in snake_case and
its numbers: iq's cosine presets, the sRGB and OKLCh conversions, palette stops filled from a preset,
and the palette at an index. The tree takes its colour as linear light, oklch_to_linear's values,
as its LEDs are linear PWM; oklch_to_srgb is those through to_gamma, as Bermuda's screen takes them."""
from dataclasses import dataclass
import math

Vec3 = tuple[float, float, float]

@dataclass
class Stop:
    """A palette stop: where it sits on the index (0 to 1), its L, C and h, and how it mixes into the
    next: "straight" in Lab, "short" or "long" round the hue circle."""
    at: float
    lch: Vec3
    mix: str

@dataclass
class Palette:
    """Bermuda's scene palette, the parts the tree reads: its stops, a hue added to each stop's in
    degrees, and the contrast its lightness is spread by round 0.5."""
    stops: list[Stop]
    hue: float = 0.0
    contrast: float = 1.0

# iq's cosine palettes, a + b·cos(2π(c·t + d)), as the Tapestries used them
COSINES: dict[str, tuple[Vec3, Vec3, Vec3, Vec3]] = {
    "rainbow": (
        (0.5, 0.5, 0.5),
        (0.5, 0.5, 0.5),
        (1, 1, 1),
        (0, 0.333, 0.667),
    ),
    "warm": (
        (0.6, 0.6, 0.6),
        (0.4, 0.3, 0.35),
        (2, 2, 2),
        (0.85, 0.55, 0.25),
    ),
    "dusk": (
        (0.744, 0.244, 0.577),
        (0.231, 0.395, 0.498),
        (0.759, 1.375, 0.932),
        (3.477, 6.066, 1.898),
    ),
    "ice": (
        (0.5, 0.5, 0.5),
        (0.5, 0.5, 0.5),
        (1, 1, 1),
        (0.3, 0.2, 0.2),
    ),
    "forest": (
        (0.5, 0.5, 0.5),
        (0.5, 0.5, 0.5),
        (1, 1, 0.5),
        (0.8, 0.9, 0.3),
    ),
    "ember": (
        (0.5, 0.5, 0.5),
        (0.5, 0.5, 0.5),
        (1, 0.7, 0.4),
        (0, 0.15, 0.2),
    ),
}

def cosine(abcd: tuple[Vec3, Vec3, Vec3, Vec3], t: float) -> Vec3:
    a, b, c, d = abcd
    return tuple(min(1, max(0, a[i] + b[i] * math.cos(2 * math.pi * (c[i] * t + d[i])))) for i in range(3))

def to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def to_gamma(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055

def srgb_to_oklch(rgb: Vec3) -> Vec3:
    r, g, b = (to_linear(c) for c in rgb)
    l = math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m = math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s = math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    L = 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s
    A = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s
    B = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s
    h = (math.atan2(B, A) * 180) / math.pi
    return (L, math.hypot(A, B), (h + 360) % 360)

def oklch_to_linear(lch: Vec3) -> Vec3:
    """oklchToSrgb's R, G and B before to_gamma: linear light, each kept to 0 to 1."""
    L, C, h = lch
    A = C * math.cos((h * math.pi) / 180)
    B = C * math.sin((h * math.pi) / 180)
    l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3
    m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3
    s = (L - 0.0894841775 * A - 1.291485548 * B) ** 3
    return tuple(min(1, max(0, c)) for c in (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
    ))

def oklch_to_srgb(lch: Vec3) -> Vec3:
    return tuple(to_gamma(c) for c in oklch_to_linear(lch))

def js_round(v: float) -> float:
    # JavaScript's Math.round: halves round up, where Python's round takes them to the even side
    return math.floor(v + 0.5)

def round3(v: float) -> float:
    return js_round(v * 1000) / 1000

def stops_from_cosine(name: str, count: int) -> list[Stop]:
    """Samples a cosine preset at evenly spaced stops, each segment mixing the short way round."""
    stops = []
    for i in range(count):
        L, C, h = srgb_to_oklch(cosine(COSINES[name], i / count))
        stops.append(Stop(i / count, (round3(L), round3(min(C, 0.37)), js_round(h)), "short"))
    return stops

def palette_at(palette: Palette, t: float) -> Vec3:
    """The palette at index t, as Bermuda's shader works it out: L, C and h."""
    stops = palette.stops
    t -= math.floor(t)
    k = len(stops) - 1
    for i, s in enumerate(stops):
        if s.at <= t:
            k = i
    k2 = 0 if k + 1 >= len(stops) else k + 1
    a = stops[k]
    b = stops[k2]
    a1 = b.at + 1 if k2 <= k else b.at
    f = min(1, max(0, ((t + 1 if t < a.at else t) - a.at) / max(a1 - a.at, 1e-5)))
    ha, hb = a.lch[2] + palette.hue, b.lch[2] + palette.hue
    L = a.lch[0] + (b.lch[0] - a.lch[0]) * f
    lightness = min(1, max(0, 0.5 + (L - 0.5) * palette.contrast))
    if a.mix == "straight":
        def lab(s: Stop, h: float) -> tuple[float, float]:
            return (s.lch[1] * math.cos((h * math.pi) / 180), s.lch[1] * math.sin((h * math.pi) / 180))
        xa, ya = lab(a, ha)
        xb, yb = lab(b, hb)
        x = xa + (xb - xa) * f
        y = ya + (yb - ya) * f
        return (lightness, math.hypot(x, y), (math.atan2(y, x) * 180) / math.pi)
    dh = ((((hb - ha + 180) % 360) + 360) % 360) - 180
    if a.mix == "long":
        # Math.sign: 0 at 0
        dh -= ((dh + 1e-6 > 0) - (dh + 1e-6 < 0)) * 360
    return (lightness, a.lch[1] + (b.lch[1] - a.lch[1]) * f, ha + dh * f)
