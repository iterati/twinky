import io
import math
from pytweening import linear, easeInOutCubic, easeInOutSine
import random
import time

from control import WiredPattern
from layout import normalize
from param import getv, Curve
from streamer import Streamer, getv_streamers

# A light's color as it goes to the tree: W, R, G and B, each 0 to 255. Frames are mixed in these.
WRGB = tuple[float, float, float, float]

FRAME = 1/16

def wait_for(next_frame: float) -> float:
    """Sleeps until next_frame and gives the frame after it. Once more than a frame late, it
    counts again from now rather than rushing frames out to catch up."""
    delay = next_frame - time.time()
    if delay > 0:
        time.sleep(delay)
    elif delay < -FRAME:
        return time.time() + FRAME
    return next_frame + FRAME

class Pixel:
    def __init__(self, idx, x, y, z):
        self.idx = idx  # across every strand
        self.x = x
        self.y = y
        self.z = z
        self.t = ((math.atan2(z, x) / math.pi) + 1) / 2

class SmoothNoise:
    """For each light, a value from 0 to 1 easing between random targets at its own rate and phase."""
    targets = 32

    def __init__(self, count: int):
        self.rates = [random.uniform(1.0, 3.0) for _ in range(count)]
        self.phases = [random.uniform(0, self.targets) for _ in range(count)]
        self.values = [[random.random() for _ in range(self.targets)] for _ in range(count)]

    def __call__(self, idx: int, t: float) -> float:
        s = (t * self.rates[idx]) + self.phases[idx]
        k = math.floor(s)
        values = self.values[idx]
        a = values[k % self.targets]
        b = values[(k + 1) % self.targets]
        return a + ((b - a) * easeInOutSine(s - k))

class Run:
    """One turn of a pattern, from when it starts to fade in, with its own clock, sparkles and streamers."""
    def __init__(self, pattern: WiredPattern, start: float):
        self.pattern = pattern
        self.start = start
        self.sparkles: dict[int, float] = {}  # light index: when it lit, on the run's clock
        self.next_sparkle = 0.0
        self.streamers: list[Streamer] = []
        self.next_streamer = 0.0
        self.last_streamer_t: float | None = None

class Change:
    """A fade from a source (a live run or a frozen frame) to a run."""
    def __init__(self, source: Run | list[WRGB], run: Run, start: float, length: float, shape: str):
        self.source = source
        self.run = run
        self.start = start
        self.length = length
        self.shape = shape

