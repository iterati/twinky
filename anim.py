import io
import math
from pytweening import (
    linear,
    easeInOutSine,
    easeInOutCubic,
)
import random as rand
import struct
import time
from xled.discover import xdiscover
from xled.control import ControlInterface
from xled_plus.ledcolor import (
    hsl_color,
    set_color_style,
)

from curves import (
    curve,
    tween,
    const,
    ordered,
    stepped,
    random,
    choice,
)

import effects
from effects import (
    Effect,
    getv,
)


PI = math.pi
PI_2 = math.pi / 2


class Color:
    def __init__(self, w=0, h=0.0, s=1.0, l=-1.0):
        self.w, self.h, self.s, self.l = w, h, s, l

    def reset(self):
        self.w, self.h, self.s, self.l = 0, 0, 1.0, -1.0

    def as_byte(self):
        rgb = hsl_color(self.h % 1, self.s, self.l)
        return struct.pack('>BBBB', int(self.w * 255), *rgb)
        

class Pixel:
    def __init__(self, strand, idx, x, y, z):
        self._y = y
        self.y = self._y
        self._t = ((math.atan2(z, x) / math.pi) + 1) / 2
        self.t = self._t
        self.strand = strand
        self.idx = idx
        self.color = Color()

    def reset(self):
        self.t = self._t
        self.y = self._y
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


class Interface(ControlInterface):
    def __init__(self, device):
        super(Interface, self).__init__(device.ip_address)
        self.device = device
        self.layout = self.get_led_layout()['coordinates']


class Lights:
    def __init__(self):
        dgen = xdiscover()
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

    @property
    def pixels(self):
        return self.light_pixels[0] + self.light_pixels[1]

    def init(self, t):
        for effect in self.effects:
            effect.init(t, self.pixels)

    def reset(self, t):
        for effect in self.effects:
            effect.reset(t, self.pixels)

    def render(self, t):
        for effect in self.effects:
            effect.render(t, self.pixels)
        
        for interface, buffer, pixels in zip(lights.interfaces, self.buffers, self.light_pixels):
            buffer.seek(0)
            for pixel in pixels:
                buffer.write(pixel.as_byte())
                
            interface._udpclient = lights.udpclient
            interface.udpclient.destination_host = interface.host
            buffer.seek(0)
            interface.set_rt_frame_socket(buffer, 3)


def rainbow_spirals(
        lights,
        mirror=3,
        spin=tween(10, linear, 0, 1),
        spiral=5,
        blend=tween(60, linear, 0, 1),
        spread=curve([
            tween(5, easeInOutSine, 0, 8/8, True),
            tween(5, easeInOutSine, 0, -8/8, True),
        ]),
):
    return Animation(
        lights=lights,
        effects=[
            Effect(effects.reset),
            Effect(effects.set('h', blend)),
            Effect(effects.set('l', 0.0)),
            Effect(effects.mirror(mirror)),
            Effect(effects.spin(spin)),
            Effect(effects.spiral(spiral)),
            Effect(effects.spread(spread)),
        ]
    )

def crossing_streamers(
        lights,
        blend=tween(30, linear, 0, 1),
        length=choice(1, [1/5, 1/4, 1/3, 1/2, 2/3, 3/4, 1]),
        width=random(1, 0.05, 0.15),
        delay=random(1, 0.25, 1.0),
        emit=1,
        speed=choice(1, [i/2 for i in range(2,6)]),
        spin=choice(1, [-2, -3/2, -1, -3/4, -2/3, -1/2, -1/3, 1/3, 1/2, 2/3, 3/4, 1, 3/2, 2]),
):
    def streamer(pixelf, reverse):
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

    def invert_white(t, pixel):
        if pixel.l == -1.0:
            pixel.h = (pixel.h + 0.5) % 1
            pixel.l = 0.0
        else:
            pixel.w = 0.75
            pixel.s = 0.4
            pixel.l = 0.75

    return Animation(
        lights=lights,
        effects=[
            Effect(effects.reset),
            Effect(effects.set('h', blend)),
            streamer(effects.set('l', 0.0), False),
            streamer(effects.set('l', 0.0), True),
            streamer(invert_white, False),
            streamer(invert_white, True),
        ]
    )


