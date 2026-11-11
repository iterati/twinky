from copy import deepcopy
from enum import Enum
import math
import random
from typing import TypeAlias

from colors import Color
from param import Param, getv, rand
from utils import coverage

# The soft edges of a streamer: across its width, as a fraction of a turn, and along its length
EDGE_T = 0.03
EDGE_Y = 0.05

class Direction(Enum):
    FROM_BOT = 0
    FROM_TOP = 1

class Spin(Enum):
    CLOCKWISE = 1
    COUNTERCLOCKWISE = -1

class StreamerFunc:
    def __init__(self,
                 w: Param | None=None,
                 h: Param | None=None,
                 s: Param | None=None,
                 l: Param | None=None,
                 make_white: bool=False,
                 ignore_color: bool=False):
        self.w = w
        self.h = h
        self.s = s
        self.l = l
        self.make_white = make_white
        self.ignore_color = ignore_color
        self._h = None

    def __call__(self, color: Color, t: float, blend: float) -> Color:
        if color.l != -1.0 and self.make_white:
            return Color(
                w=1,
                s=0.0,
                l=-0.75,
            )

        h = blend
        if self.h is not None and self._h is None:
            self._h = getv(self.h, t)
        h += self._h if self._h is not None else 0
        h += 0 if self.ignore_color else getv(color.h, t)

        return Color(
            w=getv(self.w, t) if self.w is not None else color.w,
            h=h,
            s=getv(self.s, t) if self.s is not None else color.s,
            l=getv(self.l, t) if self.l is not None else color.l,
        )

class RandomColorStreamerFunc(StreamerFunc):
    def __init__(self,
                 minh: Param=0.0,
                 maxh: Param=1.0,
                 w: Param | None=None,
                 s: Param | None=None,
                 l: Param | None=None):
        self.minh = minh
        self.maxh = maxh
        self.w = w
        self.s = s
        self.l = l

    def h(self, t: float) -> float:
        return rand(getv(self.minh, t), getv(self.maxh, t))(t)

    def __call__(self, color: Color, t: float, blend: float) -> Color:
        return Color(
            w=getv(self.w, t) if self.w is not None else color.w,
            h=self.h(t),
            s=getv(self.s, t) if self.s is not None else color.s,
            l=getv(self.l, t) if self.l is not None else color.l,
        )

class Streamer:
    def __init__(self,
                 initial_t: float,
                 norm_t: float,
                 func: StreamerFunc | None=None,
                 move_dir: Direction | None=None,
                 spin_dir: Spin | None=None,
                 angle: Param | None=None,
                 spin: Param | None=None,
                 length: Param | None=None,
                 width: Param | None=None,
                 lifetime: Param | None=None):
        self.initial_t = initial_t
        self.norm_t = norm_t
        move_dir = move_dir if move_dir is not None else Direction.FROM_BOT
        spin_dir = spin_dir if spin_dir is not None else Spin.CLOCKWISE
        angle = angle if angle is not None else random.random()
        spin = spin if spin is not None else 1.0
        length = length if length is not None else 1.0
        width = width if width is not None else 0.1
        lifetime = lifetime if lifetime is not None else 1.0

        self.reverse = move_dir != Direction.FROM_TOP
        self.func = deepcopy(func) if func is not None else StreamerFunc()
        self.move_dir = move_dir
        self.spin_dir = 1 if spin_dir == Spin.CLOCKWISE else -1
        self.angle = angle
        self.spin = getv(spin, norm_t)
        self.length = getv(length, norm_t)
        self.width = getv(width, norm_t)
        self.lifetime = getv(lifetime, norm_t)

    def alive(self, t):
        return t < self.initial_t + self.lifetime

    def place(self, t) -> tuple[float, float]:
        # once a frame: the bottom of its length, and its angle
        s = (t - self.initial_t) / self.lifetime
        if self.reverse:
            miny = -self.length + (s * (1 + self.length))
        else:
            miny = 1 - (s * (1 + self.length))
        return miny, getv(self.angle, t)

    def coverage(self, pixel, miny, angle) -> float:
        if not miny - EDGE_Y < pixel.y < miny + self.length + EDGE_Y:
            return 0.0
        along = coverage(pixel.y, miny, miny + self.length, EDGE_Y, wrap=False)
        mino = ((pixel.y * self.spin * self.spin_dir) + angle) % 1
        return along * coverage(pixel.t, mino, mino + self.width, EDGE_T)

    def __repr__(self):
        return f"Streamer({self.angle},{self.spin},{self.length},{self.width},{self.lifetime})"

class StreamerValue:
    def __init__(self,
                 func: StreamerFunc | None=None,
                 move_dir: Direction | None=None,
                 spin_dir: Spin | None=None,
                 angle: Param | None=None,
                 spin: Param | None=None,
                 length: Param | None=None,
                 width: Param | None=None,
                 lifetime: Param | None=None):
        self.func = func
        self.move_dir = move_dir
        self.spin_dir = spin_dir
        self.angle = angle
        self.spin = spin
        self.length = length
        self.width = width
        self.lifetime = lifetime

StreamerValues: TypeAlias = list[StreamerValue]

class StreamerChoices:
    def __init__(self,
                 delay: float,
                 choices: list[StreamerValues],
                 choose: tuple[int, int] | None=None,
                 delay_offset: float=0):
        self.choices = choices
        self.choose = choose
        self.delay = delay
        self.delay_offset = delay_offset

    def __call__(self, t: float, last_t: float | None) -> StreamerValues:
        # t and last_t (None at first) are the turn's clock, so a pattern starts each turn afresh
        trigger = math.floor((t - self.delay_offset) / self.delay)
        if trigger < 0 or (
            last_t is not None
            and trigger == math.floor((last_t - self.delay_offset) / self.delay)
        ):
            return []

        c = self.choices[(trigger + 1) % len(self.choices)]
        if self.choose:
            pick = (
                self.choose[0]
                if self.choose[0] == self.choose[1] else
                random.randint(*self.choose)
            )
            return random.choices(c, k=pick)
        return c

class CombinedChoices(StreamerChoices):
    def __init__(self, streamer_choices: list[StreamerChoices]):
        self.streamer_choices = streamer_choices

    def __call__(self, t: float, last_t: float | None) -> StreamerValues:
        r = []
        for sc in self.streamer_choices:
            r.extend(sc(t, last_t))
        return r

StreamerParam: TypeAlias = StreamerChoices | StreamerValues

def getv_streamers(v: StreamerParam, t: float, last_t: float | None) -> StreamerValues:
    return v(t, last_t) if isinstance(v, StreamerChoices) else v
