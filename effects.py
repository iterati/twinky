"""Ten effects in the tree's 3D space: Aurora, Fireflies, Fireworks, Ripples, Lava lamp, Comets,
Hearth, Lightning, Drips and Heartbeat.

Each is a WiredPattern whose base color is its Effect. Once a frame, before the lights, the Blender
calls the pattern's step with the run's clock, every light, the music and the base hue, and the
effect works out each light's layers from its x, y and z: (cover, (w, h, s, l)), how much of a shape
covers the light and its colour in Color's terms. Then the Blender asks for each light in turn, and
the effect gives it those layers and an off one making up the rest, mixed in light as WRGB the way
the other patterns' are, so transitions and glides work on them as they do.

Grain raw hardens the soft edges, a light in or out; only the rainbow palettes turn with the base
hue's 66 s clock. With Music on, a beat and the bands drive each effect's knobs as its notes say; off,
they play as set."""
import math
import random

from colors import BaseColor, Color
from control import BlendFeature, Control, Feature, Option, WiredPattern

# Hues on xled_plus's 8col circle: blue 0, cyan 1/8, green 2/8, yellow 3/8, orange 4/8, red 5/8,
# magenta 6/8, purple 7/8
BLUE, CYAN, GREEN, YELLOW, ORANGE, RED, MAGENTA, PURPLE = [i / 8 for i in range(8)]

# A layer's colour as (w, h, s, l), Color's own terms
FULL = lambda h: (0.0, h % 1, 1.0, 0.0)
WARM_WHITE = (1.0, 0.0, 0.0, -1.0)  # the W LEDs alone
COOL_WHITE = (0.6, CYAN, 0.25, -0.35)

# The palette that turns with the base hue, in every effect that has one
RAINBOW = "rainbow"
# With grain raw, a light more covered than this is in, the rest out
RAW_EDGE = 0.35
# The music: how quickly an effect follows the bands, in seconds, and a beat's swell, rising and
# falling away
BAND_GLIDE = 0.3
SWELL_RISE = 0.15
SWELL_FALL = 0.35


# --- shared pieces ---------------------------------------------------------------------------

def smoothstep(a, b, x):
    if x <= a:
        return 0.0
    if x >= b:
        return 1.0
    x = (x - a) / (b - a)
    return x * x * (3 - 2 * x)

def bump(d2, s2):
    """A soft round spot: 1 at its middle, 0 from size s out, d2 and s2 squared."""
    q = 1.0 - d2 / s2
    return q * q if q > 0 else 0.0

def lerp_h(a, b, m):
    """A hue m of the way from a to b, the short way round."""
    d = ((b - a + 0.5) % 1) - 0.5
    return (a + d * m) % 1

def turned(color, hue):
    """A colour turned round the wheel by hue."""
    w, h, s, l = color
    return (w, (h + hue) % 1, s, l)

def banded(value, band):
    """A knob's value as a band drives it: half at a quiet band, as set at a middling one, half as
    much again at a loud one."""
    return value * (0.5 + band)

def seg_dist2(p, a, b):
    """How far p is from the segment a to b, squared."""
    ax, ay, az = a
    dx, dy, dz = b[0] - ax, b[1] - ay, b[2] - az
    px, py, pz = p[0] - ax, p[1] - ay, p[2] - az
    den = dx * dx + dy * dy + dz * dz
    u = 0.0 if den == 0 else max(0.0, min(1.0, (px * dx + py * dy + pz * dz) / den))
    return (px - u * dx) ** 2 + (py - u * dy) ** 2 + (pz - u * dz) ** 2

class Noise3:
    """Smooth value noise in 3D, 0 to 1, and its sum over octaves."""
    def __init__(self):
        rnd = random.Random(random.random())
        perm = list(range(256))
        rnd.shuffle(perm)
        self.perm = perm + perm
        self.values = [rnd.random() for _ in range(256)]

    def __call__(self, x, y, z):
        p, v = self.perm, self.values
        xi, yi, zi = math.floor(x), math.floor(y), math.floor(z)
        xf, yf, zf = x - xi, y - yi, z - zi
        xi, yi, zi = xi & 255, yi & 255, zi & 255
        u = xf * xf * (3 - 2 * xf)
        w = yf * yf * (3 - 2 * yf)
        s = zf * zf * (3 - 2 * zf)
        a, b = p[xi] + yi, p[xi + 1] + yi
        aa, ab, ba, bb = p[a] + zi, p[a + 1] + zi, p[b] + zi, p[b + 1] + zi
        x00 = v[p[aa]] + u * (v[p[ba]] - v[p[aa]])
        x10 = v[p[ab]] + u * (v[p[bb]] - v[p[ab]])
        x01 = v[p[aa + 1]] + u * (v[p[ba + 1]] - v[p[aa + 1]])
        x11 = v[p[ab + 1]] + u * (v[p[bb + 1]] - v[p[ab + 1]])
        y0 = x00 + w * (x10 - x00)
        y1 = x01 + w * (x11 - x01)
        return y0 + s * (y1 - y0)

    def fbm(self, x, y, z, octaves=2):
        total, amp, norm = 0.0, 1.0, 0.0
        for _ in range(octaves):
            total += amp * self(x, y, z)
            norm += amp
            x, y, z, amp = x * 2.03, y * 2.03, z * 2.03, amp * 0.5
        return total / norm

