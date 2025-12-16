import random
import time
from typing import Callable

from core import (
    Color,
    Lights,
    Animation,
)
from param import (
    ParamFunc,
    Param,
    Direction,
    Spin,
    Streamer,
    StreamerParamFunc,
    StreamerParam,
    const,
    curve,
    getv,
    getv_streamers,
)
from pytweening import (
    linear,
    easeInSine,
    easeOutSine,
    easeInOutSine,
    easeOutBounce,
    easeInOutBounce,
    easeInOutCubic,
)

DEBUG = False
# DEBUG = True
CHANGE = "none"
# CHANGE = "transition"
CURR_PATTERN = -1
NEXT_PATTERN = 1

def rand(minv=0.0, maxv=1.0) -> Callable[[], float]:
    def func() -> float:
        s = random.random()
        return (s * (maxv - minv)) + minv

    return func


def choice(choices: list[float]) -> Callable[[], float]:
    def func() -> float:
        return random.choice(choices)

    return func


class Topology:
    def __call__(self, t: float, pixel_t: float, pixel_y: float) -> float:
        return pixel_t


class TopologyMirror(Topology):
    def __init__(self, count: Param):
        self.count = count

    def __call__(self, t: float, pixel_t: float, pixel_y: float) -> float:
        count = getv(self.count, t)
        r = ((pixel_t * count) % 1) * 2
        return r if r < 1.0 else 2.0 - r


class TopologyRepeat(Topology):
    def __init__(self, count: Param):
        self.count = count

    def __call__(self, t: float, pixel_t: float, pixel_y: float) -> float:
        count = getv(self.count, t)
        return (pixel_t * getv(count, t)) % 1


class TopologyDistort(Topology):
    def __init__(self, top_d: Param=0, bot_d: Param=0):
        self.top_d = top_d
        self.bot_d = bot_d

    def __call(self, t: float, pixel_t: float, pixel_y: float) -> float:
        top_d = getv(self.top_d, t)
        bot_d = getv(self.bot_d, t)

        return pixel_t + getv(
            curve(easeInOutSine, [(0, 0), (0.25, bot_d), (0.5, 0), (0.75, top_d), (1, 0)]),
            pixel_y
        )

type BaseColorValue = tuple[Color, list[str]]
type BaseColorFunc = Callable[[float, float, float, float, float], BaseColorValue]
type FuncsParamFunc = Callable[[float], list[BaseColorFunc | None]]
type FuncsParam = FuncsParamFunc | list[BaseColorFunc | None]

def getv_funcs(v: FuncsParam, t: float) -> list[BaseColorFunc | None]:
    return v(t) if callable(v) else v

class BaseColor:
    def __init__(self,
                 w: Param=0,
                 h: Param=0,
                 s: Param=1,
                 l: Param=-1,
                 suppress: list[str] | None=None,
                 blend: bool=True,
                 spread: bool=True):
        self.color_w = w
        self.color_h = h
        self.color_s = s
        self.color_l = l
        self.suppress = suppress if suppress is not None else []
        self.blend = blend
        self.spread = spread
        self.base_hue = 0

    def init(self, base_hue):
        self.base_hue = base_hue

    def __call__(self, t: float, blend: float, spread: float, pixel_t: float, pixel_y: float) -> BaseColorValue:
        color = Color(
            w=getv(self.color_w, t),
            h=(
                getv(self.color_h, t)
              + (blend if self.blend else 0)
              + ((spread * pixel_t) if self.spread else 0)
            ),
            s=getv(self.color_s, t),
            l=getv(self.color_l, t),
        )
        return color, self.suppress

    def __repr__(self):
        return f"{self.__class__.__name__}({self.color_w},{self.color_h},{self.color_s},{self.color_l})"


class WindowColor(BaseColor):
    def __init__(self,
                 ratio: Param,
                 funcs: FuncsParam | None=None,
                 suppress: list[str] | None=None):
        super(WindowColor, self).__init__(suppress=suppress)
        self.ratio = ratio
        self.funcs = funcs
        
    def __call__(self, t: float, blend: float, spread: float, pixel_t: float, pixel_y: float) -> BaseColorValue:
        ratio = getv(self.ratio, t)
        side = int(pixel_t + ratio) % 2
        iteration = 0
        if isinstance(self.ratio, curve):
            iteration = int(t / self.ratio.length)

        if self.funcs:
            funcs = getv_funcs(self.funcs, t)
        else:
            funcs = [None, None]

        func = funcs[side]
        if func is not None:
            return func(t, blend, spread, pixel_t, pixel_y)
        else:
            print(side, iteration, spread)
            color = Color(0, blend + ((side + iteration) * spread), 1, 0)
            return color, self.suppress

    def __repr__(self):
        return f"Window({self.ratio}, {self.funcs})"


