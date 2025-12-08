import random as rand

from effects import (
    bounce,
    getv,
)


class tween:
    def __init__(self, length, shapef, minv, maxv, circular=False):
        self.shapef = shapef
        self.length = length
        self.minv = minv
        self.maxv = maxv
        self.circular = circular

    def __call__(self, t):
        s = (t / self.length) % 1
        r = bounce(1)(s) if self.circular else s
        r = self.shapef(r)
        return (r * (self.maxv - self.minv)) + self.minv


class const:
    def __init__(self, length, v):
        self.length = length
        self.v = v
        
    def __call__(self, t):
        return self.v


class ordered:
    def __init__(self, length, interval, choices):
        self.length = length
        self.interval = interval
        self.choices = choices
        
    def __call__(self, t):
        i = int(t / self.interval) % len(self.choices)
        return self.choices[i]


class stepped:
    def __init__(self, length, interval, steps=2, minv=0.0, maxv=1.0):
        self.length = length
        self.interval = interval
        self.minv = minv
        self.maxv = maxv
        self.steps = steps

    def __call__(self, t):
        s = int(t / self.interval) % self.steps
        r = s / self.steps
        return (r * (self.maxv - self.minv)) + self.minv


class random:
    def __init__(self, length, minv=0.0, maxv=1.0):
        self.length = length
        self.minv = minv
        self.maxv = maxv

    def __call__(self, t):
        n = getv(self.minv, t)
        m = getv(self.maxv, t)
        return (rand.random() * (m - n)) + n


class choice:
    def __init__(self, length, choices):
        self.length = length
        self.choices = choices
        
    def __call__(self, t):
        return rand.choice(self.choices)


class curve:
    def __init__(self, tweens, circular=False):
        self.tweens = tweens
        self.length = sum(t.length for t in tweens)
        self.circular = circular
        self.ranges = []
        s = 0
        for t in tweens:
            self.ranges.append((s, s + t.length))
            s += t.length

    @property
    def total_length(self):
        return self.length * 2 if self.circular else self.length

    def __call__(self, t):
        s = t % self.total_length
        if s > self.length:
            s = self.total_length - s

        for i, (start, end) in enumerate(self.ranges):
            if start <= s < end:
                return self.tweens[i](s - start)
