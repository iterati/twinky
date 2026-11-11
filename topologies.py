from typing import Callable, TypeAlias

from param import Param, CurveFunc, Curve, getv

# A topology, once a frame, gives the function that moves each light's (pixel_t, pixel_y) to its new pixel_t
TopologyFunc: TypeAlias = Callable[[float, float], float]

class Topology:
    def __call__(self, t: float) -> TopologyFunc:
        return lambda pixel_t, pixel_y: pixel_t

class SpinTopology(Topology):
    def __init__(self, angle: Param):
        self.angle = angle

    def __call__(self, t: float) -> TopologyFunc:
        angle = getv(self.angle, t)
        return lambda pixel_t, pixel_y: (pixel_t + angle) % 1

class SpiralTopology(Topology):
    def __init__(self, turn: Param, mid: Param=0):
        self.turn = turn
        self.mid = mid

    def __call__(self, t: float) -> TopologyFunc:
        turn = getv(self.turn, t)
        mid = getv(self.mid, t)
        return lambda pixel_t, pixel_y: (pixel_t + ((pixel_y - mid) * turn)) % 1

class DistortTopology(Topology):
    def __init__(self,
                 shape_func: CurveFunc,
                 top_d: Param=0,
                 bot_d: Param=0,
                 mid: Param=0.5):
        self.shape_func = shape_func
        self.top_d = top_d
        self.bot_d = bot_d
        self.mid = mid

    def __call__(self, t: float) -> TopologyFunc:
        top_d = getv(self.top_d, t)
        bot_d = getv(self.bot_d, t)
        mid = getv(self.mid, t)
        distort_func = Curve(self.shape_func, [
            (0, 0),
            (mid/2, bot_d),
            (mid, 0),
            ((1+mid)/2, top_d),
            (1, 0),
        ])
        return lambda pixel_t, pixel_y: pixel_t + getv(distort_func, pixel_y)

class MirrorTopology(Topology):
    def __init__(self, count: Param):
        self.count = count

    def __call__(self, t: float) -> TopologyFunc:
        count = getv(self.count, t)

        def func(pixel_t: float, pixel_y: float) -> float:
            r = ((pixel_t * count) % 1) * 2
            return r if r < 1.0 else 2.0 - r
        return func

class RepeatTopology(Topology):
    def __init__(self, count: Param):
        self.count = count

    def __call__(self, t: float) -> TopologyFunc:
        count = getv(self.count, t)
        return lambda pixel_t, pixel_y: (pixel_t * count) % 1