class SplitColor(BaseColor):
    def __init__(self,
                 count: Param,
                 funcs: FuncsParam | None=None,
                 suppress: list[str] | None=None):
        super(SplitColor, self).__init__(suppress=suppress)
        self.count = count
        self.funcs = funcs

    def __call__(self, t: float, blend: float, spread: float, pixel_t: float, pixel_y: float) -> BaseColorValue:
        count = getv(self.count, t)
        side = int(pixel_t * count)
        if self.funcs:
            funcs = getv_funcs(self.funcs, t)
        else:
            funcs = [None] * int(count)

        func = funcs[side]
        if func is not None:
            return func(t, blend, spread, pixel_t, pixel_y)
        else:
            color = Color(0, blend + (side * spread), 1, 0)
            return color, self.suppress

    def __repr__(self):
        return f"Split({self.count}, {self.funcs})"


class FallingColor(BaseColor):
    def __init__(self,
                 num_colors: int=8,
                 skip_colors: int=3,
                 suppress: list[str] | None=None):
        super(FallingColor, self).__init__(suppress=suppress)
        self._num_colors = num_colors
        self._skip_colors = skip_colors
        self._ycurve = curve(linear, [(0, 0), (60, num_colors)])
        self._lcurve = curve(easeInOutCubic, [(0, -1), (0.5, 0), (1, -1)])

    def _h(self, pixel_y: float) -> float:
        return ((int(pixel_y) * self._skip_colors) % self._num_colors) / self._num_colors

    def __call__(self, t: float, blend: float, spread: float, pixel_t: float, pixel_y: float) -> BaseColorValue:
        pixel_y += getv(self._ycurve, t)
        color = Color(
            0,
            self.base_hue + self._h(pixel_y),
            1,
            getv(self._lcurve, pixel_y),
        )
        return color, self.suppress


class Pattern:
    def __init__(self,
                 name: str,
                 base_color: BaseColor | None=None,
                 topologies: list[Topology] | None=None,
                 spread: Param=0,
                 flash: Param=0,
                 flicker: Param=0,
                 flitter: Param=0,
                 flux: Param=0,
                 spiral: Param=0,
                 spin: Param=0,
                 sparkles: Param=0,
                 streamers: StreamerParam | None=None):
        self.name = name
        self.base_color = base_color if base_color is not None else BaseColor()
        self.topologies = topologies if topologies is not None else []
        self.spread = spread
        self.flash = flash
        self.flicker = flicker
        self.flitter = flitter
        self.flux = flux
        self.spiral = spiral
        self.spin = spin
        self.sparkles = sparkles
        self.streamers = streamers if streamers is not None else []


