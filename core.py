import io
import math
from pytweening import linear, easeInOutCubic
import random
import time
from typing import Callable, TypeAlias
from xled.discover import xdiscover
from xled.control import ControlInterface

from colors import Color, BaseColor, ColorFuncs
from control import WiredPattern
from param import Param, getv, Curve
from streamer import Streamer, StreamerParam, getv_streamers
from topologies import Topology

import sys
sys.stdout = open('log.txt', 'w')
sys.stderr = open('error.txt', 'w')

def rand(minv=0.0, maxv=1.0) -> Callable[[], float]:
    def func() -> float:
        s = random.random()
        return (s * (maxv - minv)) + minv

    return func


def choice(choices: list[float]) -> Callable[[], float]:
    def func() -> float:
        return random.choice(choices)

    return func


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
        self.color.w = w
 
    @property
    def h(self):
        return self.color.h

    @h.setter
    def h(self, h):
        self.color.h = h
 
    @property
    def s(self):
        return self.color.s

    @s.setter
    def s(self, s):
        self.color.s = s
 
    @property
    def l(self):
        return self.color.l

    @l.setter
    def l(self, l):
        self.color.l = l
 
    def as_byte(self, t=0):
        return self.color.as_byte(t)


class Interface(ControlInterface):
    def __init__(self, device):
        super(Interface, self).__init__(device.ip_address)
        self.device = device
        self.layout = self.get_led_layout()['coordinates']


class Lights:
    def __init__(self):
        dgen = xdiscover()
        devices = [next(dgen), next(dgen)]
        self.interfaces = [Interface(device) for device in devices]
        self.udpclient = self.interfaces[0].udpclient


class Pattern:
    def __init__(self,
                 name: str,
                 base_color: BaseColor | None=None,
                 topologies: list[Topology] | None=None,
                 spread: Param=0,
                 flash: Param=0,
                 flicker: Param=0,
                 flitter: Param=0,
                 flux: Param=0,
                 spiral: Param=0,
                 spin: Param=0,
                 sparkles: Param=0,
                 sparkle_func: Callable[[Color], Color] | None=None,
                 streamers: StreamerParam | None=None):
        self.name = name
        self.base_color = base_color if base_color is not None else BaseColor()
        self.topologies = topologies if topologies is not None else []
        self.spread = spread
        self.flash = flash
        self.flicker = flicker
        self.flitter = flitter
        self.flux = flux
        self.spiral = spiral
        self.spin = spin
        self.sparkles = sparkles
        self.sparkle_func = sparkle_func if sparkle_func is not None else ColorFuncs.WHITEN
        self.streamers = streamers if streamers is not None else []


ControlValue: TypeAlias = float | Curve | StreamerParam | BaseColor | list[Topology]
ControlOption: TypeAlias = tuple[str, ControlValue]
ControlOptions: TypeAlias = list[ControlOption]
Control: TypeAlias = tuple[str, ControlOptions]
Controls: TypeAlias = list[Control]


class ControllablePattern(Pattern):
    controls = []

    def __init__(self, name, **kwargs):
        super(ControllablePattern, self).__init__(name, **kwargs)

        self.set_controls = [0] * len(self.controls)
        self.randomize()
        for idx, option_idx in enumerate(self.set_controls):
            self.set_control_option(idx, option_idx)

    def get_controls(self) -> list[str]:
        return [name for name, _ in self.controls]

    def get_control(self, idx: int) -> Control:
        return self.controls[idx]

    def get_control_options(self, idx: int) -> list[str]:
        _, options = self.get_control(idx)
        return [name for name, _ in options]

    def set_control_option(self, idx: int, option_idx: int):
        try:
            name, options = self.controls[idx]
        except:
            raise Exception(self.controls, idx)
        try:
            _, option = options[option_idx]
        except Exception as ex:
            print(self.name, idx, option_idx, self.controls)
            raise ex
        self.set_controls[idx] = option_idx
        setattr(self, name, option)

    def get_control_option(self, i: int) -> int:
        return self.set_controls[i]

    def update_values(self):
        pass

    def randomize(self):
        for idx, (_, options) in enumerate(self.controls):
            option_idx = random.randint(0, len(options) - 1)
            self.set_control_option(idx, option_idx)


