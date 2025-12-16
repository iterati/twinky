from enum import Enum
import random
from typing import Callable
from pytweening import linear


type ParamFunc = Callable[[float], float]
type Param = ParamFunc | float
type FuncParamFunc = Callable[[float], list]
type FuncParam = FuncParamFunc | list
type ControlPoint = tuple[float, float]
type ControlPoints = list[ControlPoint]


def getv(v: Param, t: float) -> float:
    return v(t) if callable(v) else v


def getfv(v: FuncParam, t: float) -> list:
    return v(t) if callable(v) else v


def const(_: float) -> float:
    return 0


class curve:
    def __init__(self, shape_func: ParamFunc, control_points: ControlPoints):
        self.shape_func = shape_func
        self.control_points = control_points

    @property
    def length(self) -> float:
        return self.control_points[-1][0] if len(self.control_points) > 0 else 0

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


class Direction(Enum):
    FROM_BOT = 0
    FROM_TOP = 1

class Spin(Enum):
    CLOCKWISE = 0
    COUNTERCLOCKWISE = 1

class Streamer:
    def __init__(self,
                 initial_t,
                 func=None,
                 move_dir: Direction=Direction.FROM_BOT,
                 spin_dir: Spin=Spin.CLOCKWISE,
                 angle: Param | None=None,
                 spin: Param=1.0,
                 length: Param=1.0,
                 width: Param=0.1,
                 lifetime: Param=6.0):
        self.initial_t = initial_t
        self.reverse = move_dir != Direction.FROM_TOP
        if move_dir == Direction.FROM_TOP:
            spind = -1 if spin_dir == Spin.CLOCKWISE else 1
        else:
            spind = 1 if spin_dir == Spin.CLOCKWISE else -1

        self.angle = random.random() if angle is None else angle
        self.spin = spind * getv(spin, initial_t)
        self.length = getv(length, initial_t)
        self.width = getv(width, initial_t)
        self.lifetime = getv(lifetime, initial_t)
        self.func = func

        if self.reverse:
            self.y_func = curve(linear, [(0, -self.length), (self.lifetime, 1)])
        else:
            self.y_func = curve(linear, [(0, 1), (self.lifetime, -self.length)])

    def alive(self, t):
        return t < self.initial_t + self.lifetime

    def contains(self, t, pixel):
        miny = self.y_func(t - self.initial_t)
        maxy = miny + self.length
        mino = (((pixel.y * self.spin) + self.angle) % 1) + 1
        maxo = mino + self.width
        return (miny <= pixel.y <= maxy) and (mino <= pixel.t + 1 <= maxo)

    def __repr__(self):
        return f"Streamer({self.angle},{self.spin},{self.length},{self.width},{self.lifetime})"


type StreamerParamFunc = Callable[[float], list[dict]]
type StreamerParam = StreamerParamFunc | list[dict]


def getv_streamers(v: StreamerParam, t: float) -> list[dict]:
    return v(t) if callable(v) else v
