import random
from typing import Any, Callable, TypeAlias

CurveFunc: TypeAlias = Callable[[float], float]
ControlPoint: TypeAlias = tuple[float, float]
ControlPoints: TypeAlias = list[ControlPoint]

class Curve:
    def __init__(self, shape_func: CurveFunc, control_points: ControlPoints):
        if len(control_points) < 2:
            raise ValueError("Need at least 2 control_points")
            
        self.shape_func = shape_func
        self.control_points = control_points
        self.length = self.control_points[-1][0]

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
        return f"{self.__class__.__name__}({self.control_points})"

    def __add__(self, y):
        return Curve(self.shape_func, [(t, v + y) for (t, v) in self.control_points])

    def __radd__(self, y):
        return self.__add__(y)

    def __sub__(self, y):
        return Curve(self.shape_func, [(t, v - y) for (t, v) in self.control_points])

    def __rsub__(self, y):
        return Curve(self.shape_func, [(t, y - v) for (t, v) in self.control_points])

    def __mul__(self, y):
        return Curve(self.shape_func, [(t, v * y) for (t, v) in self.control_points])

    def __rmul__(self, y):
        return self.__mul__(y)

    def __truediv__(self, y):
        return Curve(self.shape_func, [(t, v / y) for (t, v) in self.control_points])

    def __rtruediv__(self, y):
        return Curve(self.shape_func, [(t, y / v) for (t, v) in self.control_points])

    def __floordiv__(self, y):
        return Curve(self.shape_func, [(t, v // y) for (t, v) in self.control_points])

    def __floorrdiv__(self, y):
        return Curve(self.shape_func, [(t, y // v) for (t, v) in self.control_points])

    def __mod__(self, y):
        return Curve(self.shape_func, [(t, v % y) for (t, v) in self.control_points])

    def __rmod__(self, y):
        return Curve(self.shape_func, [(t, y % v) for (t, v) in self.control_points])

    def __neg__(self):
        return self.__mul__(-1)

Param: TypeAlias = CurveFunc | Curve | float

def getv(v: Param, t: float) -> float:
    return v(t) if callable(v) else v

def const(_: float) -> float:
    return 0

def rand(minv: float=0.0, maxv: float=1.0) -> CurveFunc:
    def func(_: float) -> float:
        s = random.random()
        return (s * (maxv - minv)) + minv
    return func

def choice(choices: Callable[[float], list[Param]] | list[Param]) -> CurveFunc:
    def func(t: float) -> Any:
        c = choices(t) if callable(choices) else choices
        pick = random.choice(c)
        return getv(pick, t)
    return func
