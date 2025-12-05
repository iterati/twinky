import io
import math
from pytweening import (
    linear,
    easeInOutSine,
)
import random
import struct
import time
import xled
from xled_plus.ledcolor import hsl_color, set_color_style

import effects
from effects import (
    Effect,
    bounce,
    getv,
)


PI = math.pi
PI_2 = math.pi / 2


class Tween:
    def __init__(self, shapef, length, minv, maxv, circular=False):
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


class Curve:
    def __init__(self, *tweens, circular=False):
        self.tweens = tweens
        self.length = sum(t.length for t in tweens)
        self.circular = circular
        self.ranges = []
        s = 0
        for t in tweens:
            self.ranges.append((s, s + t.length))
            s += t.length

        self.init_time = time.time()

    def __call__(self, t):
        total_length = self.length * 2 if self.circular else self.length
        s = (t - self.init_time) % total_length
        if s > self.length:
            s = total_length - s

        for i, (start, end) in enumerate(self.ranges):
            if start <= s < end:
                return self.tweens[i](s - start)


def rand(minv, maxv):
    def func(t):
        n = getv(minv, t)
        m = getv(maxv, t)
        return (random.random() * (m - n)) + n

    return func


def randc(*choices):
    def func(t):
        return random.choice(choices)

    return func


class Color:
    def __init__(self, w=0, h=0.0, s=1.0, l=-1.0):
        self.w, self.h, self.s, self.l = w, h, s, l

    def reset(self):
        self.w, self.h, self.s, self.l = 0, 0, 1.0, -1.0

    def as_byte(self):
        rgb = hsl_color(self.h % 1, self.s, self.l)
        return struct.pack('>BBBB', self.w, *rgb)
        

class Pixel:
    def __init__(self, strand, idx, x, y, z):
        self.y = y
        self._t = ((math.atan2(z, x) / math.pi) + 1) / 2
        self.t = self._t
        self.strand = strand
        self.idx = idx
        self.color = Color()

    def reset(self):
        self.t = self._t
        self.color.reset()

    @property
    def w(self):
        return self.color.w

    @w.setter
    def w(self, w):
        self.color.w = max(min(int(w), 255), 0)
 
    @property
    def h(self):
        return self.color.h

    @h.setter
    def h(self, h):
        self.color.h = h % 1
 
    @property
    def s(self):
        return self.color.s

    @s.setter
    def s(self, s):
        self.color.s = max(min(s, 1.0), 0.0)
 
    @property
    def l(self):
        return self.color.l

    @l.setter
    def l(self, l):
        self.color.l = max(min(l, 1.0), -1.0)
 
    def as_byte(self):
        return self.color.as_byte()


class Interface(xled.control.ControlInterface):
    def __init__(self, device):
        super(Interface, self).__init__(device.ip_address)
        self.device = device
        self.layout = self.get_led_layout()['coordinates']


class Lights:
    def __init__(self):
        dgen = xled.discover.xdiscover()
        devices = [next(dgen), next(dgen)]
        print("Found:", devices)
        self.interfaces = [Interface(device) for device in devices]
        print("Connected")
        self.udpclient = self.interfaces[0].udpclient


class Animation:
    def __init__(self, lights, effects):
        self.lights = lights
        self.effects = effects
        self.buffers = [io.BytesIO() for _ in lights.interfaces]
        self.light_pixels = [
            [Pixel(strand, idx, **p) for idx, p in enumerate(interface.layout)]
            for strand, interface in enumerate(lights.interfaces)
        ]

    def init(self, t):
        for effect in self.effects:
            effect.init(t)

    def reset(self, t):
        for effect in self.effects:
            effect.reset(t)

    def render(self, t):
        for interface, buffer, pixels in zip(lights.interfaces, self.buffers, self.light_pixels):
            for effect in self.effects:
                effect.tick(t)

            buffer.seek(0)
            for pixel in pixels:
                for effect in self.effects:
                    effect.render_pixel(t, pixel)

                buffer.write(pixel.as_byte())
                
            # write to light
            interface.set_mode("rt")
            interface._udpclient = lights.udpclient
            interface.udpclient.destination_host = interface.host
            buffer.seek(0)
            interface.set_rt_frame_socket(buffer, 3)


