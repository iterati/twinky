from enum import Enum
import random
from typing import TypeAlias, TypedDict, NotRequired
from pytweening import linear

from core import Color
from param import Curve, CurveFunc, Param, getv, rand

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

    def __call__(self, color: Color, t: float, pixel_x: float, pixel_y: float) -> Color:
        if color.l != -1.0 and self.make_white:
            return Color(
                w=0.75,
                s=0.0,
                l=-0.75,
            )

        return Color(
            w=getv(self.w, t) if self.w is not None else color.w,
            h=(
                (0 if self.ignore_color else color.h)
                + (0 if self.h is None else getv(self.h, t))
            ),
            s=getv(self.s, t) if self.s is not None else color.s,
            l=getv(self.l, t) if self.l is not None else color.l,
        )

class RandomColorStreamerFunc(StreamerFunc):
    def __init__(self,
                 minh: Param,
                 maxh: Param,
                 w: Param | None=None,
                 s: Param | None=None,
                 l: Param | None=None):
        self.w = w
        self.minh = minh
        self.maxh = maxh
        self._h = None
        self.s = s
        self.l = l

    def h(self, t: float) -> float:
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
        self.angle = random.random() if angle is None else angle
        self.spin_dir = 1 if spin_dir == Spin.CLOCKWISE else -1
        self.spin = getv(spin, initial_t)
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

class StreamerValue(TypedDict):
    func: NotRequired[StreamerFunc]
    move_dir: NotRequired[Direction]
    spin_dir: NotRequired[Spin]
    angle: NotRequired[Param | CurveFunc]
    spin: NotRequired[Param | CurveFunc]
    length: NotRequired[Param | CurveFunc]
    width: NotRequired[Param | CurveFunc]
    lifetime: NotRequired[Param | CurveFunc]
    
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