class Grid:
    """The lights by cell, so a spot finds the lights near it without looking at all 800."""
    def __init__(self, points, cell=0.1):
        self.cell = cell
        self.cells = {}
        for i, (x, y, z) in enumerate(points):
            self.cells.setdefault(self._key(x, y, z), []).append(i)

    def _key(self, x, y, z):
        c = self.cell
        return (math.floor(x / c), math.floor(y / c), math.floor(z / c))

    def near(self, x, y, z, radius):
        kx, ky, kz = self._key(x, y, z)
        r = max(1, math.ceil(radius / self.cell))
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                for dz in range(-r, r + 1):
                    yield from self.cells.get((kx + dx, ky + dy, kz + dz), ())

class Trail:
    """A fading glow on each light: what passed over it, and its colour."""
    def __init__(self, count, attack=None):
        self.cover = [0.0] * count
        self.color = [WARM_WHITE] * count
        # the most a light brightens in a frame, so a quick spot glides on rather than pops
        self.attack = attack
        self.start = list(self.cover)

    def deposit(self, i, c, color):
        old = self.cover[i]
        if c <= 0.002:
            return
        if old < 0.01:
            self.color[i] = color
        else:
            w0, h0, s0, l0 = self.color[i]
            w1, h1, s1, l1 = color
            m = c / (old + c)
            self.color[i] = (w0 + (w1 - w0) * m, lerp_h(h0, h1, m), s0 + (s1 - s0) * m, l0 + (l1 - l0) * m)
        if self.attack is not None:
            c = min(c, self.start[i] + self.attack)
        self.cover[i] = max(old, c)

    def fade(self, dt, tau):
        k = math.exp(-dt / tau) if tau > 0 else 0.0
        self.cover = [c * k if c > 0.004 else 0.0 for c in self.cover]
        # once a frame, before the frame's deposits: what the attack counts from
        self.start = list(self.cover)

    def layer(self, i):
        c = self.cover[i]
        return (c, self.color[i]) if c > 0.004 else None

def surface_radius(points, slices=10):
    """The tree's outer radius at a height: a line through each height slice's 90th percentile."""
    groups = {}
    for x, y, z in points:
        groups.setdefault(min(slices - 1, int(y * slices)), []).append(math.hypot(x, z))
    pts = []
    for k, rs in groups.items():
        rs.sort()
        pts.append(((k + 0.5) / slices, rs[int(len(rs) * 0.9)]))
    my = sum(y for y, _ in pts) / len(pts)
    mr = sum(r for _, r in pts) / len(pts)
    slope = sum((y - my) * (r - mr) for y, r in pts) / sum((y - my) ** 2 for y, _ in pts)
    return lambda y: max(0.02, mr + slope * (y - my))


# --- an effect, as a pattern -----------------------------------------------------------------

class Effect(BaseColor):
    """One effect's state and knobs, and the base color that hands each light its layers."""
    name = ""
    # (control name, [(option name, value)], the option it starts on)
    knobs: list = []

    def __init__(self):
        super(Effect, self).__init__()
        self.knob = {}
        self.last = None
        self.layers = []

    def step(self, t, pixels, sound, beating, beat, hue, grain):
        # a run starting again starts the effect again
        if self.last is None or t < self.last:
            self.points = [(p.x, p.y, p.z) for p in pixels]
            self.grid = Grid(self.points)
            self.surface = surface_radius(self.points)
            self.low = self.mid = self.high = 0.5
            self.beat_at = None
            self.reset()
            self.last = t
        dt = min(0.25, t - self.last)
        self.last = t
        self.t = t
        self.sound = sound
        self.beating = beating
        self.beat = beat
        self.hue = hue
        self.grain = grain
        if sound is not None:
            glide = 1 - math.exp(-dt / BAND_GLIDE)
            self.low += (sound.low - self.low) * glide
            self.mid += (sound.mid - self.mid) * glide
            self.high += (sound.high - self.high) * glide
        if beat is not None:
            self.beat_at = t
        self.layers = self.lights(t, dt)

    @property
    def level(self):
        """The bands together."""
        return (self.low + self.mid + self.high) / 3

    @property
    def swell(self):
        """The last beat's swell, 0 to 1, rising and falling away: 0 with Music off."""
        if self.sound is None or self.beat_at is None:
            return 0.0
        since = self.t - self.beat_at
        return smoothstep(0, SWELL_RISE, since) * math.exp(-since / SWELL_FALL)

    def due(self, at):
        """Whether a launch due at time at goes now: while the music's tempo is sure, it waits for a beat."""
        return self.t >= at and (not self.beating or self.beat is not None)

    def drifted(self, color):
        """A palette's colour, turned with the base hue while the palette is the rainbow."""
        return turned(color, self.hue) if self.knob.get("Palette") == RAINBOW else color

    def reset(self):
        pass

    def lights(self, t, dt):
        """Each light's layers for the frame at t, dt after the last: [(cover, (w, h, s, l))]."""
        raise NotImplementedError

    def on_surface(self, y, angle, depth=0.9):
        r = self.surface(y) * depth
        return (r * math.cos(angle), y, r * math.sin(angle))

    def __call__(self, t, blend, spread, pixel_t, pixel_y, pixel):
        out = []
        total = 0.0
        for cover, (w, h, s, l) in self.layers[pixel.idx]:
            if self.grain == "raw":
                cover = 1.0 if cover > RAW_EDGE else 0.0
            if cover > 0:
                out.append([min(1.0, cover), Color(w=w, h=h, s=s, l=l), []])
                total += out[-1][0]
        if total > 1.0:
            for layer in out:
                layer[0] /= total
            total = 1.0
        out = [tuple(layer) for layer in out]
        out.append((1.0 - total, Color(), []))
        return out

