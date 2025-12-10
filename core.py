import io
import math
import struct
from xled.discover import xdiscover
from xled.control import ControlInterface
from xled_plus.ledcolor import (
    hsl_color,
    set_color_style,
)

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

    def write(self):
        for interface, buffer, pixels in zip(self.lights.interfaces, self.buffers, self.light_pixels):
            buffer.seek(0)
            for pixel in pixels:
                buffer.write(pixel.as_byte())
                
            interface._udpclient = self.lights.udpclient
            interface.udpclient.destination_host = interface.host
            buffer.seek(0)
            interface.set_rt_frame_socket(buffer, 3)

    def render(self, t):
        for effect in self.effects:
            effect.render(t, self.pixels)
        
        self.write()


set_color_style('8col')
# set_color_style('linear')
