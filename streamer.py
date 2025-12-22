from enum import Enum
import random
from typing import TypeAlias
from pytweening import linear

from core import Color
from param import Curve, Param, getv, rand

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

    def __call__(self, color: Color, t: float) -> Color:
        if color.l != -1.0 and self.make_white:
            return Color(
                w=0.75,
                s=0.0,
                l=-0.75,
            )

        h = 0
        if self.h is not None:
            h = getv(h, t)

        if isinstance(h, Curve):
            print("Curved curve", h, flush=True)
            h = getv(h, t)

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

    def __call__(self, color: Color, t: float) -> Color:
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
        self.func = func if func is not None else StreamerFunc()
        self.move_dir = move_dir
        self.spin_dir = 1 if spin_dir == Spin.CLOCKWISE else -1
        self.angle = angle
        self.spin = getv(spin, norm_t)
        self.length = getv(length, norm_t)
        self.width = getv(width, norm_t)
        self.lifetime = getv(lifetime, norm_t)

    @property
    def y_func(self):
        if self.reverse:
            return Curve(linear, [(0, -self.length), (self.lifetime, 1)])
        return Curve(linear, [(0, 1), (self.lifetime, -self.length)])

    def alive(self, t):
        return t < self.initial_t + self.lifetime

    def contains(self, t, pixel):
        if not self.alive(t):
            return False
        
        miny = self.y_func(t - self.initial_t)
        if pixel.y < miny or pixel.y > miny + self.length:
            return False
        
        mino = (
            (pixel.y * self.spin * self.spin_dir)
            + getv(self.angle, t)
        ) % 1
        if mino + self.width > 1.0:
            return mino < pixel.t or pixel.t < (mino + self.width) - 1
        else:
            return mino < pixel.t < mino + self.width

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
        self.delay = delay
        self.choices = choices
        self.choose = choose
        self.delay_offset = delay_offset

    def __call__(self, t: float) -> StreamerValues:
        s = int(t + self.delay_offset) % (len(self.choices) * self.delay)
        if s % self.delay != 0:
            return []

        c = self.choices[int(s / self.delay) % len(self.choices)]
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

    def __call__(self, t: float) -> StreamerValues:
        r = []
        for sc in self.streamer_choices:
            r.extend(sc(t))
        return r

StreamerParam: TypeAlias = StreamerChoices | StreamerValues

def getv_streamers(v: StreamerParam, t: float) -> StreamerValues:
    return v(t) if isinstance(v, StreamerChoices) else v