class EffectFeature(Feature):
    """An effect's knobs, each a control starting on its option."""
    def __init__(self, effect: Effect):
        self.effect = effect
        controls = []
        for name, options, start in effect.knobs:
            control = Control(name, [Option(n, v) for n, v in options])
            control.set([n for n, _ in options].index(start))
            controls.append(control)
        super(EffectFeature, self).__init__(effect.name, controls)

    @property
    def value(self):
        self.effect.knob = {c.name: c.value for c in self.controls}
        return {"base_color": self.effect}

class EffectPattern(WiredPattern):
    def __init__(self, effect: Effect):
        super(EffectPattern, self).__init__(effect.name)
        self.effect = effect
        self.features = [EffectFeature(effect), BlendFeature()]
        self.update(set_dirty=False)

    def step(self, t, pixels, sound, beating, beat, hue):
        self.effect.step(t, pixels, sound, beating, beat, hue, self.grain)


# --- the ten ---------------------------------------------------------------------------------

AURORA_PALETTES = {
    "green-violet": (GREEN, PURPLE + 0.03),
    "teal-rose": (CYAN + 0.03, MAGENTA + 0.04),
    "ice": (CYAN, BLUE),
}

class Aurora(Effect):
    """Curtains of green and violet that drift and fold up the tree, from 3D noise. The beat swells
    the brightness; the low band drives Speed, the high band the violet share."""
    name = "Aurora"
    knobs = [
        ("Speed", [("slow", 0.05), ("gentle", 0.09), ("lively", 0.16)], "gentle"),
        ("Folds", [("wide", 2.2), ("medium", 3.4), ("fine", 5.0)], "medium"),
        ("Palette", [(n, n) for n in AURORA_PALETTES], "green-violet"),
        ("Softness", [("crisp", 0.22), ("soft", 0.38)], "soft"),
    ]

    def reset(self):
        self.noise = Noise3()
        self.rays = Noise3()
        self.drift = 0.0

    def lights(self, t, dt):
        k = self.knob
        music = self.sound is not None
        self.drift += dt * (banded(k["Speed"], self.low) if music else k["Speed"])
        d, f = self.drift, k["Folds"]
        lo, hi = AURORA_PALETTES[k["Palette"]]
        soft = k["Softness"]
        violet = 0.6 * (self.high - 0.5) if music else 0.0
        bright = 1 + 0.3 * self.swell
        out = []
        for x, y, z in self.points:
            # out to the surface at every height alike, so the narrow top folds as much as the base
            spread = 0.38 / self.surface(y)
            x, z = x * spread, z * spread
            # sheets where the noise crosses its middle, leaning and folding as they go up
            n = self.noise.fbm(x * f + d * 0.6, y * 1.1 - d, z * f - d * 0.4 + y * 0.8)
            ridge = 1.0 - abs(2.0 * n - 1.0)
            sheet = smoothstep(1.0 - soft, 1.0, ridge)
            if sheet <= 0:
                out.append(())
                continue
            rays = self.rays(x * 7, y * 2.0 - d * 2.5, z * 7)
            cover = sheet * (0.45 + 0.55 * rays) * (0.6 + 0.4 * smoothstep(0.0, 0.35, y))
            m = min(1.0, max(0.0, 0.15 + 0.9 * y + 0.6 * (rays - 0.5) + violet))
            out.append(((min(1.0, cover * bright), FULL(lerp_h(lo, hi, m))),))
        return out

FIREFLY_COLORS = {
    "meadow": (0.15, YELLOW - 0.06, 1.0, -0.05),
    "warm white": WARM_WHITE,
    "amber": (0.2, YELLOW + 0.07, 1.0, 0.0),
}

class Fireflies(Effect):
    """A few soft warm lights blink on and fade, wandering in small clusters. A firefly lights on the
    beat; the high band sets how many glow at once."""
    name = "Fireflies"
    knobs = [
        ("Count", [("few", 6), ("some", 12), ("many", 20)], "some"),
        ("Pace", [("lazy", 1.6), ("gentle", 1.0)], "gentle"),
        ("Colour", [(n, n) for n in FIREFLY_COLORS], "amber"),
        ("Size", [("small", 0.055), ("soft", 0.075)], "soft"),
    ]

    def reset(self):
        self.noise = Noise3()
        self.flies = []
        self.clusters = [(random.uniform(0.15, 0.75), random.uniform(0, 2 * math.pi)) for _ in range(3)]

    def _fly(self, start):
        pace = self.knob["Pace"]
        return {
            "cluster": random.randrange(3),
            "seed": random.uniform(0, 100),
            "start": start,
            "rise": 0.6 * pace,
            "hold": 0.5 * pace,
            "fall": 1.3 * pace,
        }

    def lights(self, t, dt):
        k = self.knob
        count = banded(k["Count"], self.high) if self.sound is not None else k["Count"]
        life = 2.4 * k["Pace"]
        # each fly rises, holds and fades; about count glowing at once
        self.flies = [f for f in self.flies if t < f["start"] + f["rise"] + f["hold"] + f["fall"]]
        rate = count / life
        while len(self.flies) < count * 1.5 and random.random() < rate * dt:
            self.flies.append(self._fly(t))
        if not self.flies or (self.beat is not None and len(self.flies) < count * 1.5):
            self.flies.append(self._fly(t))
        color = FIREFLY_COLORS[k["Colour"]]
        size2 = k["Size"] ** 2
        layers = [[] for _ in self.points]
        for f in self.flies:
            age = t - f["start"]
            if age < f["rise"]:
                b = smoothstep(0, f["rise"], age)
            elif age < f["rise"] + f["hold"]:
                b = 1.0
            else:
                b = 1.0 - smoothstep(0, f["fall"], age - f["rise"] - f["hold"])
            # the cluster drifts slowly; its flies wander round it
            cy, ca = self.clusters[f["cluster"]]
            s = f["seed"]
            ca += 0.6 * math.sin(t * 0.05 + f["cluster"])
            cy += 0.08 * math.sin(t * 0.07 + 2 * f["cluster"])
            wy = cy + 0.14 * (self.noise(s, t * 0.15, 0) - 0.5)
            wa = ca + 1.4 * (self.noise(0, s, t * 0.15) - 0.5)
            px, py, pz = self.on_surface(min(0.95, max(0.03, wy)), wa, 0.85)
            for i in self.grid.near(px, py, pz, k["Size"]):
                x, y, z = self.points[i]
                c = b * bump((x - px) ** 2 + (y - py) ** 2 + (z - pz) ** 2, size2)
                if c > 0:
                    layers[i].append((c, color))
        return layers