class Blender(Animation):
    sparkle_delay = 0.25
    streamer_delay = 1.0

    def __init__(self, lights: Lights, patterns: list[Pattern]):
        super(Blender, self).__init__(lights, None)
        self.patterns = patterns
        self._blend_func = curve(linear, [(0, 0), (60, 1)])

    def _pick_next(self):
        return random.choice([p for p in self.patterns if p.name != self.curr_pattern.name])

    def init(self, t: float):
        for interface in self.lights.interfaces:
            interface.set_mode("rt")
    
        self._t = t
        self.pattern_start = t
        if DEBUG:
            self.curr_pattern = self.patterns[CURR_PATTERN]
            self.next_pattern = self.patterns[NEXT_PATTERN]
            if CHANGE == "transition":
                self.transitioning = True
                self.pattern_end = t + 6.0
                print(f"{self.curr_pattern.name}->{self.next_pattern.name}")
            else:
                self.transitioning = False
                self.pattern_end = t + 54.0
                print(self.curr_pattern.name)
        else:
            self.curr_pattern = random.choice(self.patterns)
            self.next_pattern = self._pick_next()
            self.transitioning = False
            self.pattern_end = t + 54.0
            print(self.curr_pattern.name)

        self.curr_pattern.base_color.init(getv(self._blend_func, t))
        self.pattern = self.curr_pattern

        self.next_sparkle = t
        self.sparkles = []
        self.next_streamer = t
        self.streamers = []

    def _render(self, t: float, pattern: Pattern) -> list[Color]:
        blend_h = getv(self._blend_func, t)
        spread_h = getv(pattern.spread, t)
        flash_v = getv(pattern.flash, t)
        flash_func = rand(0.0, flash_v)
        flicker_v = getv(pattern.flicker, t)
        flicker_func = rand(0.0, flicker_v)
        flitter_v = getv(pattern.flitter, t)
        flitter_func = rand(0.0, flitter_v)
        flux_v = getv(pattern.flux, t)
        flux_func = rand(-flux_v/2, flux_v/2)

        colors = []
        for pixel in self.pixels:
            pixel_t = (
                pixel.t
              + getv(pattern.spin, t)
              + (getv(pattern.spiral, t) * pixel.y)
            ) % 1

            for topology in pattern.topologies:
                pixel_t = topology(t, pixel_t, pixel.y)

            color, suppress = pattern.base_color(
                t,
                blend_h,
                spread_h,
                pixel_t,
                pixel.y,
            )

            if "flash" not in suppress and pixel.l != -1.0:
                color.l -= flash_func()
            if "flicker" not in suppress:
                color.w += flicker_func()
            if "flitter" not in suppress and pixel.s != 0.0:
                color.s -= flitter_func()
            if "flux" not in suppress:
                color.h += flux_func()

            if "sparkles" not in suppress:
                idx = pixel.idx + (400 * pixel.strand)
                if idx in self.sparkles:
                    color = whiten(color)

            if "streamers" not in suppress:
                for streamer in self.streamers:
                    if streamer.contains(self._t, pixel):
                        color = streamer.func(color)

            colors.append(color)

        return colors

    def _render_transition(self, t: float) -> list[Color]:
        curr_colors = self._render(54.0 + t, self.curr_pattern)
        next_colors = self._render(t, self.next_pattern)
        colors = []
        for curr_color, next_color in zip(curr_colors, next_colors):
            colors.append(Color(
                getv(curve(easeInOutCubic, [(0, curr_color.w), (6, next_color.w)]), t),
                getv(curve(easeInOutCubic, [(0, curr_color.h), (6, next_color.h)]), t),
                getv(curve(easeInOutCubic, [(0, curr_color.s), (6, next_color.s)]), t),
                getv(curve(easeInOutCubic, [(0, curr_color.l), (6, next_color.l)]), t),
            ))

        return colors

    def render(self, t: float):
        self._t = t
        if t >= self.pattern_end and not (DEBUG and CHANGE == "none"):
            self.pattern_start = self.pattern_end
            if not self.transitioning:
                self.pattern_hue = getv(self._blend_func, t)
                self.transitioning = True
                self.pattern_end += 6.0
                print(f"{self.curr_pattern.name}->{self.next_pattern.name}")
            else:
                self.curr_pattern = self.next_pattern
                self.curr_pattern.base_color.init(getv(self._blend_func, t))
                self.next_pattern = self._pick_next()
                self.pattern = self.curr_pattern
                self.transitioning = False
                self.pattern_end += 54.0
                print(self.pattern.name)

        if t >= self.next_sparkle:
            self.next_sparkle += self.sparkle_delay
            if self.transitioning:
                sparkle_chance = getv(curve(linear, [
                    (0, getv(self.curr_pattern.sparkles, 60.0)),
                    (6, getv(self.next_pattern.sparkles, 6.0)),
                ]), t - self.pattern_start)
            else:
                sparkle_chance = getv(self.pattern.sparkles, t)

            self.sparkles = random.choices(
                range(len(self.pixels)),
                k=int(len(self.pixels) * sparkle_chance))
                
        if t >= self.next_streamer:
            self.next_streamer += self.streamer_delay
            streamer_defs = getv_streamers(self.pattern.streamers, t - self.pattern_start)
            self.streamers.extend([
                Streamer(t, **streamer_def)
                for streamer_def in streamer_defs
            ])

            new_streamers = []
            for streamer in self.streamers:
                if streamer.alive(t):
                    new_streamers.append(streamer)

            self.streamers = new_streamers
                
        if self.transitioning:
            colors = self._render_transition(t - self.pattern_start) 
        else:
            colors = self._render(t - self.pattern_start, self.pattern)

        for pixel, color in zip(self.pixels, colors):
            pixel.color = color

        self.write()

    def animate(self):
        start_time = time.time()
        self.init(start_time)
        next_frame = start_time + (1/16)
        while True:
            self.render(time.time())
            while time.time() < next_frame:
                pass

            next_frame += 1/16