class Blender:
    sparkle_delay = 0.25
    streamer_delay = 0.25
    pattern_length = 60.0
    transition_length = 6.0
    glide_length = 0.5
    # the soft edge of the sweep, rise and spiral transitions, as a share of their way across
    transition_edge = 0.25
    spiral_turns = 2

    def __init__(self,
                 patterns: list[WiredPattern],
                 lights,
                 start_idx: int | None=None,
                 pause_change: bool=False):
        self.lights = lights
        self.patterns = patterns
        self.pause_change = pause_change
        self._blend_func = Curve(linear, [(0, 0), (66, 1)])
        lights_layout = [light for interface in lights.interfaces for light in interface.layout]
        self.pixels = [Pixel(idx, **light) for idx, light in enumerate(normalize(lights_layout))]
        self.noise = {name: SmoothNoise(len(self.pixels)) for name in ["flash", "flicker", "flitter", "flux"]}
        self.running = False
        pattern = self.patterns[
            start_idx
            if start_idx is not None else
            random.randint(0, len(patterns) - 1)
        ]
        pattern.randomize()
        self.run = Run(pattern, 0.0)
        self.next_pattern = self._pick_next()
        self.change: Change | None = None
        self.frame: list[WRGB] | None = None
        self.glide_from: list[WRGB] | None = None
        self.glide_start = 0.0
        self._init_t = 0.0
        self._t = 0.0

    @property
    def pattern(self) -> WiredPattern:
        return self.run.pattern

    @property
    def transitioning(self) -> bool:
        return self.change is not None

    def _pick_next(self) -> WiredPattern:
        choice = random.choice([p for p in self.patterns if p.name != self.pattern.name])
        choice.randomize()
        return choice

    def init(self, t: float):
        for interface in self.lights.interfaces:
            interface.set_mode("rt")

        self._init_t = t
        self._t = t
        self.run = Run(self.pattern, t)
        self.change = None
        self.running = True

    def _spawn(self, run: Run, t: float):
        pattern = run.pattern
        if t >= run.next_sparkle:
            run.next_sparkle += self.sparkle_delay
            if pattern.grain == "raw":
                run.sparkles.clear()
            else:
                run.sparkles = {i: lit for i, lit in run.sparkles.items() if t - lit < 2 * self.sparkle_delay}
            count = len(self.pixels)
            for idx in random.choices(range(count), k=int(count * getv(pattern.sparkles, t))):
                run.sparkles.setdefault(idx, t)

        if t >= run.next_streamer:
            run.next_streamer += self.streamer_delay
            streamer_defs = getv_streamers(pattern.streamers, t, run.last_streamer_t)
            run.last_streamer_t = t
            run.streamers = [streamer for streamer in run.streamers if streamer.alive(t)]
            run.streamers.extend([
                Streamer(
                    t,
                    t,
                    streamer_def.func,
                    streamer_def.move_dir,
                    streamer_def.spin_dir,
                    streamer_def.angle,
                    streamer_def.spin,
                    streamer_def.length,
                    streamer_def.width,
                    streamer_def.lifetime,
                )
                for streamer_def in streamer_defs
            ])

    def _sparkle(self, run: Run, idx: int, t: float) -> float:
        # raw sparkles are on or off; smooth ones fade in and out over their life
        lit = run.sparkles.get(idx)
        if lit is None:
            return 0.0
        if run.pattern.grain == "raw":
            return 1.0
        return math.sin(math.pi * min(1.0, (t - lit) / (2 * self.sparkle_delay))) ** 2

    def _render(self, run: Run, now: float) -> list[WRGB]:
        pattern = run.pattern
        t = now - run.start
        self._spawn(run, t)
        clock = now - self._init_t
        blend_h = getv(self._blend_func, clock)
        spread_h = getv(pattern.spread, t)
        spin = getv(pattern.spin, t)
        spiral = getv(pattern.spiral, t)
        topologies = [topology(t) for topology in pattern.topologies]
        streamers = [(streamer, *streamer.place(t)) for streamer in run.streamers]
        smooth = pattern.grain != "raw"
        effects = {
            "flash": getv(pattern.flash, t),
            "flicker": getv(pattern.flicker, t),
            "flitter": getv(pattern.flitter, t),
            "flux": getv(pattern.flux, t),
        }

        def grain(name: str, idx: int) -> float:
            return effects[name] * (self.noise[name](idx, clock) if smooth else random.random())

        frame = []
        for pixel in self.pixels:
            pixel_t = (pixel.t + spin + (spiral * pixel.y)) % 1
            for topology in topologies:
                pixel_t = topology(pixel_t, pixel.y)

            sparkle = self._sparkle(run, pixel.idx, t)
            covering = []
            for streamer, miny, angle in streamers:
                c = streamer.coverage(pixel, miny, angle)
                if c > 0:
                    covering.append((streamer, c))

            w = r = g = b = 0.0
            for weight, color, suppress in pattern.base_color(t, blend_h, spread_h, pixel_t, pixel.y):
                if effects["flash"] and "flash" not in suppress and color.l != -1.0:
                    color.l -= grain("flash", pixel.idx)
                if effects["flicker"] and "flicker" not in suppress:
                    color.w += grain("flicker", pixel.idx)
                if effects["flitter"] and "flitter" not in suppress and color.s != 0.0:
                    color.s -= grain("flitter", pixel.idx)
                if effects["flux"] and "flux" not in suppress:
                    color.h += grain("flux", pixel.idx) - (effects["flux"] / 2)

                # each soft sparkle or streamer edge splits the color into a part with and a part without
                parts = [(weight, color)]
                if sparkle and "sparkles" not in suppress:
                    parts = [(weight * (1 - sparkle), color), (weight * sparkle, pattern.sparkle_func(color))]
                if "streamers" not in suppress:
                    for streamer, c in covering:
                        split = []
                        for part_weight, part_color in parts:
                            split.append((part_weight * (1 - c), part_color))
                            split.append((part_weight * c, streamer.func(part_color, t, blend_h)))
                        parts = split

                for weight, color in parts:
                    if weight > 0:
                        cw, cr, cg, cb = color.as_wrgb()
                        w += weight * cw
                        r += weight * cr
                        g += weight * cg
                        b += weight * cb
            frame.append((w, r, g, b))

        return frame

    def _mix(self, a: list[WRGB], b: list[WRGB], progress: float, shape: str="crossfade") -> list[WRGB]:
        """a turning into b, progress (0 to 1) of the way, eased once a frame. Every shape but the
        crossfade turns each light over in its turn: by its angle, its height, or its place on a
        spiral winding up the tree."""
        mix = easeInOutCubic(min(1.0, max(0.0, progress)))
        edge = self.transition_edge
        frame = []
        for pixel, ca, cb in zip(self.pixels, a, b):
            if shape == "crossfade":
                m = mix
            else:
                if shape == "sweep":
                    key = pixel.t
                elif shape == "rise":
                    key = pixel.y
                else:
                    key = ((pixel.y * self.spiral_turns) + pixel.t) / (self.spiral_turns + 1)
                m = min(1.0, max(0.0, ((mix * (1 + edge)) - key) / edge))
            frame.append(tuple(x + ((y - x) * m) for x, y in zip(ca, cb)))
        return frame

    @property
    def pattern_name(self) -> str:
        if self.change is not None:
            return f"{self.pattern.name}->{self.change.run.pattern.name}"
        else:
            pattern_state = "?"
            if self.pattern.configured:
                pattern_state = "!"
            if self.pattern.dirty:
                pattern_state = "*"
            return f"{self.pattern.name}{pattern_state}"

    @property
    def time_str(self) -> str:
        if self.change is not None:
            left = self.change.start + self.change.length - self._t
        else:
            left = self.run.start + self.pattern_length - self._t
        if self.pause_change:
            if self.change is not None:
                return f"(PAUSED) -{left:.2f}"
            else:
                return f"(PAUSED) {(self._t - self._init_t):.2f}"
        return f"-{left:.2f}"

    def start_transition(self, next: int | None=None):
        if next is not None:
            self.next_pattern = self.patterns[next]
        self.next_pattern.randomize()
        source: Run | list[WRGB] = self.run
        if self.frame is not None and (self.change is not None or self.next_pattern is self.pattern):
            # a switch in the middle of a change, or to the pattern on show: fade from the frame on
            # show, frozen, so nothing jumps back
            source = self.frame
            if self.change is not None:
                self.run = self.change.run
        self.change = Change(
            source,
            Run(self.next_pattern, self._t),
            self._t,
            self.transition_length,
            self.next_pattern.transition,
        )

    def glide(self):
        # eases the tree from the frame on show into the pattern's new settings
        if self.frame is not None:
            self.glide_from = self.frame
            self.glide_start = self._t

    def render(self, t: float) -> list[WRGB]:
        self._t = t
        if (self.change is None
                and not self.pause_change
                and t >= self.run.start + self.pattern_length):
            self.start_transition()
        if self.change is not None and t >= self.change.start + self.change.length:
            self.run = self.change.run
            self.change = None
            self.next_pattern = self._pick_next()

        if self.change is None:
            frame = self._render(self.run, t)
        else:
            change = self.change
            source = change.source if isinstance(change.source, list) else self._render(change.source, t)
            frame = self._mix(source, self._render(change.run, t), (t - change.start) / change.length, change.shape)

        if self.glide_from is not None:
            progress = (t - self.glide_start) / self.glide_length
            if progress >= 1:
                self.glide_from = None
            else:
                frame = self._mix(self.glide_from, frame, progress)

        self.frame = frame
        return frame

    def write(self, frame: list[WRGB]):
        start = 0
        for interface in self.lights.interfaces:
            end = start + len(interface.layout)
            data = bytes(int(c + 0.5) for light in frame[start:end] for c in light)
            interface.set_rt_frame_socket(io.BytesIO(data), 3)
            start = end

    def animate(self):
        start_time = time.time()
        self.init(start_time)
        next_frame = start_time + FRAME
        while self.running:
            colors = self.render(time.time())
            self.write(colors)
            next_frame = wait_for(next_frame)
