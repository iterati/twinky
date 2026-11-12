import io
import math
from pytweening import linear, easeInOutCubic, easeInOutSine
import random
import time
from typing import Callable

from control import MusicFeature, WiredPattern
from layout import normalize
from music import BeatClock, Sound
from param import getv, Curve
from streamer import Streamer, StreamerValue, getv_streamers
from utils import coverage

# A light's color as it goes to the tree: W, R, G and B, each 0 to 255. Frames are mixed in these.
WRGB = tuple[float, float, float, float]

FRAME = 1/16

# The music links. A beat counts once the page is this sure of it
BEAT_CONFIDENCE = 0.3
# The base hue's anchors on xled_plus's 8col wheel, gliding from blue for dark music through
# violet and pink to orange for bright
COOL_HUE = 1.0
WARM_HUE = 0.5
PALETTE_GLIDE = 8.0
# A flash's decay, in seconds, from groove to drive, and the sectors that chase round the trunk
FLASH_DECAY = (0.4, 0.12)
SECTORS = 4
SECTOR_EDGE = 0.05
# With Feel: a control's glide from groove to drive, a change's length in groove, and in drive
# the bars a change lasts, from one bar line to another
FEEL_GLIDE = (2.0, 0.25)
GROOVE_CHANGE = 12.0
DRIVE_BARS = 2