class Blender:
    sparkle_delay = 0.25
    streamer_delay = 1.0
    pattern_length = 60.0
    transition_length = 6.0
    transition_offset = pattern_length - transition_length

    def __init__(self,
                 patterns: list[WiredPattern],
                 start_idx: int | None=None,
                 pause_change: bool=False):
        self.lights = Lights()
        self.patterns = patterns
        self.start_idx = start_idx
        self.pause_change = pause_change
        self._blend_func = Curve(linear, [(0, 0), (66, 1)])
        self.buffers = [io.BytesIO() for _ in self.lights.interfaces]
        self.light_pixels = [
            [Pixel(strand, idx, **p) for idx, p in enumerate(interface.layout)]
            for strand, interface in enumerate(self.lights.interfaces)
        ]
        self.running = False
        self.pattern = self.patterns[
            start_idx
            if start_idx is not None else
            random.randint(0, len(patterns) - 1)
        ]
        self.next_pattern = self._pick_next()
        self.transitioning = False
        self._init_t = 0.0
        self._t = 0.0
        self.pattern_end = self.pattern_length

    @property
    def pixels(self):
        return self.light_pixels[0] + self.light_pixels[1]

    def _pick_next(self):
        choice = random.choice([p for p in self.patterns if p.name != self.pattern.name])
        if isinstance(choice, ControllablePattern):
            choice.randomize()
        return choice

    def init(self, t: float):
        for interface in self.lights.interfaces:
            interface.set_mode("rt")
    
        if self.start_idx is not None:
            self.pattern = self.patterns[self.start_idx]
        else:
            self.pattern = random.choice(self.patterns)
        self.next_pattern = self._pick_next()
        self.pattern.base_color.init(getv(self._blend_func, t))
        self.pattern.randomize()

        self._init_t = t
        self._t = t
        self.transitioning = False
        self.pattern_start = t
        self.pattern_end = t + self.pattern_length
        self.next_sparkle = t
        self.sparkles = []
        self.next_streamer = t
        self.streamers = []
        self.running = True

    def _render(self, t: float, pattern: Pattern) -> list[Color]:
        blend_h = getv(self._blend_func, t)
        spread_h = getv(pattern.spread, t)
        flash_v = getv(pattern.flash, t)
        flash_func = rand(0.0, flash_v)
        flicker_v = getv(pattern.flicker, t)
        flicker_func = rand(0.0, flicker_v)
        flitter_v = getv(pattern.flitter, t)
        flitter_func = rand(0.0, flitter_v)
        flux_v = getv(pattern.flux, t)
        flux_func = rand(-flux_v/2, flux_v/2)

        colors = []
        for pixel in self.pixels:
            pixel_t = (
                pixel.t
              + getv(pattern.spin, t)
              + (getv(pattern.spiral, t) * pixel.y)
            ) % 1

            for topology in pattern.topologies:
                pixel_t = topology(t, pixel_t, pixel.y)

            color, suppress = pattern.base_color(
                t,
                blend_h,
                spread_h,
                pixel_t,
                pixel.y,
            )

            if "flash" not in suppress and pixel.l != -1.0:
                color.l -= flash_func()
            if "flicker" not in suppress:
                color.w += flicker_func()
            if "flitter" not in suppress and pixel.s != 0.0:
                color.s -= flitter_func()
            if "flux" not in suppress:
                color.h += flux_func()

            if "sparkles" not in suppress:
                idx = pixel.idx + (400 * pixel.strand)
                if idx in self.sparkles:
                    color = self.pattern.sparkle_func(color)

            if "streamers" not in suppress:
                for streamer in self.streamers:
                    if streamer.contains(self._t, pixel):
                        color = streamer.func(color, t, pixel.t, pixel.y)

            colors.append(color)

        return colors

    def _render_transition(self, t: float) -> list[Color]:
        # current goes around again from 60/0 -> 6
        curr_colors = self._render(t, self.pattern)
        # next starts early, 54 -> 60/0
        next_colors = self._render(self.transition_offset + t, self.next_pattern)
        colors = []
        for curr_color, next_color in zip(curr_colors, next_colors):
            colors.append(Color(
                getv(Curve(easeInOutCubic, [(0, curr_color.w), (6, next_color.w)]), t),
                getv(Curve(easeInOutCubic, [(0, curr_color.h), (6, next_color.h)]), t),
                getv(Curve(easeInOutCubic, [(0, curr_color.s), (6, next_color.s)]), t),
                getv(Curve(easeInOutCubic, [(0, curr_color.l), (6, next_color.l)]), t),
            ))

        return colors

    @property
    def pattern_name(self):
        if self.transitioning:
            return f"{self.pattern.name}->{self.next_pattern.name}"
        else:
            return self.pattern.name

    @property
    def time_str(self):
        if self.pause_change:
            return f"{round(self._t - self._init_t, 2)}"
        elif self.transitioning:
            return f"{round(self.pattern_end - self._t, 2)}"
        else:
            return f"{round(self.pattern_end - self._t + self.transition_length, 2)}"

    def start_transition(self, next: int | None=None):
        self.pattern_hue = getv(self._blend_func, self._t)
        self.transitioning = True
        self.pattern_end = self._t + self.transition_length
        if next is not None:
            self.next_pattern = self.patterns[next]

    def render(self, t: float):
        self._t = t
        if t >= self.pattern_end and not (self.pause_change and not self.transitioning):
            self.pattern_start = self.pattern_end
            if not self.transitioning:
                self.next_pattern.base_color.init(getv(self._blend_func, self.transition_offset + t))
                self.start_transition()
            else:
                self.transitioning = False
                self.pattern_end = self._t + self.pattern_length
                self.pattern = self.next_pattern
                self.next_pattern = self._pick_next()
                self.pattern.randomize()
            
        if t >= self.next_sparkle:
            self.next_sparkle += self.sparkle_delay
            if self.transitioning:
                sparkle_chance = getv(Curve(linear, [
                    (0, getv(self.pattern.sparkles, self.transition_length)),
                    (6, getv(self.next_pattern.sparkles, self.transition_offset)),
                ]), t - self.pattern_start)
            else:
                sparkle_chance = getv(self.pattern.sparkles, t)

            self.sparkles = random.choices(
                range(len(self.pixels)),
                k=int(len(self.pixels) * sparkle_chance))
                
        if t >= self.next_streamer:
            self.next_streamer += self.streamer_delay
            streamer_defs = getv_streamers(self.pattern.streamers, t - self.pattern_start)
            self.streamers.extend([
                Streamer(t, **streamer_def)
                for streamer_def in streamer_defs
            ])

            new_streamers = []
            for streamer in self.streamers:
                if streamer.alive(t):
                    new_streamers.append(streamer)

            self.streamers = new_streamers
                
        if self.transitioning:
            colors = self._render_transition(t - self.pattern_start) 
        else:
            colors = self._render(t - self.pattern_start, self.pattern)

        return colors

    def write(self, colors):
        colors = [colors[:400], colors[400:]]
        for interface, buffer, colors in zip(self.lights.interfaces, self.buffers, colors):
            buffer.seek(0)
            for color in colors:
                buffer.write(color.as_byte(self._t - self.pattern_start))
            
            interface._udpclient = self.lights.udpclient
            interface.udpclient.destination_host = interface.host
            buffer.seek(0)
            interface.set_rt_frame_socket(buffer, 3)

    def animate(self):
        start_time = time.time()
        self.init(start_time)
        next_frame = start_time + (1/16)
        while self.running:
            colors = self.render(time.time())
            self.write(colors)
            while time.time() < next_frame:
                pass

            next_frame += 1/16