def dancing_tree(
        lights,
        spin=tween(10, easeInOutSine, -1, 1, True),
        spiral=tween(5, linear, -3, 3, True),
        colors=3,
        sparkle_chance=0.5,
):
    def split_colors(t, pixel):
        pixel.h += int(pixel.t * colors) / colors

    return Animation(
        lights=lights,
        effects=[
            Effect(effects.reset),
            Effect(effects.set('l', 0.0)),
            Effect(effects.spin(spin)),
            Effect(effects.spiral(spiral)),
            Effect(effects.add('h', tween(60, linear, 0, 1))),
            Effect(split_colors),
            effects.Sparkle(
                chance=sparkle_chance,
                pixelf=effects.chain(
                    effects.set('w', 0.75),
                    effects.set('s', 0.0),
                ),
            ),
            effects.Sparkle(
                chance=sparkle_chance,
                pixelf=effects.chain(
                    effects.set('w', 0),
                    effects.set('l', -1.0),
                ),
            ),
        ]
    )


def slider(lights):
    def streamer(reverse):
        return effects.Streamers(
            length=1,
            width=0.05,
            delay=0.5,
            emit=choice(1, [1, 2]),
            speed=1.5,
            spin=choice(1, [-2, -3/2, -1, -3/4, -2/3, -1/2, -1/3, 1/3, 1/2, 2/3, 3/4, 1, 3/2, 2]),
            pixelf=effects.chain(
                effects.set('w', 0.75),
                effects.set('s', 0.0),
            ),
            reverse=reverse,
        )
        
    return Animation(
        lights=lights,
        effects=[
            Effect(effects.reset),
            Effect(effects.repeat(3)),
            Effect(effects.split(tween(5, linear, 0.0, 1.0))),
            Effect(effects.spread(1)),
            Effect(effects.set('l', 0.0)),
            Effect(effects.add('h', stepped(1, 5, 2))),
            Effect(effects.add('h', random(1, -1/16, 1/16))),
            Effect(effects.add('h', tween(60, linear, 0, -1))),
            streamer(True),
            streamer(False),
        ]
    )

def stained_glass(
        lights,
        length=2,
        width=0.1,
        delay=10,
        speed=10,
        blend_time=60,
        split_time=15,
        split_min=1/64,
        split_max=1/3,
):
    def streamer(inv=False):
        choices = [1, 2, 3, 4, 5]
        spin = choice(1, [-i for i in choices]) if inv else choice(1, choices)
        return effects.Streamers(
            length=length,
            width=width,
            delay=delay,
            speed=speed,
            spin=spin,
            pixelf=effects.chain(
                effects.set('w', 0.5),
                effects.set('s', 0.5),
                effects.set('l', 0.5),
            ),
            reverse=False,
        )

    return Animation(
        lights=lights,
        effects=[
            Effect(effects.reset),
            Effect(effects.set('l', random(1, -0.25, .1))),
            Effect(effects.set('s', random(1, 1.0, 0.8))),
            Effect(effects.set('h', curve(
                [tween(blend_time/8, easeInOutSine, -i/8, -(i+1)/8) for i in range(8)],
                circular=True,
            ))),
            Effect(effects.add('h', random(
                1, 
                tween(split_time, linear, -split_min, -split_max, True),
                tween(split_time, linear, split_min, split_max, True),
            ))),
            streamer(False),
            streamer(True),
        ]
    )


def color_fall(
        lights,
        num_colors=8,
        colors_at_once=0.75,
        color_step=3,
):
    def foo(t, pixel):
        fy = tween(60, linear, 0, num_colors)
        y = ((pixel.y + getv(fy, t)) * colors_at_once) % num_colors
        h = (int(y) * color_step) % num_colors
        fl = tween(1, easeInOutCubic, -1.0, 0.25, True)
        pixel.w = 0
        pixel.h = h / num_colors
        pixel.s = 1.0
        pixel.l = fl(y)
    
    return Animation(
        lights=lights,
        effects=[
            Effect(effects.reset),
            Effect(foo),
            Effect(effects.add('h', random(1, -1/16, 1/16))),
            effects.Sparkle(
                chance=0.25,
                pixelf=effects.chain(
                    effects.set('w', 0.75),
                    effects.set('s', 0.0),
                    effects.set('l', 0.0),
                ),
            ),
        ],
    )


