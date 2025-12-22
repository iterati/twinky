import random
from typing import Callable

def rand(minv=0.0, maxv=1.0) -> Callable[[], float]:
    def func() -> float:
        s = random.random()
        return (s * (maxv - minv)) + minv

    return func

def choice(choices: list[float]) -> Callable[[], float]:
    def func() -> float:
        return random.choice(choices)

    return func

def mk_bump(period, s, e=None):
    if e is None:
        e = s
        s = 0
    return [
        (0,            s),
        (period * 0.5, e),
        (period,       s),
    ]

def mk_bounce(period, s, e=None):
    if e is None:
        e = s
        s = 0
    return [
        (0,             s),
        (period * 0.25, e),
        (period * 0.5,  -s),
        (period * 0.75, -e),
        (period,        s),
    ]
