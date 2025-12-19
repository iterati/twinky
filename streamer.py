from enum import Enum
import random
from typing import Callable, TypeAlias
from pytweening import linear

from core import Color
from param import Curve, Param, getv, rand


StreamerValue: TypeAlias = dict
StreamerValues: TypeAlias = list[dict]
StreamerParamFunc: TypeAlias = Callable[[float], StreamerValues]
StreamerParam: TypeAlias = StreamerParamFunc | StreamerValues
StreamerParams: TypeAlias = list[StreamerParam]

StreamerFunc: TypeAlias = Callable[[Color, float, float, float], Color]
StreamerFuncParam: TypeAlias = Callable[[Color, float, float, float], Color] | Color


def getv_streamers(v: StreamerParam, t: float) -> StreamerValues:
    return v(t) if callable(v) else v


def setcolor_streamer(w: Param | None=None,
                      h: Param | None=None,
                      s: Param | None=None,
                      l: Param | None=None,
                      make_white: bool=False,
                      ignore_color: bool=False) -> StreamerFunc:
    def func(color: Color, t: float, pixel_t: float, pixel_y: float) -> Color:
        if color.l != -1.0 and make_white:
            return Color(
                w=0.75,
                s=0.0,
                l=-0.75,
            )

        return Color(
            w=getv(w, t) if w is not None else color.w,
            h=(0 if ignore_color else color.h) + (0 if h is None else getv(h, t)),
            s=getv(s, t) if s is not None else color.s,
            l=getv(l, t) if l is not None else color.l,
        )
    return func


class RandomColorStreamerFunc:
    def __init__(self,
                 minh,
                 maxh,
                 w: Param | None=None,
                 s: Param | None=None,
                 l: Param | None=None):
        self.w = w
        self.minh = minh
        self.maxh = maxh
        self._h = None
        self.s = s
        self.l = l

    def h(self, t):
        if self._h is None:
            self._h = rand(getv(self.minh, t), getv(self.maxh, t))(0)
            
        return self._h

    def __call__(self, color: Color, t: float, pixel_x: float, pixel_y: float) -> Color:
        return Color(
            w=getv(self.w, t) if self.w is not None else color.w,
            h=self.h(t),
            s=getv(self.s, t) if self.s is not None else color.s,
            l=getv(self.l, t) if self.l is not None else color.l,
        )


class StreamerFuncs(Enum):
    BASE = setcolor_streamer(l=0.0)
    BASE_WHITEN = setcolor_streamer(l=0.0, make_white=True)
    BLANK = setcolor_streamer(w=0, l=-1)
    INVERT = setcolor_streamer(h=0.5, l=0.0)
    INVERT_WHITEN = setcolor_streamer(h=0.5, l=0.0, make_white=True)
    WHITEN = setcolor_streamer(w=0.75, s=0.0, l=-0.75)
    NOOP = setcolor_streamer()
    RANDOM = setcolor_streamer(h=rand(), l=0)


def streamer_choices(
        delay: float,
        choices: list[StreamerValues],
        choose: tuple[int, int] | None=None,
        delay_offset: float=0,
) -> StreamerParamFunc:
    def func(t: float) -> StreamerValues:
        s = int(t + delay_offset) % (len(choices) * delay)
        if s % delay == 0:
            c = choices[int(s / delay) % len(choices)]
            if choose:
                return random.choices(c, k=random.randint(*choose))
            else:
                return c
        else:
            return []
    return func


def combined_choices(funcs: list[StreamerParamFunc]) -> StreamerParamFunc:
    def func(t: float) -> StreamerValues:
        r = []
        for f in funcs:
            r.extend(f(t))
        return r
    return func


class Direction(Enum):
    FROM_BOT = 0
    FROM_TOP = 1


class Spin(Enum):
    CLOCKWISE = 0
    COUNTERCLOCKWISE = 1


class Streamer:
    def __init__(self,
                 initial_t,
                 func: StreamerFunc,
                 move_dir: Direction=Direction.FROM_BOT,
                 spin_dir: Spin=Spin.CLOCKWISE,
                 angle: Param | None=None,
                 spin: Param=1.0,
                 length: Param=1.0,
                 width: Param=0.1,
                 lifetime: Param=6.0):
        self.initial_t = initial_t
        self.reverse = move_dir != Direction.FROM_TOP
        #if move_dir == Direction.FROM_TOP:
        spind = -1 if spin_dir == Spin.CLOCKWISE else 1
        #else:
        #    spind = 1 if spin_dir == Spin.CLOCKWISE else -1

        self.angle = random.random() if angle is None else angle
        self.spin = spind * getv(spin, initial_t)
        self.length = getv(length, initial_t)
        self.width = getv(width, initial_t)
        self.lifetime = getv(lifetime, initial_t)
        self.func = func

        if self.reverse:
            self.y_func = Curve(linear, [(0, -self.length), (self.lifetime, 1)])
        else:
            self.y_func = Curve(linear, [(0, 1), (self.lifetime, -self.length)])

    def alive(self, t):
        return t < self.initial_t + self.lifetime

    def contains(self, t, pixel):
        if not self.alive(t):
            return False
        
        miny = self.y_func(t - self.initial_t)
        if pixel.y < miny or pixel.y > miny + self.length:
            return False
        
        mino = ((pixel.y * self.spin) + self.angle) % 1
        if mino + self.width > 1.0:
            return mino < pixel.t or pixel.t < (mino + self.width) - 1
        else:
            return mino < pixel.t < mino + self.width

    def __repr__(self):
        return f"Streamer({self.angle},{self.spin},{self.length},{self.width},{self.lifetime})"