FIREWORK_PALETTES = {
    RAINBOW: None,
    "gold": [(0.4, YELLOW + 0.05, 1.0, 0.0), (0.7, YELLOW, 0.6, -0.4)],
    "red-green": [FULL(RED), FULL(GREEN)],
    "blue-white": [FULL(BLUE), COOL_WHITE],
}

class Fireworks(Effect):
    """A spark climbs, bursts into a sphere of colour on the cone's surface, and falls with fading
    trails. A rocket goes up on the beat, Rate the most there can be; the low band sets the burst's
    Size."""
    name = "Fireworks"
    knobs = [
        ("Rate", [("rare", 4.0), ("some", 2.5), ("busy", 1.5)], "some"),
        ("Size", [("small", 0.18), ("medium", 0.25), ("large", 0.33)], "medium"),
        ("Palette", [(n, n) for n in FIREWORK_PALETTES], RAINBOW),
        ("Trails", [("short", 0.45), ("long", 0.9)], "short"),
    ]

    def reset(self):
        self.trail = Trail(len(self.points), attack=0.45)
        self.rockets = []
        self.sparks = []
        self.next_launch = 0.3

    def _colors(self):
        palette = FIREWORK_PALETTES[self.knob["Palette"]]
        if palette is None:
            h = random.random()
            palette = [FULL(h), FULL(h + 0.12)]
        return [self.drifted(color) for color in palette]

    def _clamp(self, x, y, z):
        # a spark leaving the cone slides along its surface, so the burst stays on the lights
        y = min(1.0, max(0.0, y))
        r = math.hypot(x, z)
        rmax = self.surface(y)
        if r > rmax:
            x, z = x * rmax / r, z * rmax / r
        return x, y, z

    def lights(self, t, dt):
        k = self.knob
        self.trail.fade(dt, k["Trails"])
        if self.due(self.next_launch):
            self.next_launch = t + k["Rate"] * random.uniform(0.7, 1.3)
            self.rockets.append({
                "start": t,
                "angle": random.uniform(0, 2 * math.pi),
                "top": random.uniform(0.45, 0.8),
                "climb": random.uniform(1.5, 1.9),
            })
        size = banded(k["Size"], self.low) if self.sound is not None else k["Size"]
        heads = []
        for rocket in list(self.rockets):
            age = (t - rocket["start"]) / rocket["climb"]
            if age >= 1:
                self.rockets.remove(rocket)
                cx, cy, cz = self.on_surface(rocket["top"], rocket["angle"], 0.95)
                colors = self._colors()
                n = 40
                for j in range(n):
                    # an even spread of directions over the sphere
                    v = 1 - 2 * (j + 0.5) / n
                    a = j * 2.39996
                    rr = math.sqrt(1 - v * v)
                    speed = size * random.uniform(1.6, 2.0)
                    self.sparks.append({
                        "p": [cx, cy, cz],
                        "v": [rr * math.cos(a) * speed, v * speed, rr * math.sin(a) * speed],
                        "start": t,
                        "life": random.uniform(1.3, 1.8),
                        "color": colors[j % len(colors)],
                    })
                continue
            # it rises out of the dark at the bottom, quickest mid-climb, slowing to its burst
            e = 0.5 - 0.5 * math.cos(math.pi * age)
            y = 0.02 + (rocket["top"] - 0.02) * e
            b = 0.9 * smoothstep(0, 0.2, age)
            heads.append((self.on_surface(y, rocket["angle"] + 0.3 * e, 0.95), b, (0.8, YELLOW + 0.05, 0.5, -0.5)))
        for spark in list(self.sparks):
            age = t - spark["start"]
            if age > spark["life"]:
                self.sparks.remove(spark)
                continue
            p, v = spark["p"], spark["v"]
            drag = math.exp(-2.6 * dt)
            v[0] *= drag
            v[2] *= drag
            v[1] = v[1] * drag - 0.35 * dt
            p[0], p[1], p[2] = self._clamp(p[0] + v[0] * dt, p[1] + v[1] * dt, p[2] + v[2] * dt)
            # each spark comes up over a few frames from the burst, then fades as it falls
            fade = smoothstep(0, 0.12, age) * (1 - age / spark["life"]) ** 1.2
            heads.append((p, fade, spark["color"]))
        size2 = 0.065 ** 2
        for (px, py, pz), b, color in heads:
            for i in self.grid.near(px, py, pz, 0.065):
                x, y, z = self.points[i]
                c = b * bump((x - px) ** 2 + (y - py) ** 2 + (z - pz) ** 2, size2)
                self.trail.deposit(i, c, color)
        return [[layer] if (layer := self.trail.layer(i)) else [] for i in range(len(self.points))]

RIPPLE_PALETTES = {
    "water": [FULL(BLUE), FULL(CYAN), FULL(CYAN - 0.06), FULL(BLUE + 0.97)],
    RAINBOW: None,
    "moonlight": [COOL_WHITE, (0.3, BLUE, 0.6, -0.2), WARM_WHITE],
}

