from enum import Enum
import math
from typing import Callable, TypeAlias
from pytweening import easeInOutCubic
from xled_plus.ledcolor import hsl_color, set_color_style

from param import Param, Curve, getv, rand
from utils import coverage, mk_bump

set_color_style('8col')
# set_color_style('linear')

class Color:
    def __init__(self, w=0.0, h=0.0, s=1.0, l=-1.0):
        self._w = min(1.0, max(0.0, w))
        self._h = h % 1
        self._s = min(1.0, max(0.0, s))
        self._l = min(1.0, max(-1.0, l))

    @property
    def w(self):
        return self._w

    @w.setter
    def w(self, v: float):
        self._w = min(1.0, max(0.0, v))
    
    @property
    def h(self):
        return self._h

    @h.setter
    def h(self, v: float):
        self._h = v % 1

    @property
    def s(self):
        return self._s

    @s.setter
    def s(self, v: float):
        self._s = min(1.0, max(0.0, v))
    
    @property
    def l(self):
        return self._l

    @l.setter
    def l(self, v: float):
        self._l = min(1.0, max(-1.0, v))

    def reset(self):
        self.w, self.h, self.s, self.l = 0, 0, 1.0, -1.0

    def as_wrgb(self) -> tuple[float, int, int, int]:
        if self.l == -1.0:
            return (self.w * 255, 0, 0, 0)  # off, whatever its hue
        return (self.w * 255, *hsl_color(self.h, self.s, self.l))

    def __repr__(self):
        return f"{self.w} {self.h} {self.s} {self.l}"

# The soft edge of a Window or Split side, as a fraction of a turn round the trunk
EDGE = 0.05

# A light's color as layers, each (weight, Color, suppression strings), their weights summing to 1:
# a light on a soft edge is part one side, part the other, mixed as light once each is bytes.
# The suppression strings could move to an enum for better type safety
BaseColorValue: TypeAlias = list[tuple[float, Color, list[str]]]

# A base color is called for each light with its angle round the trunk (pixel_t, as spin and the
# topologies move it), its height, and its core.Pixel, which only an effect reads (effects.py)

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

    def __call__(self, t: float, blend: float, spread: float, pixel_t: float, pixel_y: float, pixel=None) -> BaseColorValue:
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
        return [(1.0, color, self.suppress)]

    def frame(self, beats: float, dt: float):
        """Called once a frame, before the lights, with the frame's beats and seconds: a hint's
        modulators run on them (hints.py)."""

    def __repr__(self):
        return f"{self.__class__.__name__}({self.color_w},{self.color_h},{self.color_s},{self.color_l})"

BaseColorFuncs: TypeAlias = list[BaseColor]
BaseColorFuncsParam: TypeAlias = Callable[[float], BaseColorFuncs] | BaseColorFuncs

class WindowColor(BaseColor):
    def __init__(self,
                 ratio: Param,
                 funcs: BaseColorFuncsParam | None=None,
                 suppress: list[str] | None=None):
        super(WindowColor, self).__init__(suppress=suppress)
        self.ratio = ratio
        self.funcs = funcs
        
    def __call__(self, t: float, blend: float, spread: float, pixel_t: float, pixel_y: float, pixel=None) -> BaseColorValue:
        ratio = getv(self.ratio, t)
        iteration = 0
        if isinstance(self.ratio, Curve):
            iteration = int(t / self.ratio.length)

        if self.funcs:
            funcs = getv_funcs(self.funcs, t)
        else:
            funcs = [None, None]

        # int(pixel_t + ratio) % 2 picks the side: the first up to 1 - ratio, the second from there round to 1
        first = math.floor(ratio) % 2
        second_share = coverage(pixel_t % 1, 1 - (ratio % 1), 1, EDGE)
        layers = []
        for side, share in ((first, 1 - second_share), (1 - first, second_share)):
            if share <= 0:
                continue
            func = funcs[side]
            if func is None:
                color = Color(0, blend + ((side + iteration) * spread), 1, 0)
                layers.append((share, color, self.suppress))
            else:
                layers += [(share * w, c, s) for w, c, s in func(t, blend, spread, pixel_t, pixel_y, pixel)]
        return layers

    def __repr__(self):
        return f"Window({self.ratio}, {self.funcs})"

