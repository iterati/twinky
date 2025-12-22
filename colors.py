from enum import Enum
from typing import Callable, TypeAlias
from pytweening import linear, easeInOutCubic
import struct
from xled_plus.ledcolor import hsl_color, set_color_style

from param import Param, Curve, getv, const, rand
from utils import mk_bump

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

    def as_byte(self, t=0):
        try:
            w = getv(self.w, t)
            h = getv(self.h, t)
            s = getv(self.s, t)
            l = getv(self.l, t)
            rgb = hsl_color(h, s, l)
            return struct.pack('>BBBB', int(w * 255), *rgb)
        except Exception:
            raise ValueError("OOPS", self)

    def __repr__(self):
        return f"{self.w} {self.h} {self.s} {self.l}"

# list[str] are suppression strings - could move to an enum for better type safety
BaseColorValue: TypeAlias = tuple[Color, list[str]]

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
        
    def __call__(self, t: float, blend: float, spread: float, pixel_t: float, pixel_y: float) -> BaseColorValue:
        ratio = getv(self.ratio, t)
        side = int(pixel_t + ratio) % 2
        iteration = 0
        if isinstance(self.ratio, Curve):
            iteration = int(t / self.ratio.length)

        if self.funcs:
            funcs = getv_funcs(self.funcs, t)
        else:
            funcs = [None, None]

        func = funcs[side]
        if func is None:
            color = Color(0, blend + ((side + iteration) * spread), 1, 0)
            return color, self.suppress
        else:
            return func(t, blend, spread, pixel_t, pixel_y)

    def __repr__(self):
        return f"Window({self.ratio}, {self.funcs})"

class SplitColor(BaseColor):
    def __init__(self,
                 count: Param,
                 funcs: BaseColorFuncsParam | None=None,
                 suppress: list[str] | None=None):
        super(SplitColor, self).__init__(suppress=suppress)
        self.count = count
        self.funcs = funcs

    def __call__(self, t: float, blend: float, spread: float, pixel_t: float, pixel_y: float) -> BaseColorValue:
        count = getv(self.count, t)
        side = int((pixel_t % 1) * count)
        if self.funcs is not None:
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
                 offset: float=0,
                 period: float=60,
                 suppress: list[str] | None=None,
                 fade_func: Curve | float=1,
                 hue_func: Curve | None=None):
        super(FallingColor, self).__init__(suppress=suppress)
        self._num_colors = num_colors
        self._skip_colors = skip_colors
        self._offset = offset
        self._fade_func = (
            fade_func
            if isinstance(fade_func, Curve) else
            Curve(easeInOutCubic, mk_bump(1, -fade_func, 0))
        )
        self._hue_func = (
            hue_func
            if hue_func is not None else
            Curve(const, [(0, 0), (1, 0)])
        )
        self._period = period

    @property
    def ycurve(self) -> Curve:
        return Curve(linear, [(0, 0), (self._period, self._num_colors)])

    def _h(self, t: float, pixel_y: float) -> float:
        r = ((int(pixel_y) * self._skip_colors) % self._num_colors) / self._num_colors
        r += getv(self._hue_func, t)
        return r

    def __call__(self, t: float, blend: float, spread: float, pixel_t: float, pixel_y: float) -> BaseColorValue:
        s = (t + self._offset) % 60
        pixel_y += getv(self.ycurve, s)
        l = getv(self._fade_func, pixel_y)
        l = ((l + 1) ** 2) - 1
        color = Color(0, self.base_hue + self._h(s, pixel_y), 1, l)
        return color, self.suppress

def setcolor(w: float | None=None,
             h: float | None=None,
             s: float | None=None,
             l: float | None=None,
             make_white: bool=False) -> Callable[[Color], Color]:
    def func(color: Color) -> Color:
        if color.l != -1.0 and make_white:
            return Color(
                w=0.75,
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
    WHITEN = setcolor(w=0.75, s=0.0, l=-0.75)
    RANDOM = lambda _: Color(h=rand()(0), l=0)

def getv_funcs(v: BaseColorFuncsParam, t: float) -> BaseColorFuncs:
    return v(t) if callable(v) else v

def periodic_choices(delay: float, choices: list[BaseColorFuncs]):
    def func(t: float) -> BaseColorFuncs:
        return choices[int(t / delay) % len(choices)]
    return func