class Ripples(Effect):
    """Rings spread through the tree from a random point, like rain on a pond, crossing and mixing.
    A drop falls on the beat; the bands' level sets the ring's Width."""
    name = "Ripples"
    knobs = [
        ("Rate", [("drizzle", 0.6), ("rain", 1.1), ("shower", 2.0)], "shower"),
        ("Speed", [("slow", 0.16), ("medium", 0.26)], "slow"),
        ("Width", [("fine", 0.06), ("soft", 0.1)], "fine"),
        ("Palette", [(n, n) for n in RIPPLE_PALETTES], "water"),
    ]
    # how far a ring spreads
    reach = 0.4

    def reset(self):
        self.drops = []
        self.next_drop = 0.0

    def lights(self, t, dt):
        k = self.knob
        reach = self.reach
        if self.due(self.next_drop):
            self.next_drop = t + random.expovariate(k["Rate"])
            palette = RIPPLE_PALETTES[k["Palette"]]
            color = self.drifted(FULL(random.random()) if palette is None else random.choice(palette))
            # a drop lands on the surface, where the lights are thickest
            place = self.on_surface(random.uniform(0.05, 0.85), random.uniform(0, 2 * math.pi), 0.85)
            self.drops.append((t, place, color))
        speed = k["Speed"]
        width = banded(k["Width"], self.level) if self.sound is not None else k["Width"]
        self.drops = [d for d in self.drops if (t - d[0]) * speed < reach + width]
        layers = [[] for _ in self.points]
        for start, (cx, cy, cz), color in self.drops:
            age = t - start
            front = age * speed
            # the ring comes up from nothing at the drop, and thins out as it spreads
            amp = smoothstep(0, 0.3, age) * (1 - min(1.0, front / reach)) ** 0.8
            lo, hi = max(0.0, front - width), front + width
            for i in self.grid.near(cx, cy, cz, hi):
                x, y, z = self.points[i]
                d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2)
                if lo <= d <= hi:
                    c = amp * bump((d - front) ** 2, width * width)
                    if c > 0.003:
                        layers[i].append((c, color))
        return layers

LAVA_PALETTES = {
    "lava": ([FULL(RED), FULL(ORANGE), FULL(RED - 0.04)], FULL(PURPLE)),
    "plasma": ([FULL(MAGENTA), FULL(BLUE), FULL(PURPLE)], FULL(CYAN)),
    "ocean": ([FULL(CYAN), FULL(BLUE), FULL(GREEN - 0.04)], FULL(BLUE + 0.95)),
    "sunset": ([FULL(ORANGE), FULL(MAGENTA + 0.05), FULL(YELLOW)], FULL(PURPLE)),
}