def delay_choices(delay: float, choices: list) -> Callable[[float], list]:
    def func(t):
        return choices[int(t / delay) % len(choices)]

    return func

def streamer_choices(
        delay: float,
        choices: list[list],
        choose: tuple[int, int] | None=None,
        delay_offset: float=0,
) -> Callable[[float], list]:
    def func(t: float) -> list:
        s = int(t + delay_offset) % (len(choices) * 6)
        if s % delay == 0:
            c = choices[int(s / delay) % len(choices)]
            if choose:
                return random.choices(c, k=random.randint(*choose))
            else:
                return c
        else:
            return []
    return func

def combined_choices(funcs: list[Callable[[float], list[dict]]]):
    def func(t: float) -> list[dict]:
        r = []
        for f in funcs:
            r.extend(f(t))
        return r
    return func

def setcolor(w=None, h=None, s=None, l=None, make_white=False):
    def func(color: Color):
        if color.l != -1.0 and make_white:
            return whiten(color)

        return Color(
            w=w if w is not None else color.w,
            h=color.h + (0 if h is None else h),
            s=s if s is not None else color.s,
            l=l if l is not None else color.l,
        )
    return func


def whiten(color: Color):
    return Color(0.75, color.h, 0.0, -0.75)

def whiten_if_l(color: Color):
    if color.l != -1.0:
        return whiten(color)
    else:
        return Color(color.w, color.h, color.s, 0.0)

def invert(color: Color):
    return Color(color.w, color.h + 0.5, color.s, 0.0)

        