def evolver(lights):
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


    def whiten(pixel):
        pixel.w = 0.75
        pixel.s = 0.0
        pixel.l = 0

    class Evolver(Effect):
        # 60s for color fall
        # 12s color goes black, crossing streamers start over sparkles fading
        # 60s for crossing streamers
        # 12s streamers cover the tree, fade out to dancing tree
        # 60s for dancing tree
        # 12s spiral stalls, colors fade to single hue
        # 60s for rainbow spiral/stained glass
        # 12s spiral reverses, streamers fade, hue collapses
        # 60s for slider
        # 12s slider slides in blank with sparkles
        # repeat (6min)
        def __init__(self):
            self.sparkles = []
            self.blinks = []
            self.streamers = []
            self.last_update = 0

            self.flicker_time = 0.25

            self.sparkle_chance_f = curve([])
            self.blink_chance_f = curve([])
            self.base_h_f = curve([])
            self.base_s_f = curve([])
            self.base_l_f = curve([])
            self.spin_f = curve([])
            self.spiral_f = curve([])
            self.scale_f = curve([])
            self.offset_f = curve([])

        def reset(self, t, pixels):
            self.sparkles = []
            self.blinks = []
            self.streamers = []
            self.last_update = t
            self.next_streamer = t

        def render(self, t, pixels):
            base_h = getv(self.base_h_f, t)
            base_s = getv(self.base_s_f, t)
            base_l = getv(self.base_l_f, t)
            spin = getv(self.spin_f, t)
            spiral = getv(self.spiral_f, t)
            scale = getv(self.scale_f, t)
            offset = getv(self.offset_f, t)

            if t >= self.last_update + self.flicker_time:
                self.sparkles = rand.choices(range(len(pixels)), k=int(getv(self.sparkle_chance_f, t) * len(pixels)))
                self.blinks = rand.choices(range(len(pixels)), k=int(getv(self.blink_chance_f, t) * len(pixels)))

            for pixel in pixels:
                pixel.reset()
                pixel_idx = pixel.idx + (400 * pixel.strand)

                if pixel_idx in self.blinks:
                    pixel.reset()
                elif pixel_idx in self.sparkles:
                    whiten(pixel)
                else:
                    pixel.w, pixel.h, pixel.s, pixel.l = 0, base_h, base_s, base_l
                    pixel.t = (pixel.t + spin + (pixel.y * spiral))
                    pixel.y = (pixel.y + offset + (pixel.y * scale))


            self.last_update = t
        
    return Animation(
        lights=lights,
        effects=[Effect(Evolver)],
    )

    
def animate(animation):
    start = time.time()
    animation.init(start)
    for interface in animation.lights.interfaces:
        interface.set_mode("rt")
    
    while True:
        since_start = time.time() - start
        frame_start = time.time()
        animation.render(since_start)
        while time.time() < frame_start + (1 / 30):
            pass


def playlist(seg_length, animations):
    start = time.time()
    for animation in animations:
        animation.init(start)

    for interface in animations[0].lights.interfaces:
        interface.set_mode("rt")

    active_animation = 0
    while True:
        since_start = time.time() - start
        frame_start = time.time()
        idx = int(since_start / seg_length) % len(animations)
        if idx != active_animation:
            animations[idx].reset(since_start)
            active_animation = idx
            
        animations[idx].render(since_start)
        while time.time() < frame_start + (1 / 30):
            pass


set_color_style('8col')
# set_color_style('linear')
lights = Lights()
modes = [
    color_fall,
    stained_glass,
    slider,
    dancing_tree,
    crossing_streamers,
    rainbow_spirals,
]

playlist(60, [f(lights) for f in modes])
# animate(evolver(lights))
