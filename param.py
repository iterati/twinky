import random
from typing import Callable, TypeAlias


ParamFunc: TypeAlias = Callable[[float], float]
Param: TypeAlias = ParamFunc | float

ControlPoint: TypeAlias = tuple[float, float]
ControlPoints: TypeAlias = list[ControlPoint]


def getv(v: Param, t: float) -> float:
    return v(t) if callable(v) else v


def const(_: float) -> float:
    return 0


def rand(minv: float=0.0, maxv: float=1.0) -> ParamFunc:
    def func(_: float) -> float:
        s = random.random()
        return (s * (maxv - minv)) + minv

    return func


def choice(choices: Callable[[float], list[float]] | list[float]) -> ParamFunc:
    def func(t: float) -> float:
        c = choices(t) if callable(choices) else choices
        return random.choice(c)

    return func


class Curve:
    def __init__(self, shape_func: ParamFunc, control_points: ControlPoints):
        self.shape_func = shape_func
        self.control_points = control_points
        self.length = self.control_points[-1][0] if len(self.control_points) > 0 else 0

    def _find_control_points(self, s) -> tuple[int, int]:
        bottom = None
        for i, [start, _] in enumerate(self.control_points):
            if start <= s:
                bottom = i

        if bottom is None:
            raise ValueError("Couldn't find the bottom")

        return (bottom, bottom + 1)

    def __call__(self, t: float) -> float:
        s = t % self.length
        bottom, top = self._find_control_points(s)
        start_t, start_v = self.control_points[bottom]
        end_t, end_v = self.control_points[top]
        ss = (s - start_t) / (end_t - start_t)
        return (self.shape_func(ss) * (end_v - start_v)) + start_v

    def __repr__(self):
        return f"curve({self.control_points})"


class Random(Curve):
    def __init__(self,
                 minv: Curve | float=0.0,
                 maxv: Curve | float=1.0,
                 length: float | None=None):
        self.minv = minv
        self.maxv = maxv
        if isinstance(minv, Curve) and isinstance(maxv, Curve):
            self.length = max(minv.length, maxv.length)
        elif isinstance(minv, Curve):
            self.length = minv.length
        elif isinstance(maxv, Curve):
            self.length = maxv.length
        else:
            if length is None:
                raise ValueError("Length needs to be set if no curves")

            self.length = length

    def __call__(self, t: float) -> float:
        s = random.random()
        minv = getv(self.minv, t)
        maxv = getv(self.maxv, t)
        return (s * (maxv - minv)) + minv


class CombinedCurve(Curve):
    def __init__(self, curves: list[Curve]):
        self.curves = curves
        self.starts = []
        self.length = 0
        for curve in self.curves:
            self.starts.append(self.length)
            self.length += curve.length

    def __call__(self, t: float) -> float:
        s = t % self.length
        idx = 0
        for i, s in enumerate(self.starts):
            if t > s:
                idx = i

        return self.curves[idx](t - self.starts[idx])
            

def combined_curve(curves: list[Curve]) -> ParamFunc:
    starts = []
    length = 0
    for c in curves:
        starts.append(length)
        length += c.length
        
    def func(t: float):
        s = t % length
        idx = 0
        for i, s in enumerate(starts):
            if t > s:
                idx = i

        return curves[idx](t - starts[idx])

    return func
