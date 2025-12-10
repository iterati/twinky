import math
from pytweening import (
    linear,
    easeInOutSine,
    easeInOutCubic,
)
import random as rand
import time

from core import (
    Lights,
    Animation,
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


class Streamer:
    def __init__(
            self,
            initial_t,
            angle,
            length,
            width,
            speed,
            spin,
            reverse,
    ):
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
        return f'y={round(self.y, 2)} yTop={round(self.y + self.length, 2)} angle={round(self.angle, 2)} alive={self.alive()}'


def whiten(pixel):
    pixel.w = 0.75
    pixel.s = 0.0
    pixel.l = 0.0


def blank(pixel):
    pixel.w = 0
    pixel.l = -1.0


def justhue(hue):
    def func(pixel):
        pixel.w = 0
        pixel.h = hue
        pixel.s = 1.0
        pixel.l = 0.0

    return func


def invertwhite(hue):
    def func(pixel):
        if pixel.l == 0.0:
            whiten(pixel)
        else:
            pixel.w = 0
            pixel.h = hue + 0.5
            pixel.s = 1.0
            pixel.l = 0.0

    return func


class Evolver(Effect):
    def __init__(self):
        self.sparkles = []
        self.blinks = []
        self.hue_streamers = []
        self.inv_streamers = []
        self.last_update = 0
        self.next_sparkle = 0
        self.next_streamer = 0
        self.initial_fall = None
        self.offset = 0

    def reset(self, t, pixels):
        self.sparkles = []
        self.blinks = []
        self.hue_streamers = []
        self.inv_streamers = []
        self.last_update = t
        self.next_sparkle = t
        self.next_streamer = t
        self.initial_fall = None
        self.offset = 0

    def blend(self, t):
        return getv(tween(60, linear, 0, 1), t)

    def flux(self, t):
        return getv(random(-1/16, 1/16), t)

    def new_streamer(self, t, spin_dir, reverse, width=0.1):
        return Streamer(
            t,
            angle=rand.random(),
            length=1.0,
            width=width,
            speed=3,
            spin=spin_dir*2,
            reverse=reverse,
        )

    def update_sparkles(self, t, pixels, chance):
        if t >= self.next_sparkle:
            self.sparkles = rand.choices(
                range(len(pixels)),
                k=int(len(pixels) * chance),
            )
            self.next_sparkle = t + 0.25

    def sparkle_pixel(self, pixel, f):
        idx = pixel.idx + (400 * pixel.strand)
        if idx in self.sparkles:
            f(pixel)

    def update_streamers(self, t, streamers, reverse, make_new=True, width=0.1, update=False):
        if t >= self.next_streamer:
            if make_new:
                streamers.extend(
                    self.new_streamer(t, spin_dir, reverse, width)
                    for spin_dir in [1, -1]
                )
            if update:
                self.next_streamer = t + 1.0

        new_streamers = []
        for streamer in streamers:
            streamer.update(t)
            if streamer.alive():
                new_streamers.append(streamer)

        streamers = new_streamers

    def streamer_pixel(self, pixel, streamers, func):
        for streamer in streamers:
            if streamer.contains(pixel):
                func(pixel)

    def slider(self, t, pixels):
        self.update_sparkles(t, pixels, 0.25)
        window = getv(tween(6, linear, 0.0, 1.0), t)
        for pixel in pixels:
            pixel.reset()
            side = (pixel.t * 3) % 1
            side = int(side + window)
            pixel.h = (
                (side * 0.5)
              + (0.5 * int(t / 6))
              + self.blend(t)
              + self.flux(t)
            ) % 1
            pixel.l = 0.0
            self.sparkle_pixel(pixel, whiten)

    def slider_to_fall(self, t, pixels):
        self.update_sparkles(t, pixels, 0.25)
        window = getv(tween(6, linear, 0.0, 1.0), t)
        for pixel in pixels:
            pixel.reset()
            side = (pixel.t * 3) % 1
            side = int(side + window)
            pixel.h = (
                (side * 0.5)
                + (0.5 * int(t / 6))
                + self.blend(t)
                + self.flux(t)
            ) % 1
            pixel.l = 0.0 if side == 0 else -1.0
            self.sparkle_pixel(pixel, [blank, whiten][side])

    def slider_to_streamers(self, t, pixels):
        pass

    def slider_to_glass(self, t, pixels):
        sparkle_chance = getv(tween(6, linear, 0.25, 0.0), t)
        self.update_sparkles(t, pixels, sparkle_chance)
        self.update_streamers(t, self.hue_streamers, False)
        self.update_streamers(t, self.inv_streamers, True, update=True)
        spread = getv(curve([
            tween(3, easeInOutSine, 0, 1/3, True),
            tween(3, easeInOutSine, 0, -1/3, True),
        ]), t)
        spiral = 2 if int(t / 6) % 2 == 0 else -2
        for pixel in pixels:
            pixel.reset()
            pixel_t = effects.bounce(2)(pixel.t) % 1
            pixel_t = (pixel_t + (pixel.y * spiral)) % 1
            pixel.h = (
                (pixel_t * spread)
              + self.blend(t)
              + self.flux(t)
            ) % 1
            pixel.l = 0.0
            self.sparkle_pixel(pixel, whiten)
            self.streamer_pixel(pixel, self.inv_streamers, whiten)

    def fall(self, t, pixels):
        # TODO: unfuck
        if not self.initial_fall:
            self.initial_fall = getv(tween(60, linear, 0.0, 1.0), t)

        self.update_sparkles(t, pixels, 0.25)
        color_offset = getv(tween(60, linear, -1.0, 9.0), t - self.offset)
        for pixel in pixels:
            pixel.reset()
            color_y = pixel.y + color_offset
            pixel.s = 1.0
            if color_y <= 0.0 or color_y > 8.0:
                pixel.l = -1.0
            else:
                color_y = color_y % 8.0
                pixel.h = (
                    self.initial_fall
                  + ((int(color_y + 3) * 3) % 8) / 8
                  + self.flux(t)
                )
                pixel.l = getv(tween(1, easeInOutCubic, -1.0, 0.0, True), color_y)

            self.sparkle_pixel(pixel, whiten)

    def fall_to_slider(self, t, pixels):
        self.update_sparkles(t, pixels, 0.25)
        window = getv(tween(6, linear, 0.0, 1.0), t)
        for pixel in pixels:
            pixel.reset()
            side = (pixel.t * 3) % 1
            side = int(side + window)
            pixel.h = (
                (side * 0.5)
                + (0.5 * int(t / 6))
                + self.blend(t)
                + self.flux(t)
            ) % 1
            pixel.l = 0.0 if side == 0 else -1.0
            self.sparkle_pixel(pixel, [blank, whiten][side])

    def fall_to_streamers(self, t, pixels):
        sparkle_chance = getv(tween(6, linear, 0.25, 0.0), t)
        self.update_sparkles(t, pixels, sparkle_chance)
        self.update_streamers(t, self.hue_streamers, False)
        self.update_streamers(t, self.inv_streamers, True, update=True)
        for pixel in pixels:
            pixel.reset()
            blend = self.blend(t)
            self.sparkle_pixel(pixel, whiten)
            self.streamer_pixel(pixel, self.hue_streamers, justhue(blend))
            self.streamer_pixel(pixel, self.inv_streamers, invertwhite(blend))

    def fall_to_glass(self, t, pixels):
        pass

    def streamers(self, t, pixels):
        self.update_streamers(t, self.hue_streamers, False)
        self.update_streamers(t, self.inv_streamers, True, update=True)
        for pixel in pixels:
            pixel.reset()
            blend = self.blend(t)
            self.streamer_pixel(pixel, self.hue_streamers, justhue(blend))
            self.streamer_pixel(pixel, self.inv_streamers, invertwhite(blend))

    def streamers_to_slider(self, t, pixels):
        pass
    
    def streamers_to_fall(self, t, pixels):
        sparkle_chance = getv(tween(6, linear, 0.0, 0.25), t)
        self.update_sparkles(t, pixels, sparkle_chance)
        self.update_streamers(t, self.hue_streamers, False, make_new=False)
        self.update_streamers(t, self.inv_streamers, True, make_new=False, update=True)
        for pixel in pixels:
            pixel.reset()
            blend = self.blend(t)
            self.sparkle_pixel(pixel, whiten)
            self.streamer_pixel(pixel, self.hue_streamers, justhue(blend))
            self.streamer_pixel(pixel, self.inv_streamers, invertwhite(blend))
    
    def streamers_to_glass(self, t, pixels):
        width = getv(curve([
            tween(3, linear, 0.1, 1),
            tween(3, linear, 1, 1)
        ]), t)
        self.update_streamers(t, self.hue_streamers, False, width=width)
        self.update_streamers(t, self.inv_streamers, True, make_new=False, update=True)
        for pixel in pixels:
            pixel.reset()
            blend = self.blend(t)
            self.streamer_pixel(pixel, self.hue_streamers, justhue(blend))
            self.streamer_pixel(pixel, self.inv_streamers, invertwhite(blend))

    def glass(self, t, pixels):
        # inv streamers are white, we don't render base
        self.update_streamers(t, self.hue_streamers, False, make_new=False)
        self.update_streamers(t, self.inv_streamers, True, update=True)
        spread = getv(curve([
            tween(3, easeInOutSine, 0, 1/3, True),
            tween(3, easeInOutSine, 0, -1/3, True),
        ]), t)
        spiral = 2 if int(t / 6) % 2 == 0 else -2

        for pixel in pixels:
            pixel.reset()
            pixel_t = effects.bounce(2)(pixel.t) % 1
            pixel_t = (pixel_t + (pixel.y * spiral)) % 1
            pixel.h = (
                (pixel_t * spread)
              + self.blend(t)
              + self.flux(t)
            ) % 1
            pixel.l = 0.0
            self.streamer_pixel(pixel, self.inv_streamers, whiten)

    def glass_to_slider(self, t, pixels):
        sparkle_chance = getv(tween(6, linear, 0.0, 0.25), t)
        self.update_sparkles(t, pixels, sparkle_chance)
        self.update_streamers(t, self.hue_streamers, False, make_new=False)
        self.update_streamers(t, self.inv_streamers, True, make_new=False, update=True)
        spread = getv(curve([
            tween(3, easeInOutSine, 0, 1/3, True),
            tween(3, easeInOutSine, 0, -1/3, True),
        ]), t)
        spiral = 2 if int(t / 6) % 2 == 0 else -2
        for pixel in pixels:
            pixel.reset()
            pixel_t = effects.bounce(2)(pixel.t) % 1
            pixel_t = (pixel_t + (pixel.y * spiral)) % 1
            pixel.h = (
                (pixel_t * spread)
              + self.blend(t)
              + self.flux(t)
            ) % 1
            pixel.l = 0.0
            self.sparkle_pixel(pixel, whiten)
            self.streamer_pixel(pixel, self.inv_streamers, whiten)

    def glass_to_fall(self, t, pixels):
        pass

    def glass_to_streamers(self, t, pixels):
        self.update_streamers(t, self.hue_streamers, False, make_new=False)
        self.update_streamers(t, self.inv_streamers, True, make_new=False, update=True)
        spread = getv(curve([
            tween(3, easeInOutSine, 0, 1/3, True),
            tween(3, easeInOutSine, 0, -1/3, True),
        ]), t)
        spiral = 2 if int(t / 6) % 2 == 0 else -2
        fade = getv(tween(6, linear, 0, -1), t)

        for pixel in pixels:
            pixel.reset()
            pixel_t = effects.bounce(2)(pixel.t) % 1
            pixel_t = (pixel_t + (pixel.y * spiral)) % 1
            pixel.h = (
                (pixel_t * spread)
              + self.blend(t)
              + self.flux(t)
            ) % 1
            pixel.l = fade
            self.streamer_pixel(pixel, self.inv_streamers, whiten)

    def render(self, t, pixels):
        s = t % 264

        if s < 60:
            self.slider(t, pixels)
        elif s < 66:
            self.offset += 6
            self.slider_to_glass(t, pixels)
        elif s < 126:
            self.glass(t, pixels)
        elif s < 132:
            self.offset += 6
            self.glass_to_streamers(t, pixels)
        elif s < 192:
            self.streamers(t, pixels)
        elif s < 198:
            self.offset += 6
            self.streamers_to_fall(t, pixels)
        elif s < 258:
            self.fall(t, pixels)
        elif s < 264:
            self.offset += 6
            self.fall_to_slider(t, pixels)

        self.last_update = t


def evolver(lights):
    x = Evolver()
    return Animation(
        lights=lights,
        effects=[x],
    )

    
def animate(animation):
    start = time.time()
    animation.init(start)
    for interface in animation.lights.interfaces:
        interface.set_mode("rt")
    
    next_frame = time.time() + (1 / 16)
    while True:
        frame_start = time.time()
        t = time.time() - start
        animation.render(t)
        while time.time() < next_frame:
            pass

        next_frame += 1 / 16


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


lights = Lights()
modes = [
    color_fall,
    stained_glass,
    slider,
    dancing_tree,
    crossing_streamers,
    rainbow_spirals,
]

# playlist(60, [f(lights) for f in modes])
animate(evolver(lights))
