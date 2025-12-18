import random
from typing import Callable, TypeAlias


ParamFunc: TypeAlias = Callable[[float], float]
Param: TypeAlias = ParamFunc | float

ControlPoint: TypeAlias = tuple[float, Param]
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
        start_v = getv(start_v, s)
        end_t, end_v = self.control_points[top]
        end_v = getv(end_v, s)
        ss = (s - start_t) / (end_t - start_t)
        return (self.shape_func(ss) * (end_v - start_v)) + start_v

    def __repr__(self):
        return f"{self.__class__.__name__}({self.control_points})"

    def __add__(self, y):
        return Curve(self.shape_func, [(t, v + y) for (t, v) in self.control_points])

    def __radd__(self, y):
        return self.__add__(y)

    def __sub__(self, y):
        return Curve(self.shape_func, [(t, v - y) for (t, v) in self.control_points])

    def __rsub__(self, y):
        return self.__sub__(y)

    def __mul__(self, y):
        return Curve(self.shape_func, [(t, v * y) for (t, v) in self.control_points])

    def __rmul__(self, y):
        return self.__mul__(y)

    def __truediv__(self, y):
        return Curve(self.shape_func, [(t, v / y) for (t, v) in self.control_points])

    def __rtruediv__(self, y):
        return self.__truediv__(y)

    def __floordiv__(self, y):
        return Curve(self.shape_func, [(t, v // y) for (t, v) in self.control_points])

    def __floorrdiv__(self, y):
        return self.__floordiv__(y)

    def __mod__(self, y):
        return Curve(self.shape_func, [(t, v % y) for (t, v) in self.control_points])

    def __rmod__(self, y):
        return self.__mod__(y)

    def __neg__(self):
        return self.__mul__(-1)


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

    def __add__(self, y):
        return Random(self.minv + y, self.maxv + y, self.length)

    def __sub__(self, y):
        return Random(self.minv - y, self.maxv + y, self.length)

    def __mul__(self, y):
        return Random(self.minv * y, self.maxv + y, self.length)

    def __truediv__(self, y):
        return Random(self.minv / y, self.maxv + y, self.length)

    def __floordiv__(self, y):
        return Random(self.minv // y, self.maxv + y, self.length)

    def __mod__(self, y):
        return Random(self.minv % y, self.maxv + y, self.length)


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

        return self.curves[idx](s - self.starts[idx])
            
    def __add__(self, y):
        return CombinedCurve([
            Curve(curve.shape_func, [(t, v + y) for (t, v) in curve.control_points])
            for curve in self.curves
        ])

    def __sub__(self, y):
        return CombinedCurve([
            Curve(curve.shape_func, [(t, v - y) for (t, v) in curve.control_points])
            for curve in self.curves
        ])

    def __mul__(self, y):
        return CombinedCurve([
            Curve(curve.shape_func, [(t, v * y) for (t, v) in curve.control_points])
            for curve in self.curves
        ])

    def __truediv__(self, y):
        return CombinedCurve([
            Curve(curve.shape_func, [(t, v / y) for (t, v) in curve.control_points])
            for curve in self.curves
        ])

    def __floordiv__(self, y):
        return CombinedCurve([
            Curve(curve.shape_func, [(t, v // y) for (t, v) in curve.control_points])
            for curve in self.curves
        ])

    def __mod__(self, y):
        return CombinedCurve([
            Curve(curve.shape_func, [(t, v % y) for (t, v) in curve.control_points])
            for curve in self.curves
        ])