patterns = [
    Pattern(
        "Basic Bitch",
        base_color=BaseColor(l=0),
        flash=1.0,
        flicker=curve(easeInOutSine, [(0, 0.5), (3, 0), (6, 0.5)]),
        flitter=curve(easeInOutSine, [(0, 0), (6, 0.5), (12, 0)]),
        flux=curve(easeInOutSine, [(0, 0), (3, 2/3), (6, 0), (9, -2/3), (12, 0)]),
    ),
    Pattern(
        "Circus Tent",
        base_color=SplitColor(
            count=4,
            funcs=delay_choices(
                1.5,
                [
                    [
                        BaseColor(h=0.25, l=-1),
                        BaseColor(h=0.0, l=0, suppress=["sparkles"]),
                        BaseColor(h=0.75,l=-1),
                        BaseColor(h=0.5, l=0, suppress=["sparkles"]),
                    ],
                    [
                        BaseColor(h=0.25, l=0, suppress=["sparkles"]),
                        BaseColor(h=0.0, l=0, suppress=["sparkles"]),
                        BaseColor(h=0.75, l=0, suppress=["sparkles"]),
                        BaseColor(h=0.5, l=0, suppress=["sparkles"]),
                    ],
                    [
                        BaseColor(h=0.25, l=0, suppress=["sparkles"]),
                        BaseColor(l=-1),
                        BaseColor(h=0.75, l=0, suppress=["sparkles"]),
                        BaseColor(l=-1),
                    ],
                    [
                        BaseColor(h=0.25, l=0, suppress=["sparkles"]),
                        BaseColor(h=0.0, l=0, suppress=["sparkles"]),
                        BaseColor(h=0.75, l=0, suppress=["sparkles"]),
                        BaseColor(h=0.5, l=0, suppress=["sparkles"]),
                    ],
                ]
            ),
        ),
        topologies=[TopologyRepeat(4)],
        sparkles=0.5,
        spin=curve(easeInOutSine, [(0, 0), (15, 1), (30, 0), (45, -1), (60, 0)]),
        streamers=streamer_choices(
            3,
            [
                [
                    {
                        "move_dir": move_dir,
                        "spin_dir": spin_dir,
                        "spin": curve(const, [(0, 1), (3, 0.5), (6, 1)]),
                        "length": 1.0,
                        "width": curve(const, [(0, 0.1), (3, 0.15), (6, 0.1)]),
                        "lifetime": 6.0,
                        "func": whiten,
                    } for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                ] for move_dir in [Direction.FROM_BOT, Direction.FROM_TOP]
            ],
        ),
    ),
    Pattern(
        "Confetti",
        sparkles=0.2,
        streamers=streamer_choices(
            1,
            [[
                {
                    "move_dir": Direction.FROM_TOP,
                    "spin_dir": spin_dir,
                    "spin": spin,
                    "width": width,
                    "length": lambda _: choice([0.25, 0.5])(),
                    "lifetime": lambda _: rand(3, 6)(),
                    "func": setcolor(w=0, h=i/4, s=1, l=0.0),
                }
                for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                for spin, width in [(0.5, 0.1), (1, 0.15), (1.5, 0.2)]
                for i in range(4)
            ]],
            choose=(4, 8),
        )
    ),
    Pattern(
        "Coiled Spring",
        base_color=WindowColor(
            0.75,
            [
                BaseColor(w=0.75, s=0.0, l=-0.75, suppress=["sparkles", "streamers"]),
                BaseColor(h=0.5, l=-1),
            ],
        ),
        topologies=[TopologyRepeat(3)],
        spiral=curve(easeOutBounce, [(0, 2), (15, -2), (30, 2)]),
        streamers=streamer_choices(
            2,
            [
                [
                    {
                        "move_dir": Direction.FROM_BOT,
                        "spin_dir": Spin.CLOCKWISE if o % 2 == 0 else Spin.COUNTERCLOCKWISE,
                        "angle": (i/4) + (o/5),
                        "spin": curve(easeOutBounce, [(0, -2), (15, 2), (30, -2)]),
                        "length": 1,
                        "width": 0.2,
                        "lifetime": 1.0,
                        "func": setcolor(w=0, s=1, l=0.0),
                    } for i in range(4)
                ] for o in range(5)
            ],
        )
    ),
    Pattern(
        "Rainbro",
        base_color=BaseColor(l=0),
        topologies=[TopologyRepeat(curve(const, [
                (0, 6),
                (7.5, 8),
                (22.5, 4),
                (37.5, 2),
                (52.5, 3),
                (60, 6),
        ]))],
        flitter=0.1,
        flux=1/16,
        spin=6,
        spiral=curve(easeInOutSine, [(0, -2), (7.5, 2), (15, -2)]),
        spread=curve(easeInOutSine, [(0, 1), (15, -1), (30, 1)]),
    ),
    Pattern(
        "Twisted Rainbows",
        base_color=SplitColor(3),
        topologies=[TopologyRepeat(curve(const, [
            (0, 1),
            (12, 3),
            (24, 5),
            (36, 4),
            (48, 2),
            (60, 1)
        ]))],
        spin=2.0,
        spread=curve(easeInOutCubic, [
            (0, 1/4),
            (3, 0),
            (6, -1/4),
            (9, 0),
            (12, 1/4),
        ]),
        spiral=curve(const, [
            (0, -3), (3, 3),
            (9, -1.5), (15, 1.5),
            (21, -0.5), (27, 0.5),
            (33, -1), (39, 1),
            (45, -2), (51, 2),
            (57, -3), (60, -3)
        ]),
        streamers=streamer_choices(
            1,
            [[
                {
                    "move_dir": move_dir,
                    "spin_dir": spin_dir,
                    "spin": 2.0,
                    "length": 2.0,
                    "width": 0.15,
                    "lifetime": 3,
                    "func": whiten,
                }
                for move_dir in [Direction.FROM_BOT, Direction.FROM_TOP]
                for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
            ]],
            choose=(0, 2),
        )
    ),
    Pattern(
        "Spiral Top",
        base_color=WindowColor(
            curve(linear, [(0, 0), (3, 1)]),
        ),
        topologies=[TopologyMirror(3)],
        flux=1/16,
        spin=curve(easeInSine, [(0, 0), (15, 2), (30, 0), (45, -2), (60, 0)]),
        spiral=curve(linear, [(0, 0), (7.5, 2), (15, 0), (22.5, -2), (30, 0)]),
        spread=1/3,
        sparkles=0.15,
    ),
    Pattern(
        "Sliding Door",
        base_color=WindowColor(
            curve(easeInOutSine, [(0, 0), (3, 1), (6, 0)]),
            [
                BaseColor(l=-1, spread=False),
                BaseColor(
                    h=curve(const, [(0, 0), (6, 0.5), (12, 0)]),
                    suppress=["sparkles", "streamers"],
                    spread=False,
                ),
            ],
        ),
        topologies=[TopologyMirror(curve(const, [
            (0, 4),
            (12, 3),
            (24, 6),
            (36, 2),
            (48, 5),
            (60, 4),
        ]))],
        flux=1/16,
        spread=curve(easeInOutSine, [(0, 0.5), (15, -0.5), (30, 0.5)]),
        sparkles=0.5,
        streamers=combined_choices([
            streamer_choices(
                3,
                [
                    [
                        {
                            "move_dir": move_dir,
                            "spin_dir": spin_dir,
                            "spin": curve(const, [(0, 1), (6, 0.5), (12, 1)]),
                            "length": 1.0,
                            "width": curve(const, [(0, 0.1), (6, 0.15), (12, 0.1)]),
                            "lifetime": 6.0,
                            "func": setcolor(h=0.25, l=0, make_white=True),
                        } for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                    ] for move_dir in [Direction.FROM_BOT, Direction.FROM_TOP]
                ]
            ),
            streamer_choices(
                3,
                [
                    [
                        {
                            "move_dir": move_dir,
                            "spin_dir": spin_dir,
                            "spin": curve(const, [(0, 1), (6, 0.5), (12, 1)]),
                            "length": 1.0,
                            "width": curve(const, [(0, 0.1), (6, 0.15), (12, 0.1)]),
                            "lifetime": 6.0,
                            "func": setcolor(l=0.75, make_white=True),
                        } for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                    ] for move_dir in [Direction.FROM_BOT, Direction.FROM_TOP]
                ]
            ),
        ]),
    ),
    Pattern(
        "Spread Argyle",
        base_color=BaseColor(l=0.0),
        topologies=[TopologyMirror(2)],
        spin=curve(linear, [(0, 0), (30, 1)]),
        spiral=curve(const, [(0, 0), (12, 1), (24, -1), (36, 0.5), (48, -0.5), (60, 0)]),
        spread=curve(easeInSine, [(0, 0), (3, 3/8), (6, 0), (9, -3/8), (12, 0)]),
        streamers=streamer_choices(
            12,
            [[
                {
                    "move_dir": Direction.FROM_BOT,
                    "spin_dir": Spin.CLOCKWISE,
                    "angle": (i/2),
                    "spin": spin,
                    "length": 1,
                    "width": 0.1,
                    "lifetime": 12,
                    "func": setcolor(w=0, h=h, s=0, l=0),
                }
            for i in range(2)
            for spin, h in zip([-0.75, 0.75], [-1/3, 1/3])
            ]]
        ),
    ),
    Pattern(
        "Galaxus",
        sparkles=0.25,
        streamers=combined_choices([
            streamer_choices(
                2,
                [
                    [
                        {
                            "move_dir": Direction.FROM_BOT,
                            "spin_dir": Spin.CLOCKWISE,
                            "angle": (i/6) + (o/18),
                            "spin": 0.5,
                            "length": 1,
                            "width": 0.1,
                            "lifetime": 2,
                            "func": setcolor(w=0, h=0.5, s=1, l=0),
                        } for i in range(6)
                    ] for o in range(3)
                ],
            ),
            streamer_choices(
                2,
                [
                    [
                        {
                            "move_dir": Direction.FROM_TOP,
                            "spin_dir": Spin.COUNTERCLOCKWISE,
                            "angle": (i/6) + (o/12),
                            "spin": 0.5,
                            "length": 1,
                            "width": 0.1,
                            "lifetime": 2,
                            "func": setcolor(w=0, h=0, s=1, l=0),
                        } for i in range(6)
                    ] for o in range(3)
                ],
                delay_offset=1,
            )
        ])
    ),
    Pattern(
        "Falling Snow",
        base_color=FallingColor(),
        flitter=0.25,
        flux=1/8,
        sparkles=curve(easeInOutSine, [(0, 0.25), (6, 0.5), (12, 0.25)]),
        streamers=streamer_choices(
            1,
            [[
                {
                    "move_dir": move_dir,
                    "spin_dir": spin_dir,
                    "spin": spin,
                    "width": width,
                    "length": 0.5,
                    "lifetime": lifetime,
                    "func": setcolor(w=0.2, h=0, l=-1),
                }
                for move_dir in [Direction.FROM_BOT, Direction.FROM_TOP]
                for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                for lifetime in [3, 4.5, 6, 7.5]
                for spin, width in [(2, 0.2), (3, 0.15)]
            ]],
            choose=(0, 1),
        )
    ),
]
lights = Lights()
animation = Blender(lights, patterns)
animation.animate()