class SplitColor(BaseColor):
    def __init__(self,
                 count: Param,
                 funcs: BaseColorFuncsParam | None=None,
                 suppress: list[str] | None=None):
        super(SplitColor, self).__init__(suppress=suppress)
        self.count = count
        self.funcs: BaseColorFuncsParam = (
            funcs
            if funcs is not None else
            [BaseColor(l=0), BaseColor()]
        )

    def __call__(self, t: float, blend: float, spread: float, pixel_t: float, pixel_y: float, pixel=None) -> BaseColorValue:
        count = int(getv(self.count, t))
        x = pixel_t % 1
        side = int(x * count)
        funcs = getv_funcs(self.funcs, t)
        # a light near a boundary takes some of the side next to its own, round the wrap too
        layers = []
        for s in {(side - 1) % count, side, (side + 1) % count}:
            share = coverage(x, s / count, (s + 1) / count, EDGE)
            if share > 0:
                func = funcs[s]
                layers += [(share * w, c, sup) for w, c, sup in func(t, blend, spread, pixel_t, pixel_y, pixel)]
        return layers

    def __repr__(self):
        return f"Split({self.count}, {self.funcs})"

class FallingColor(BaseColor):
    def __init__(self,
                 num_colors: int=8,
                 skip: Param=3/8,
                 offset: float=0,
                 period: float=60,
                 suppress: list[str] | None=None,
                 fade_func: Curve | float=1,
                 hue_func: Curve | None=None):
        super(FallingColor, self).__init__(suppress=suppress)
        self._num_colors = num_colors
        self._skip = skip
        self._offset = offset
        self._period = period
        self._fade_func = (
            fade_func
            if isinstance(fade_func, Curve) else
            Curve(easeInOutCubic, mk_bump(1, -fade_func, 0))
        )
        self._hue_func = 0 if hue_func is None else hue_func

    def __call__(self, t: float, blend: float, spread: float, pixel_t: float, pixel_y: float, pixel=None) -> BaseColorValue:
        # the colors fall num_colors bands a period, with no wrap, so the pattern's clock can run on
        pixel_y += (t + self._offset) * self._num_colors / self._period
        l = getv(self._fade_func, pixel_y)
        l = ((l + 1) ** 2) - 1
        h = int(pixel_y) * getv(self._skip, t)
        h += blend
        h += getv(self._hue_func, t)

        return [(1.0, Color(
            w=0,
            h=h,
            s=1,
            l=l,
        ), self.suppress)]

def setcolor(w: float | None=None,
             h: float | None=None,
             s: float | None=None,
             l: float | None=None,
             make_white: bool=False) -> Callable[[Color], Color]:
    def func(color: Color) -> Color:
        if color.l != -1.0 and make_white:
            return Color(
                w=1,
                s=0.0,
                l=-0.75,
            )

        return Color(
            w=w if w is not None else color.w,
            h=color.h + (0 if h is None else h),
            s=s if s is not None else color.s,
            l=l if l is not None else color.l,
        )
    return func

class ColorFuncs(Enum):
    BASE = setcolor(l=0.0)
    BASE_WHITEN = setcolor(l=0.0, make_white=True)
    BLANK = setcolor(w=0, l=-1)
    INVERT = setcolor(h=0.5, l=0.0)
    INVERT_WHITEN = setcolor(h=0.5, l=0.0, make_white=True)
    WHITEN = setcolor(w=1, s=0.0, l=-0.75)
    RANDOM = lambda _: Color(h=rand()(0), l=0)

def getv_funcs(v: BaseColorFuncsParam, t: float) -> BaseColorFuncs:
    return v(t) if callable(v) else v

def periodic_choices(delay: float, choices: list[BaseColorFuncs]):
    def func(t: float) -> BaseColorFuncs:
        return choices[int(t / delay) % len(choices)]
    return func
