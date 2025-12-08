import random


def getv(v, t):
    return v(t) if callable(v) else v


def bounce(n=1):
    def func(v):
        r = (v * n) % 1
        r *= 2
        if r > 1.0:
            r = 2.0 - r
        return r

    return func


def chain(*funcs):
    def func(t, pixel):
        for f in funcs:
            f(t, pixel)

    return func


def ident(t, pixel):
    pass


def reset(t, pixel):
    pixel.reset()


def reset_t(t, pixel):
    pixel.t = pixel._t

    
def invert(t, pixel):
    pixel.h = (pixel.h + 0.5) % 1


def invertAndWhite(t, pixel):
    if pixel.l != -1.0:
        pixel.w = 0.75
        pixel.s = 0.4
        pixel.l = 0.75
    else:
        pixel.h = (pixel.h + 0.5) % 1
        pixel.l = 0.0

        
def set(attr, v):
    def func(t, pixel):
        setattr(pixel, attr, getv(v, t))
        
    return func


def add(attr, v):
    def func(t, pixel):
        x = getattr(pixel, attr) + getv(v, t)
        setattr(pixel, attr, x)
        
    return func

def scale(attr, v):
    def func(t, pixel):
        x = getattr(pixel, attr) * getv(v, t)
        setattr(pixel, attr, x)
        
    return func


def color_wash(w=None, h=None, s=None, l=None, y_scale=1):
    def func(t, pixel):
        u = t
        if y_scale:
            u += pixel.y * y_scale

        if w: pixel.w = getv(w, u)
        if h: pixel.h = getv(h, u)
        if s: pixel.s = getv(s, u)
        if l: pixel.l = getv(l, u)

    return func


def blend(f):
    def func(t, pixel):
        pixel.h += getv(f, t)

    return func


def spread(s):
    def func(t, pixel):
        pixel.h += pixel.t * getv(s, t)

    return func


def mirror(m=1):
    def func(t, pixel):
        pixel.t = bounce(getv(m, t))(pixel.t)

    return func


def repeat(n=2):
    def func(t, pixel):
        pixel.t = (pixel.t * getv(n, t)) % 1

    return func


def split(window=0.5):
    def func(t, pixel):
        pixel.t = int(pixel.t + getv(window, t)) / 2

    return func


def panels(panels=3):
    def func(t, pixel):
        pixel.t = int(pixel.t * panels) / panels

    return func
        
    
def spin(s):
    def func(t, pixel):
        pixel.t = (pixel.t + getv(s, t)) % 1

    return func


def spiral(s):
    def func(t, pixel):
        pixel.t = (pixel.t + (pixel.y * getv(s, t))) % 1

    return func


class Effect:
    def __init__(self, pixelf=ident):
        self.pixelf = pixelf

    def init(self, t, pixels):
        pass

    def reset(self, t, pixels):
        pass

    def render(self, t, pixels):
        for pixel in pixels:
            self.pixelf(t, pixel)
    

class Sparkle(Effect):
    def __init__(self, chance=0.25, length=0.25, pixelf=set('w', 1.0)):
        self.chance = chance
        self.length = length
        self.pixelf = pixelf
        self.next_sparkle = 0
        self.picks = []

    def reset(self, t, pixels):
        self.next_sparkle = 0
        self.picks = []
        
    def render(self, t, pixels):
        if t >= self.next_sparkle:
            self.picks = random.choices(
                range(len(pixels)),
                k=int(getv(self.chance, t) * len(pixels))
            )
            self.next_sparkle = t + getv(self.length, t)

        for pixel in pixels:
            idx = pixel.idx + (400 * pixel.strand)
            if idx in self.picks:
                self.pixelf(t, pixel)


class Streamers(Effect):
    class Streamer:
        def __init__(self, initial_t, angle, length, width, speed, spin, reverse):
            self.angle = angle
            self.length = length
            self.width = width
            self.speed = speed
            self.spin = spin
            self.reverse = reverse
            self.y = 1.0 if reverse else -length
            self.last_update = initial_t

        def update(self, t):
            d = t - self.last_update
            self.last_update = t
            if self.reverse:
                self.y -= d / self.speed
            else:
                self.y += d / self.speed

        @property
        def alive(self):
            if self.reverse:
                return self.y > -self.length
            else:
                return self.y < 1.0 + self.length

        def contains(self, pixel):
            miny = self.y
            maxy = miny + self.length
            mino = (((pixel.y * self.spin) + self.angle) % 1) + 1
            maxo = mino + self.width
            return (miny <= pixel.y <= maxy) and (mino <= pixel._t + 1 <= maxo)

        def __repr__(self):
            return f'y={round(self.y, 2)} yTop={round(self.y + self.length, 2)} angle={round(self.angle, 2)} alive={self.alive}'

    def __init__(self,
                 length=0.2,
                 width=0.01,
                 delay=3,
                 emit=1,
                 speed=5,
                 spin=5,
                 pixelf=ident,
                 reverse=False):
        self.length = length
        self.width = width
        self.delay = delay
        self.emit = emit
        self.speed = speed
        self.spin = spin
        self.pixelf = pixelf
        self.reverse = reverse
        self.next_trigger = 0
        self.streamers = []

    def init(self, t, pixels):
        self.streamers = []
        self.next_trigger = 0

    def reset(self, t, pixels):
        self.streamers = []
        self.next_trigger = 0

    def render(self, t, pixels):
        streamers = []
        if t >= self.next_trigger:
            for _ in range(getv(self.emit, t)):
                streamer = self.Streamer(
                    t,
                    random.random(),
                    getv(self.length, t),
                    getv(self.width, t),
                    getv(self.speed, t),
                    getv(self.spin, t),
                    self.reverse,
                )
                self.streamers.append(streamer)

            self.next_trigger = t + getv(self.delay, t)

        for streamer in self.streamers:
            streamer.update(t)
            if streamer.alive:
                streamers.append(streamer)

        self.streamers = streamers

        for pixel in pixels:
            for streamer in self.streamers:
                if streamer.contains(pixel):
                    self.pixelf(t, pixel)