def wrap(x: float) -> float:
    """x round a turn, the short way: from -0.5 to 0.5."""
    return ((x + 0.5) % 1) - 0.5

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
        # called with each frame's bytes as write sends them, every strand's in turn
        self.on_frame: Callable[[bytes], None] | None = None

        # the music: its feature and beat clock, and what they give the frame on show
        self.music = MusicFeature()
        self.beat = BeatClock()
        self.links = self.music.value
        self.sound: Sound | None = None  # None with Music off or no page listening
        self.beating = False  # a tempo the page is sure of
        self.on_beat: tuple[int, float] | None = None  # the beat this frame is nearest, its number and time
        self._last_beat: int | None = None
        self._last_position: float | None = None
        self._flash: tuple[int, float] | None = None  # the last flash's beat and time
        self.dt = 0.0  # the seconds since the frame before, as _listen takes them
        self.sparkle_roll = self.sparkle_delay
        self.spin_angle = 0.0
        self.hue_shift = 0.0
        # the remote's spin ring: a turn it adds for every light, beside the spin lock's, kept
        # where the drag leaves it
        self.ring_angle = 0.0

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

    def _listen(self, t: float):
        """Reads the beat clock for the frame at t: the sound, the beat the frame is nearest, and the
        sparkles' roll, spin and base hue the music sets."""
        dt = min(max(t - self._t, 0.0), 0.25)
        self.dt = dt
        links = self.music.value
        sound = self.beat.at(t, links["latency"]) if links["on"] else None
        self.links = links
        self.sound = sound
        self.beating = sound is not None and sound.bpm > 0 and sound.confidence >= BEAT_CONFIDENCE
        self.on_beat = None
        glide = 1 - math.exp(-3 * dt / PALETTE_GLIDE)
        locked = self.beating and links["spin"]
        if self.beating:
            # the frame nearest each beat takes it
            per_frame = FRAME * sound.bpm / 60
            n = math.floor(sound.beat + (per_frame / 2))
            if self._last_beat is not None and n > self._last_beat:
                self.on_beat = (n, t + ((n - sound.beat) * 60 / sound.bpm))
                if links["flash"]:
                    self._flash = self.on_beat
            if locked and self._last_position is not None:
                # one turn every so many bars at the beat's pace, a jump in the beat moving nothing,
                # drawn round to its place in the bars, a turn starting on every so many bar lines
                bars = 4 * links["spin"]
                step = sound.beat - self._last_position
                if abs(step) < 4 * per_frame:
                    self.spin_angle += step / bars
                self.spin_angle += wrap((sound.beat / bars) - self.spin_angle) * (1 - math.exp(-dt / 2))
            self._last_beat = n
            self._last_position = sound.beat
        else:
            self._last_beat = None
            self._last_position = None
        if not locked:
            # let go, the tree turns back home the short way
            self.spin_angle -= wrap(self.spin_angle) * glide

        self.sparkle_roll = self.sparkle_delay
        if sound is not None and links["sparkles"]:
            self.sparkle_roll += (FRAME - self.sparkle_delay) * sound.high

        # while the music pulls it, the base hue leaves its clock and glides toward the tone's anchor;
        # after, the shift from the clock glides away
        if sound is not None and links["palette"]:
            anchor = COOL_HUE + ((WARM_HUE - COOL_HUE) * sound.tone)
            hue = getv(self._blend_func, self._t - self._init_t) + self.hue_shift
            hue += wrap(anchor - hue) * glide
            self.hue_shift = hue - getv(self._blend_func, t - self._init_t)
        else:
            self.hue_shift -= wrap(self.hue_shift) * glide

    @property
    def feel(self) -> float | None:
        """The music's drive while Feel is on and the page listens, else None."""
        if self.sound is None or not self.links["feel"]:
            return None
        return self.sound.drive

    @property
    def lands_on_bars(self) -> bool:
        feel = self.feel
        return feel is not None and feel >= 0.5 and self.beating

    def _flash_at(self, t: float) -> float:
        """The flash's envelope at t: full on its beat's frame, decaying faster the more the drive."""
        if self._flash is None or self.sound is None or not self.links["flash"]:
            return 0.0
        slow, fast = FLASH_DECAY
        decay = slow + ((fast - slow) * self.sound.drive)
        since = max(0.0, t - self._flash[1])
        return max(0.0, 1 - (since / decay)) ** 2

    def _launch(self, run: Run, streamer_defs: list[StreamerValue], t: float, step: float | None=None):
        # a step turns each streamer round the trunk, putting one with no angle of its own at the step
        run.streamers.extend([
            Streamer(
                t,
                t,
                streamer_def.func,
                streamer_def.move_dir,
                streamer_def.spin_dir,
                streamer_def.angle if step is None else (
                    step if streamer_def.angle is None else streamer_def.angle + step),
                streamer_def.spin,
                streamer_def.length,
                streamer_def.width,
                streamer_def.lifetime,
            )
            for streamer_def in streamer_defs
        ])

    def _spawn(self, run: Run, t: float):
        pattern = run.pattern
        sound = self.sound
        if t >= run.next_sparkle:
            run.next_sparkle += self.sparkle_roll
            if pattern.grain == "raw":
                run.sparkles.clear()
            else:
                run.sparkles = {i: lit for i, lit in run.sparkles.items() if t - lit < 2 * self.sparkle_roll}
            count = len(self.pixels)
            share = getv(pattern.sparkles, t)
            if sound is not None and self.links["sparkles"]:
                # the highs make more of them, and each band's sit at its height: bass on the wide base,
                # treble at the narrow top
                weights = [
                    (sound.low * (1 - p.y) ** 2) + (sound.mid * 4 * p.y * (1 - p.y)) + (sound.high * p.y ** 2) + 0.01
                    for p in self.pixels
                ]
                k = int(count * share * (0.25 + (1.5 * sound.high)))
                picks = random.choices(range(count), weights=weights, k=k)
            else:
                picks = random.choices(range(count), k=int(count * share))
            for idx in picks:
                run.sparkles.setdefault(idx, t)

        every = self.links["streamers"] if self.beating else 0
        if every:
            # the pattern's own streamers, launched on the beat, each launch a quarter turn on
            run.next_streamer = t
            run.streamers = [streamer for streamer in run.streamers if streamer.alive(t)]
            if self.on_beat is not None and self.on_beat[0] % every == 0:
                n, at = self.on_beat
                self._launch(run, getv_streamers(pattern.streamers, t, None), at - run.start, ((n // every) % 4) / 4)
        elif t >= run.next_streamer:
            run.next_streamer += self.streamer_delay
            streamer_defs = getv_streamers(pattern.streamers, t, run.last_streamer_t)
            run.last_streamer_t = t
            run.streamers = [streamer for streamer in run.streamers if streamer.alive(t)]
            self._launch(run, streamer_defs, t)

    def _sparkle(self, run: Run, idx: int, t: float) -> float:
        # raw sparkles are on or off; smooth ones fade in and out over their life
        lit = run.sparkles.get(idx)
        if lit is None:
            return 0.0
        if run.pattern.grain == "raw":
            return 1.0
        age = min(1.0, (t - lit) / (2 * self.sparkle_roll))
        fade = math.sin(math.pi * age) ** 2
        feel = self.feel
        if feel is not None:
            # the drive snaps them on and lets them fall away
            fade += ((1 - age) ** 2 - fade) * feel
        return fade

    def _render(self, run: Run, now: float) -> list[WRGB]:
        pattern = run.pattern
        t = now - run.start
        self._spawn(run, t)
        clock = now - self._init_t
        blend_h = getv(self._blend_func, clock) + self.hue_shift
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

        # the frame's beats while the music's tempo is sure, else one a second
        pattern.base_color.frame(self.dt * (self.sound.bpm / 60 if self.beating else 1), self.dt)
        # an effect works out every light's layers once a frame, before the lights ask for them
        beat = self.on_beat[0] if self.on_beat is not None else None
        pattern.step(t, self.pixels, self.sound, self.beating, beat, blend_h)

        beat_flash = self._flash_at(now)
        chase = self.links["flash"] == "chase" and self._flash is not None
        sector = (self._flash[0] % SECTORS) / SECTORS if chase else 0.0

        def grain(name: str, idx: int) -> float:
            return effects[name] * (self.noise[name](idx, clock) if smooth else random.random())

        frame = []
        for pixel in self.pixels:
            pixel_t = (pixel.t + spin + self.spin_angle + self.ring_angle + (spiral * pixel.y)) % 1
            flash = beat_flash
            if flash and chase:
                flash *= coverage(pixel.t, sector, sector + (1 / SECTORS), SECTOR_EDGE)
            for topology in topologies:
                pixel_t = topology(pixel_t, pixel.y)

            sparkle = self._sparkle(run, pixel.idx, t)
            covering = []
            for streamer, miny, angle in streamers:
                c = streamer.coverage(pixel, miny, angle)
                if c > 0:
                    covering.append((streamer, c))

            w = r = g = b = 0.0
            for weight, color, suppress in pattern.base_color(t, blend_h, spread_h, pixel_t, pixel.y, pixel):
                if effects["flash"] and "flash" not in suppress and color.l != -1.0:
                    color.l -= grain("flash", pixel.idx)
                if flash and "flash" not in suppress and color.l != -1.0:
                    # the beat's flash lifts the light toward white
                    color.l += 0.8 * flash * (1 - color.l)
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
    def mark(self) -> str:
        """? not saved, ! saved, * changed since."""
        pattern_state = "?"
        if self.pattern.configured:
            pattern_state = "!"
        if self.pattern.dirty:
            pattern_state = "*"
        return pattern_state

    @property
    def pattern_name(self) -> str:
        if self.change is not None:
            return f"{self.pattern.name}->{self.change.run.pattern.name}"
        else:
            return f"{self.pattern.name}{self.mark}"

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

    def start_transition(self, next: int | None=None, bars: bool=False):
        """A change to the next pattern, or the one at next. With bars, it lasts whole bars, as an
        automatic change in drive does from the bar line it starts on."""
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
            DRIVE_BARS * 4 * 60 / self.sound.bpm if bars else self._change_length(),
            self.next_pattern.transition,
        )

    def _change_length(self) -> float:
        # with Feel, the more the groove, the longer the change
        feel = self.feel
        if feel is None:
            return self.transition_length
        return GROOVE_CHANGE + ((self.transition_length - GROOVE_CHANGE) * min(1.0, feel * 2))

    def glide(self):
        # eases the tree from the frame on show into the pattern's new settings
        if self.frame is not None:
            self.glide_from = self.frame
            self.glide_start = self._t

    def render(self, t: float) -> list[WRGB]:
        self._listen(t)
        self._t = t
        if (self.change is None
                and not self.pause_change
                and t >= self.run.start + self.pattern_length
                and (not self.lands_on_bars or (self.on_beat is not None and self.on_beat[0] % 4 == 0))):
            self.start_transition(bars=self.lands_on_bars)
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
            glide_length = self.glide_length
            feel = self.feel
            if feel is not None:
                groove, drive = FEEL_GLIDE
                glide_length = groove + ((drive - groove) * feel)
            progress = (t - self.glide_start) / glide_length
            if progress >= 1:
                self.glide_from = None
            else:
                frame = self._mix(self.glide_from, frame, progress)

        self.frame = frame
        return frame

    def write(self, frame: list[WRGB]):
        start = 0
        sent = []
        for interface in self.lights.interfaces:
            end = start + len(interface.layout)
            data = bytes(int(c + 0.5) for light in frame[start:end] for c in light)
            interface.set_rt_frame_socket(io.BytesIO(data), 3)
            sent.append(data)
            start = end
        if self.on_frame is not None:
            self.on_frame(b"".join(sent))

    def animate(self):
        start_time = time.time()
        self.init(start_time)
        next_frame = start_time + FRAME
        while self.running:
            colors = self.render(time.time())
            self.write(colors)
            next_frame = wait_for(next_frame)