class LavaLamp(Effect):
    """Slow coloured blobs (3D metaballs) rise, merge and split. The beat swells the blobs; the low
    band drives Speed."""
    name = "Lava lamp"
    knobs = [
        ("Blobs", [("3", 3), ("5", 5), ("7", 7)], "5"),
        ("Speed", [("drowsy", 0.5), ("slow", 1.0), ("steady", 1.6)], "slow"),
        ("Palette", [(n, n) for n in LAVA_PALETTES], "lava"),
        ("Softness", [("firm", 0.3), ("soft", 0.55)], "soft"),
    ]

    def reset(self):
        self.blobs = [{
            "phase": random.uniform(0, 2 * math.pi),
            "rate": random.uniform(0.03, 0.07),
            "angle": random.uniform(0, 2 * math.pi),
            "spin": random.uniform(-0.12, 0.12),
            "size": random.uniform(0.12, 0.17),
            "color": j,
        } for j in range(7)]
        self.clock = 0.0

    def lights(self, t, dt):
        k = self.knob
        self.clock += dt * (banded(k["Speed"], self.low) if self.sound is not None else k["Speed"])
        colors, background = LAVA_PALETTES[k["Palette"]]
        soft = k["Softness"]
        swell = 1 + 0.15 * self.swell
        centres = []
        for blob in self.blobs[:k["Blobs"]]:
            # each blob rises and sinks the tree's height at its own rate, so they pass and meet
            y = 0.5 - 0.5 * math.cos(blob["phase"] + blob["rate"] * 2 * math.pi * self.clock)
            y = -0.05 + 1.1 * y
            a = blob["angle"] + blob["spin"] * self.clock * 2 * math.pi
            r = self.surface(min(1.0, max(0.0, y))) * 0.55
            # smaller up where the tree is narrow
            size = swell * blob["size"] * (0.55 + 0.45 * (1 - min(1.0, max(0.0, y))))
            centres.append((r * math.cos(a), y, r * math.sin(a), size * size, colors[blob["color"] % len(colors)]))
        out = []
        for x, y, z in self.points:
            field = 0.0
            parts = []
            for cx, cy, cz, s2, color in centres:
                f = s2 / ((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2 + 1e-4)
                field += f
                parts.append((f, color))
            cover = smoothstep(1 - soft, 1 + soft, field)
            layers = [(0.08 * (1 - cover), background)]
            if cover > 0:
                layers += [(cover * f / field, color) for f, color in parts if f / field > 0.02]
            out.append(layers)
        return out

COMET_PALETTES = {
    "ice": [(0.4, CYAN, 0.6, 0.0), (0.3, BLUE, 0.8, 0.0), (0.4, CYAN - 0.04, 0.5, 0.0)],
    RAINBOW: [FULL(MAGENTA), FULL(GREEN), FULL(ORANGE)],
    "ember": [FULL(ORANGE), FULL(YELLOW), FULL(RED)],
}

class Comets(Effect):
    """Two or three comets orbit the cone at different heights and speeds, leaving trails. The beat
    gives the comets a push, a surge in Speed; the bands' level sets the Tail."""
    name = "Comets"
    knobs = [
        ("Comets", [("1", 1), ("2", 2), ("3", 3)], "3"),
        ("Speed", [("slow", 0.1), ("medium", 0.16), ("quick", 0.24)], "medium"),
        ("Tail", [("short", 0.5), ("medium", 1.0), ("long", 1.8)], "medium"),
        ("Palette", [(n, n) for n in COMET_PALETTES], "ice"),
    ]

    def reset(self):
        self.trail = Trail(len(self.points), attack=0.3)
        self.orbits = [
            {"y": 0.22, "rate": 1.0, "angle": 0.0, "dir": 1, "bob": 0.07},
            {"y": 0.5, "rate": 1.3, "angle": 2.1, "dir": -1, "bob": 0.05},
            {"y": 0.72, "rate": 0.8, "angle": 4.2, "dir": 1, "bob": 0.04},
        ]
        self.turned = [0.0] * 3

    def lights(self, t, dt):
        k = self.knob
        music = self.sound is not None
        self.trail.fade(dt, (banded(k["Tail"], self.level) if music else k["Tail"]) * 0.6)
        speed = k["Speed"] * (1 + self.swell)
        colors = [self.drifted(color) for color in COMET_PALETTES[k["Palette"]]]
        heads = []
        size2 = 0.07 ** 2
        for j, orbit in enumerate(self.orbits[:k["Comets"]]):
            self.turned[j] += dt * speed * orbit["rate"] * 2 * math.pi
            a = orbit["angle"] + orbit["dir"] * self.turned[j]
            y = orbit["y"] + orbit["bob"] * math.sin(self.turned[j] * 1.5)
            px, py, pz = self.on_surface(y, a, 0.92)
            heads.append((px, py, pz))
            for i in self.grid.near(px, py, pz, 0.07):
                x, yy, z = self.points[i]
                self.trail.deposit(i, bump((x - px) ** 2 + (yy - py) ** 2 + (z - pz) ** 2, size2), colors[j])
        out = []
        for i, (x, y, z) in enumerate(self.points):
            layers = []
            if (layer := self.trail.layer(i)):
                layers.append(layer)
            # the head itself, whiter than its tail
            for px, py, pz in heads:
                d2 = (x - px) ** 2 + (y - py) ** 2 + (z - pz) ** 2
                if d2 < 0.0036:
                    layers.append((0.5 * bump(d2, 0.0036), (0.9, CYAN, 0.2, -0.3)))
            out.append(layers)
        return out

class Hearth(Effect):
    """A warm candle and ember flicker, brightest at the bottom and cooling to the top. The beat
    flares the flames' Height; the low band sets Height, the high band the Embers."""
    name = "Hearth"
    knobs = [
        ("Height", [("low", 0.4), ("fire", 0.6), ("blaze", 0.85)], "fire"),
        ("Flicker", [("calm", 0.45), ("lively", 0.8)], "calm"),
        ("Embers", [("none", 0.0), ("few", 2.5), ("many", 7.0)], "few"),
    ]

    def reset(self):
        self.noise = Noise3()
        self.embers = []
        self.rise = 0.0

    def lights(self, t, dt):
        k = self.knob
        height, embers = k["Height"], k["Embers"]
        if self.sound is not None:
            height = banded(height, self.low) * (1 + 0.2 * self.swell)
            embers = banded(embers, self.high)
        self.rise += dt * k["Flicker"]
        if random.random() < embers * dt:
            self.embers.append({
                "start": t,
                "angle": random.uniform(0, 2 * math.pi),
                "y": random.uniform(0.05, 0.25),
                "speed": random.uniform(0.08, 0.16),
                "life": random.uniform(2.5, 4.0),
                "drift": random.uniform(-0.5, 0.5),
            })
        self.embers = [e for e in self.embers if t - e["start"] < e["life"]]
        layers = []
        r = self.rise
        for x, y, z in self.points:
            # heat falls off with height, broken up by noise rising through the tree; the flames'
            # top rises and falls with a slower noise, in tongues, not a level line
            n = self.noise.fbm(x * 5, y * 3.5 - r, z * 5 + r * 0.25)
            top = height * (0.7 + 0.6 * self.noise(x * 3 + 40, y - r * 0.5, z * 3))
            base = max(0.0, 1.0 - y / top)
            heat = base ** 1.2 * (0.35 + 0.95 * n)
            # and a dim glow cooling up the rest of the tree
            heat = min(1.0, max(heat, 0.07 * (1 - y) * (0.5 + n)))
            if heat < 0.03:
                layers.append([])
                continue
            hue = lerp_h(RED + 0.02, YELLOW + 0.04, smoothstep(0.15, 0.9, heat))
            w = 0.6 * smoothstep(0.7, 1.0, heat)
            layers.append([(min(1.0, heat * 1.3), (w, hue, 1.0, 0.0))])
        size2 = 0.045 ** 2
        for e in self.embers:
            age = t - e["start"]
            b = smoothstep(0, 0.5, age) * (1 - smoothstep(e["life"] * 0.4, e["life"], age))
            py = e["y"] + age * e["speed"]
            px, py, pz = self.on_surface(min(1.0, py), e["angle"] + e["drift"] * age, 0.9)
            for i in self.grid.near(px, py, pz, 0.045):
                x, y, z = self.points[i]
                c = b * bump((x - px) ** 2 + (y - py) ** 2 + (z - pz) ** 2, size2)
                if c > 0.01:
                    layers[i] = layers[i] + [(c * 0.9, FULL(ORANGE - 0.03))]
        return layers

class Lightning(Effect):
    """A dark storm with a sudden branching bolt down the tree, then an afterglow: one quick flash,
    no strobing. A bolt strikes on a bar line, Interval the least time between; the low band lights
    the clouds."""
    name = "Lightning"
    knobs = [
        ("Interval", [("often", 4.5), ("sometimes", 8.0), ("rarely", 14.0)], "sometimes"),
        ("Branches", [("1", 1), ("2", 2), ("3", 3)], "2"),
        ("Afterglow", [("quick", 0.45), ("slow", 1.1)], "slow"),
        ("Sky", [("black", 0.0), ("clouds", 0.07)], "clouds"),
    ]

    def reset(self):
        self.noise = Noise3()
        self.trail = Trail(len(self.points))
        self.next_strike = 1.5
        self.flash = 0.0
        self.struck = None  # when the last bolt struck, on the run's clock

    def _path(self, y, angle, stop):
        """A jagged line down the surface from height y to stop."""
        points = [self.on_surface(y, angle, 0.8)]
        while y > stop:
            y -= random.uniform(0.04, 0.08)
            angle += random.uniform(-0.45, 0.45)
            points.append(self.on_surface(max(stop, y), angle, random.uniform(0.75, 1.0)))
        return points

    def _strike(self):
        top = self._path(1.0, random.uniform(0, 2 * math.pi), 0.0)
        paths = [top]
        for _ in range(self.knob["Branches"] - 1):
            j = random.randrange(2, max(3, len(top) // 2))
            y = top[j][1]
            angle = math.atan2(top[j][2], top[j][0])
            branch = self._path(y, angle + random.choice([-0.5, 0.5]), max(0.0, y - random.uniform(0.25, 0.45)))
            paths.append([top[j]] + branch[1:])
        width = 0.05
        for path in paths:
            for a, b in zip(path, path[1:]):
                middle = tuple((p + q) / 2 for p, q in zip(a, b))
                half = math.dist(a, b) / 2
                for i in self.grid.near(*middle, half + width):
                    self.trail.deposit(i, bump(seg_dist2(self.points[i], a, b), width * width), (1.0, BLUE, 0.35, -0.2))
        self.flash = 1.0

    def lights(self, t, dt):
        k = self.knob
        self.trail.fade(dt, k["Afterglow"])
        # the bolt's glow cools from blue-white to violet as it fades
        for i, c in enumerate(self.trail.cover):
            if c > 0.004:
                w, h, s, l = self.trail.color[i]
                self.trail.color[i] = (w * math.exp(-dt / 0.25), lerp_h(h, PURPLE, 1 - math.exp(-dt / 0.6)), min(1.0, s + dt * 1.5), l)
        if t >= self.next_strike and (not self.beating or (self.beat is not None and self.beat % 4 == 0)):
            self.next_strike = t + k["Interval"] * random.uniform(0.8, 1.25)
            self.struck = t
            self._strike()
        flash = self.flash
        self.flash *= math.exp(-dt / 0.12)
        sky = banded(k["Sky"], self.low) if self.sound is not None else k["Sky"]
        out = []
        for i, (x, y, z) in enumerate(self.points):
            layers = []
            if (layer := self.trail.layer(i)):
                layers.append(layer)
            if sky or flash > 0.01:
                n = self.noise.fbm(x * 3 + t * 0.04, y * 2, z * 3 - t * 0.03) if sky else 0.5
                cloud = smoothstep(0.5, 0.8, n) * smoothstep(0.2, 0.9, y)
                c = sky * cloud + 0.12 * flash * (0.4 + 0.6 * cloud)
                if c > 0.004:
                    layers.append((c, (0.2, BLUE + 0.95, 0.5, -0.2)))
            out.append(layers)
        return out

DRIP_PALETTES = {
    "paint box": [FULL(RED), FULL(YELLOW), FULL(BLUE), FULL(GREEN), FULL(MAGENTA)],
    "candy": [FULL(MAGENTA + 0.04), FULL(CYAN), FULL(YELLOW)],
    "ocean": [FULL(BLUE), FULL(CYAN), FULL(GREEN - 0.03)],
}

class Drips(Effect):
    """Paint drips run down from the top, pooling and changing colour at the bottom. A drip starts on
    the beat; the bands' level sets Speed."""
    name = "Drips"
    knobs = [
        ("Rate", [("slow", 0.5), ("steady", 0.9), ("busy", 1.6)], "steady"),
        ("Speed", [("ooze", 0.09), ("run", 0.16)], "run"),
        ("Palette", [(n, n) for n in DRIP_PALETTES], "paint box"),
        ("Pool", [("shallow", 0.1), ("deep", 0.2)], "shallow"),
    ]

    def reset(self):
        self.trail = Trail(len(self.points), attack=0.35)
        self.drips = []
        self.next_drip = 0.0
        first = DRIP_PALETTES[self.knob["Palette"]][0]
        self.pool = [0.35] * len(self.points)
        self.pool_color = [first] * len(self.points)
        self.pool_target = [first] * len(self.points)
        self.pool_lift = [0.35] * len(self.points)

    def lights(self, t, dt):
        k = self.knob
        palette = DRIP_PALETTES[k["Palette"]]
        pool_top = k["Pool"]
        speed = banded(k["Speed"], self.level) if self.sound is not None else k["Speed"]
        self.trail.fade(dt, 1.6)
        if self.due(self.next_drip):
            self.next_drip = t + random.expovariate(k["Rate"])
            self.drips.append({
                "start": t,
                "y": random.uniform(0.88, 0.97),
                "angle": random.uniform(0, 2 * math.pi),
                "wobble": random.uniform(-0.3, 0.3),
                "color": random.choice(palette),
                "fallen": 0.0,
            })
        size2 = 0.05 ** 2
        for drip in list(self.drips):
            age = t - drip["start"]
            # a bead forms, then runs, picking up speed
            b = smoothstep(0, 0.6, age)
            run = age - 0.6
            if run > 0:
                drip["fallen"] += dt * speed * (0.3 + run if run < 1.4 else 1.0)
            y = drip["y"] - drip["fallen"]
            if y <= pool_top * 0.6:
                self.drips.remove(drip)
                self._land(drip, pool_top)
                continue
            px, py, pz = self.on_surface(y, drip["angle"] + drip["wobble"] * (drip["y"] - y), 0.9)
            for i in self.grid.near(px, py, pz, 0.05):
                x, yy, z = self.points[i]
                self.trail.deposit(i, b * bump((x - px) ** 2 + (yy - py) ** 2 + (z - pz) ** 2, size2), drip["color"])
        # the pool settles back to an even glow between drips
        settle = 1 - math.exp(-dt / 3.0)
        ease = 1 - math.exp(-dt / 0.5)
        out = []
        for i, (x, y, z) in enumerate(self.points):
            layers = []
            if (layer := self.trail.layer(i)):
                layers.append(layer)
            depth = 1 - smoothstep(pool_top * 0.6, pool_top, y)
            if depth > 0:
                # the pool eases toward where the last landing left it, then settles
                w0, h0, s0, l0 = self.pool_color[i]
                w1, h1, s1, l1 = self.pool_target[i]
                self.pool_color[i] = (w0 + (w1 - w0) * ease, lerp_h(h0, h1, ease), s0 + (s1 - s0) * ease, l0 + (l1 - l0) * ease)
                self.pool[i] += (self.pool_lift[i] - self.pool[i]) * ease
                self.pool_lift[i] += (0.35 - self.pool_lift[i]) * settle
                layers.append((depth * self.pool[i], self.pool_color[i]))
            out.append(layers)
        return out

    def _land(self, drip, pool_top):
        # the drip's colour spreads round the pool from where it lands
        ax, az = math.cos(drip["angle"]), math.sin(drip["angle"])
        w0, h0, s0, l0 = drip["color"]
        for i, (x, y, z) in enumerate(self.points):
            if y > pool_top:
                continue
            r = math.hypot(x, z) or 1.0
            near = (x / r) * ax + (z / r) * az  # cos of the angle between, so no seam
            m = 0.7 * smoothstep(0.55, 1.0, near)
            if m > 0:
                w1, h1, s1, l1 = self.pool_target[i]
                self.pool_target[i] = (w1 + (w0 - w1) * m, lerp_h(h1, h0, m), s1 + (s0 - s1) * m, l1 + (l0 - l1) * m)
                self.pool_lift[i] = max(self.pool_lift[i], 0.35 + 0.55 * m)

HEART_COLORS = {
    "red": FULL(RED),
    "rose": FULL(MAGENTA + 0.07),
    "violet": FULL(PURPLE),
    "warm white": (0.9, ORANGE, 0.6, -0.6),
}

class Heartbeat(Effect):
    """A double pulse from the tree's core outwards at Rate. While the music's tempo is sure the
    pulse fires on its beat in place of Rate; the low band sets Reach."""
    name = "Heartbeat"
    knobs = [
        ("Rate", [("resting", 54), ("calm", 66), ("lively", 84), ("racing", 100)], "calm"),
        ("Colour", [(n, n) for n in HEART_COLORS], "red"),
        ("Reach", [("core", 0.35), ("half", 0.55), ("whole", 0.85)], "whole"),
        ("Softness", [("crisp", 0.14), ("soft", 0.2)], "soft"),
    ]

    def reset(self):
        self.phase = 0.0

    def lights(self, t, dt):
        k = self.knob
        rate = self.sound.bpm if self.beating else k["Rate"]
        # the phase runs at the rate, so a change of rate never jumps a pulse; a beat pulls it onto
        # the music's
        self.phase += dt * rate / 60
        if self.beat is not None:
            self.phase = round(self.phase)
        reach, width = k["Reach"], k["Softness"]
        if self.sound is not None:
            reach = banded(reach, self.low)
        speed = reach / 1.2
        color = HEART_COLORS[k["Colour"]]
        beats = []
        n = math.floor(self.phase)
        for b in (n, n - 1):
            since = (self.phase - b) * 60 / rate
            # lub, then a softer dub
            beats.append((since, 1.0))
            beats.append((since - 0.32, 0.65))
        # each pulse swells at the core over a few frames, then thins as it spreads
        fronts = [(s * speed, amp * smoothstep(0, 0.2, s) * (1 - min(1.0, s * speed / (reach + width))) ** 2.2)
                  for s, amp in beats if s >= 0]
        cx, cy, cz = 0.0, 0.38, 0.0
        out = []
        for x, y, z in self.points:
            d = math.sqrt((x - cx) ** 2 + ((y - cy) * 0.8) ** 2 + (z - cz) ** 2)
            c = 0.04 * (1 - smoothstep(reach * 0.6, reach + width, d))
            for front, amp in fronts:
                if amp > 0 and abs(d - front) < width:
                    c += amp * bump((d - front) ** 2, width * width)
            out.append([(min(1.0, c), color)] if c > 0.003 else [])
        return out

EFFECTS = [Aurora, Fireflies, Fireworks, Ripples, LavaLamp, Comets, Hearth, Lightning, Drips, Heartbeat]