set_color_style('8col')
# set_color_style('linear')
lights = Lights()


def rainbow_spirals(
        mirror=3,
        spin=Tween(linear, 11, 0, 1),
        spiral=5,
        blend=Tween(linear, 120, 0, 1),
        spread=Curve(
            Tween(easeInOutSine, 5, 0, 8/8, True),
            Tween(easeInOutSine, 5, 0, -8/8, True),
        ),
):
    return Animation(
        lights=lights,
        effects=[
            Effect(effects.reset),
            Effect(effects.setl(0.0)),
            Effect(effects.mirror(mirror)),
            Effect(effects.spin(spin)),
            Effect(effects.spiral(spiral)),
            Effect(effects.spread(spread)),
            Effect(effects.blend(blend)),
        ]
    )

def crossing_streamers(
        blend=Tween(linear, 30, 0, 1),
        length=randc(1/5, 1/4, 1/3, 1/2, 2/3, 3/4, 1),
        width=rand(0.05, 0.15),
        delay=rand(0.25, 1.0),
        emit=1,
        speed=randc(*[i/2 for i in range(2,6)]),
        spin=randc(-2, -3/2, -1, -3/4, -2/3, -1/2, -1/3, 1/3, 1/2, 2/3, 3/4, 1, 3/2, 2),
):
    def mk_crossing_streamer(pixelf, reverse):
        return effects.Streamers(
            length=length,
            width=width,
            delay=delay,
            emit=emit,
            speed=speed,
            spin=spin,
            pixelf=pixelf,
            reverse=reverse,
        )

    return Animation(
        lights=lights,
        effects=[
            Effect(effects.reset),
            mk_crossing_streamer(effects.setl(0.0), False),
            mk_crossing_streamer(effects.setl(0.0), True),
            mk_crossing_streamer(effects.invertAndWhite, False),
            mk_crossing_streamer(effects.invertAndWhite, True),
            Effect(effects.blend(blend)),
        ]
    )


def dancing_tree(
        spin=Tween(easeInOutSine, 10, -1, 1, True),
        spiral=Tween(linear, 2, -3, 3, True),
        color_repeats=1,
        colors=[Color(h=0/8, l=0.0), Color(h=2/8, l=0.0), Color(h=5/8, l=0.0)],
        sparkle_chance=0.5,
):
    return Animation(
        lights=lights,
        effects=[
            Effect(effects.reset),
            Effect(effects.spin(spin)),
            Effect(effects.spiral(spiral)),
            Effect(effects.multi_color(color_repeats, colors)),
            effects.Sparkle(
                chance=sparkle_chance,
                pixelf=effects.chain(effects.setw(192), effects.sets(0.0)),
            ),
            effects.Sparkle(
                chance=sparkle_chance,
                pixelf=effects.chain(effects.setw(0), effects.setl(-1.0)),
            ),
        ]
    )


def color_fall(
        fade=0.5,
        length=5,
        y_scale=5,
        blend_time=30,
        hue_range=1/8,
):
    hue = hue_range / 2
    return Animation(
        lights=lights,
        effects=[
            Effect(effects.reset),
            Effect(effects.color_wash(
                l=Curve(
                    Tween(linear, fade, -1, -1),
                    Tween(easeInOutSine, length - (fade * 2), -1, 0),
                    Tween(linear, fade, 0, 0),
                    circular=True,
                ),
                y_scale=y_scale,
            )),
            Effect(effects.blend(Tween(linear, blend_time, 0, 1))),
            Effect(effects.addh(rand(-hue, hue))),
            effects.Sparkle(
                pixelf=effects.chain(effects.setw(192), effects.sets(0.0), effects.setl(0.75))
            )
        ]
    )


def animate(animation):
    start = time.time()
    animation.init(start)
    while True:
        since_start = time.time() - start
        animation.render(since_start)
    

def playlist(seg_length, animations):
    start = time.time()
    for animation in animations:
        animation.init(start)

    active_animation = 0
    while True:
        since_start = time.time() - start
        idx = int(since_start / seg_length) % len(animations)
        if idx != active_animation:
            animations[idx].reset(since_start)
            active_animation = idx
            
        animations[idx].render(since_start)


playlist(60, [color_fall(), dancing_tree(), crossing_streamers(), rainbow_spirals()])
