from param import Param, ParamFunc, Curve, getv
from pytweening import easeInOutSine


class Topology:
    def __call__(self, t: float, pixel_t: float, pixel_y: float) -> float:
        return pixel_t


class MirrorTopology(Topology):
    def __init__(self, count: Param):
        self.count = count

    def __call__(self, t: float, pixel_t: float, pixel_y: float) -> float:
        count = getv(self.count, t)
        r = ((pixel_t * count) % 1) * 2
        return r if r < 1.0 else 2.0 - r


class RepeatTopology(Topology):
    def __init__(self, count: Param):
        self.count = count

    def __call__(self, t: float, pixel_t: float, pixel_y: float) -> float:
        count = getv(self.count, t)
        return (pixel_t * count) % 1


class TurntTopology(Topology):
    def __init__(self, count: Param, turn: Param):
        self.count = count
        self.turn = turn

    def __call__(self, t: float, pixel_t: float, pixel_y: float) -> float:
        count = getv(self.count, t)
        turn = getv(self.turn, t)
        y_bin = int(pixel_y * count)
        return (pixel_t + (y_bin * turn)) % 1


class DistortTopology(Topology):
    def __init__(self,
                 shape_func: ParamFunc,
                 top_d: Param=0,
                 bot_d: Param=0,
                 mid: Param=0.5):
        self.shape_func = shape_func
        self.top_d = top_d
        self.bot_d = bot_d
        self.mid = mid

    def __call__(self, t: float, pixel_t: float, pixel_y: float) -> float:
        top_d = getv(self.top_d, t)
        bot_d = getv(self.bot_d, t)
        mid = getv(self.mid, t)
        distort_func = Curve(self.shape_func, [
            (0, 0),
            (mid/2, bot_d),
            (mid, 0),
            ((1-mid)/2, top_d),
            (1, 0),
        ])
        return pixel_t + getv(distort_func, pixel_y)
