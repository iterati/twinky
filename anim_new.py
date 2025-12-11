from pytweening import (
    linear,
    easeInOutSine,
    easeInOutCubic,
)
import random
import time

from core import (
    Lights,
    Animation,
)


DEBUG = False
PAUSE_CHANGE = True
TEST_PATTERN = -1

FROM_BOT = 0
FROM_TOP = 1
CLOCKWISE = 0
COUNTERCLOCKWISE = 1

def getv(v, t):
    return v(t) if callable(v) else v

def getminv(v):
    return v.minv if isinstance(v, curve) else v

def getmaxv(v):
    return v.maxv if isinstance(v, curve) else v


def const(v):
    return 0


class curve:
    def __init__(self, shape, control_points):
        self.shape = shape
        self.control_points = control_points

    @property
    def length(self):
        return self.control_points[-1][0]

    @property
    def minv(self):
        return self.control_points[0][1]
        
    @property
    def maxv(self):
        return self.control_points[-1][1]
        
    def __call__(self, t):
        s = t % self.length
        bottom = None
        for i, [start, _] in enumerate(self.control_points):
            if start <= s:
                bottom = i

        if bottom is None:
            raise ValueError("Couldn't find bottom")

        top = bottom + 1
        start_t, start_v = self.control_points[bottom]
        end_t, end_v = self.control_points[top]

        ss = (s - start_t) / (end_t - start_t)
        return (self.shape(ss) * (end_v - start_v)) + start_v

def rand(minv=0.0, maxv=1.0):
    def func(t):
        s = random.random()
        return (s * (maxv - minv)) + minv

    return func

def choice(choices):
    def func(t):
        return random.choice(choices)

    return func

def sequential(timer, choices):
    def func(t):
        return choices[int(t / timer) % len(choices)]

    return  func

def mirror(m=1):
    def func(t, pixel_t):
        r = (pixel_t * getv(m, t)) % 1
        r *= 2
        if r > 1.0:
            r = 2.0 - r
        return r
        
    return func

def repeat(n=2):
    def func(t, pixel_t):
        return (pixel_t * getv(n, t)) % 1

    return func

def window(w=0.5):
    def func(t, pixel_t):
        return int(pixel_t + getv(w, t)) % 2

    return func

def ncolors(n=2):
    def func(t, pixel_t):
        return int(pixel_t * getv(n, t)) / n

    return func


class Streamer:
    def __init__(self,
                 initial_t,
                 move_dir=FROM_TOP,
                 spin_dir=CLOCKWISE,
                 spin=1.0,
                 length=1.0,
                 width=0.1,
                 lifetime=6.0):
        self.initial_t = initial_t
        self.reverse = move_dir != FROM_TOP

        if move_dir == FROM_TOP:
            spin_dir = -1 if spin_dir == CLOCKWISE else 1
        else:
            spin_dir = 1 if spin_dir == CLOCKWISE else -1

        self.angle = random.random()
        self.spin = spin_dir * getv(spin, initial_t)
        self.length = getv(length, initial_t)
        self.width = getv(width, initial_t)
        self.lifetime = getv(lifetime, initial_t)

        if self.reverse:
            self.y_func = curve(linear, [(0, -self.length), (self.lifetime, 1)])
        else:
            self.y_func = curve(linear, [(0, 1), (self.lifetime, -self.length)])

    def alive(self, t):
        return t <= self.initial_t + self.lifetime

    def contains(self, t, pixel):
        miny = self.y_func(t - self.initial_t)
        maxy = miny + self.length
        mino = (((pixel.y * self.spin) + self.angle) % 1) + 1
        maxo = mino + self.width
        return (miny <= pixel.y <= maxy) and (mino <= pixel.t + 1 <= maxo)

    
def whiten(pixel):
    pixel.w = 0.5
    pixel.s = 0.0
    pixel.l = 0.0


class Blender(Animation):
    sparkle_delay = 0.25
    streamer_delay = 3.0

    def __init__(self, lights, patterns):
        super(Blender, self).__init__(lights, None)
        self.patterns = patterns

    def init(self, t):
        for interface in self.lights.interfaces:
            interface.set_mode("rt")
    
        self.pattern_start = t
        if DEBUG:
            self.curr_pattern = self.patterns[TEST_PATTERN]
        else:
            self.curr_pattern = random.choice(self.patterns)
        self.next_pattern = random.choice([p for p in self.patterns if p["name"] != self.curr_pattern["name"]])
        self.pattern = self.curr_pattern
        self.pattern_end = t + 60.0
        self.transitioning = False
        # self.pattern = self.merge_patterns()
        # self.pattern_end = t + 6.0
        # self.transitioning = True
        self.pattern_hue = 0
        self.next_sparkle = t
        self.next_streamer = t
        self.sparkles = []
        self.streamers = {
            "base": [],
            "invert": [],
        }
        self.last_frame_time = t
        print(self.pattern["name"])

    def merge_patterns(self):
        def mk_curve(attr):
            return curve(easeInOutSine, [
                (0, getmaxv(self.curr_pattern.get(attr, 0.0))),
                (6, getminv(self.next_pattern.get(attr, 0.0)))
            ])

        curr_streamers = self.curr_pattern.get("streamers", {})
        next_streamers = self.next_pattern.get("streamers", {})
        def mk_streamer_curve(type, attr):
            return curve(easeInOutSine, [
                (0, getmaxv(curr_streamers[type].get(attr, 0.0))),
                (6, getmaxv(next_streamers[type].get(attr, 0.0))),
            ])

        streamers = {}
        for streamer_type in ["base", "invert"]:
            if streamer_type in curr_streamers and streamer_type in next_streamers:
                streamers[streamer_type] = {
                    "spin": mk_streamer_curve(streamer_type, "spin"),
                    "length": mk_streamer_curve(streamer_type, "length"),
                    "width": mk_streamer_curve(streamer_type, "width"),
                    "lifetime": mk_streamer_curve(streamer_type, "lifetime"),
                    "emits": next_streamers[streamer_type].get("emits", []),
                }
            elif streamer_type in next_streamers:
                streamers[streamer_type] = next_streamers[streamer_type]                

        return {
            "name": f"{self.curr_pattern['name']}->{self.next_pattern['name']}",
            "topology": {"type": "merging"},
            "base_color": {"type": "merging"},
            "flitter": mk_curve("flitter"),
            "flux": mk_curve("flitter"),
            "sparkles": mk_curve("sparkles"),
            "spin": mk_curve("spin"),
            "spiral": mk_curve("spiral"),
            "spread": mk_curve("spread"),
            "streamers": streamers,
        } 

    def render(self, t):
        if t >= self.pattern_end and not (DEBUG and PAUSE_CHANGE):
            self.pattern_start = t
            if not self.transitioning:
                self.pattern_hue = curve(linear, [(0, 0), (60, 1)])(t)
                self.transitioning = True
                self.pattern_end = t + 6.0
                self.pattern = self.merge_patterns()
            else:
                self.transitioning = False
                self.pattern_end = t + 60.0
                self.curr_pattern = self.next_pattern
                self.next_pattern = random.choice([p for p in self.patterns if p["name"] != self.curr_pattern["name"]])
                self.pattern = self.curr_pattern

            print(self.pattern["name"])

        self.render_frame(t)

    def _handle_topology(self, pattern, pixel_t, t):
        topology = pattern.get("topology", {})
        pxt = pixel_t
        if topology.get("type") == "mirror":
            mirror_fn = mirror(topology["value"])
            return mirror_fn(t - self.pattern_start, pxt)
        elif topology.get("type") == "repeat":
            repeat_fn = repeat(topology["value"])
            return repeat_fn(t - self.pattern_start, pxt)

        return pxt

    def render_frame(self, t):
        # same regardless of the pattern
        base_hue = curve(linear, [(0, 0), (60, 1)])(t)

        if t >= self.next_sparkle:
            if "sparkles" in self.pattern:
                sparkle_chance_fn = self.pattern["sparkles"]
                sparkle_chance = getv(sparkle_chance_fn, t - self.pattern_start)
                self.sparkles = random.choices(
                    range(len(self.pixels)),
                    k=int(len(self.pixels) * sparkle_chance),
                )
            self.next_sparkle = self.next_sparkle + self.sparkle_delay

        if t >= self.next_streamer:
            for streamer_type in ["base", "invert"]:
                if streamer_type in self.pattern.get("streamers", {}):
                    streamer_def = self.pattern["streamers"][streamer_type]
                    emits = getv(streamer_def["emits"], t - self.pattern_start)
                    self.streamers[streamer_type].extend([Streamer(
                        t,
                        move_dir,
                        spin_dir,
                        streamer_def["spin"],
                        streamer_def["length"],
                        streamer_def["width"],
                        streamer_def["lifetime"],
                    ) for spin_dir, move_dir in emits])
                        
            self.next_streamer = self.next_streamer + self.streamer_delay

        new_streamers = {}
        for streamer_type in ["base", "invert"]:
            active = []
            for streamer in self.streamers[streamer_type]:
                if streamer.alive(t):
                    active.append(streamer)
            
            new_streamers[streamer_type] = active

        self.streamers = new_streamers

        flitter_v = getv(self.pattern.get("flitter", 0.0), t - self.pattern_start)
        flitter_fn = rand(1.0 - flitter_v, 1.0)
        flux_v = getv(self.pattern.get("flux", 0.0), t - self.pattern_start)
        flux_fn = rand(-flux_v / 2, flux_v / 2)
        spin = getv(self.pattern.get("spin", 0.0), t - self.pattern_start)
        spiral = getv(self.pattern.get("spiral", 0.0), t - self.pattern_start)
        spread = getv(self.pattern.get("spread", 0.0), t - self.pattern_start)

        for pixel in self.pixels:
            suppress_rx = False
            # if spin = 1, we add 6 degrees (1/60) to t every second
            pixel.t += (1/60) * (t - self.last_frame_time) * spin
            pixel_t = pixel.t + (spiral * pixel.y) % 1
            if self.pattern.get("topology", {}).get("type") == "merging":
                spread = spread * getv(curve(easeInOutSine, [
                    (0, 1),
                    (3, 0),
                    (6, 1),
                ]), t - self.pattern_start)
                if (t - self.pattern_start) <= 3.0:
                    pixel_t = self._handle_topology(self.curr_pattern, pixel_t, t)
                else:
                    pixel_t = self._handle_topology(self.next_pattern, pixel_t, t)
            else:
                pixel_t = self._handle_topology(self.pattern, pixel_t, t)
                
            # handle base_color
            def handle_color(pattern, pxt, merge=None):
                base_color = pattern.get("base_color", {})
                color_type = base_color.get("type")
                if color_type == "window":
                    window_v =base_color["value"]
                    window_fn = window(window_v)
                    iteration = 0
                    if callable(window_v):
                        iteration = int((t - self.pattern_start) / window_v.length)

                    pxt = window_fn(t - self.pattern_start, pxt)
                    if merge == "in":
                        pass
                    elif merge == "out":
                        pass
                    else:
                        return (
                            base_hue
                          + (pxt * spread)
                          + (iteration * spread)
                        ), 0.0, False
                elif color_type == "door":
                    door_v = base_color["value"]
                    door_fn = window(door_v)
                    flip = base_color.get("flip", False)
                    side = door_fn(t - self.pattern_start, pxt)
                    target = 0
                    if callable(door_v) and flip:
                        target = int((t - self.pattern_start) / door_v.length) % 2

                    if side == target:
                        return base_hue, 0.0, True
                    else:
                        return 0, -1.0, False
                elif color_type == "ncolors":
                    ncolor_v = getv(base_color["value"], t - self.pattern_start)
                    ncolor_fn = ncolors(ncolor_v)
                    pxt = ncolor_fn(t - self.pattern_start, pxt)
                    return base_hue + (pxt * ncolor_v * spread), 0.0, False
                elif color_type == "falling":
                    pixel_y = (
                        pixel.y
                      + getv(curve(linear, [(0, 0), (60, 8)]), t - self.pattern_start)
                    )
                    return (
                        self.pattern_hue + (((int(pixel_y) * 3) % 8) / 8),
                        curve(easeInOutCubic, [(0, -1), (0.5, 0), (1, -1)])(pixel_y),
                        False
                    )
                elif color_type == "base":
                    return (base_hue + (spread * pxt), 0.0, False)
                else:
                    return (base_hue + (spread * pxt), -1.0, False)

            pattern_color_type = self.pattern.get("base_color", {}).get("type")
            if pattern_color_type == "merging":
                curr_h, curr_l, curr_ss = handle_color(self.curr_pattern, pixel_t)
                next_h, next_l, next_ss = handle_color(self.next_pattern, pixel_t)
                pixel.h = getv(curve(easeInOutSine, [(0, curr_h), (6, next_h)]), t - self.pattern_start)
                pixel.l = getv(curve(easeInOutSine, [(0, curr_l), (6, next_l)]), t - self.pattern_start)
                suppress_fx = curr_ss or next_ss
                # overrides
                if self.curr_pattern.get("base_color", {}).get("type") == "door" and curr_l == -1.0:
                    pixel.h, pixel.l = next_h, next_l
                elif self.next_pattern.get("base_color", {}).get("type") == "door" and next_l == -1.0:
                    pixel.h, pixel.l = curr_h, curr_l
            else:
                pixel.h, pixel.l, suppress_fx = handle_color(self.pattern, pixel_t)
                    
            # finish color
            pixel.w = 0
            pixel.h += flux_fn(t - self.pattern_start)
            pixel.s = flitter_fn(t - self.pattern_start)

            # run streamers and sparkles
            if not suppress_fx:
                for streamer in self.streamers["invert"]:
                    if streamer.contains(t, pixel):
                        pixel.h += 0.5
                        pixel.l = 0.0
                        
                for streamer in self.streamers["base"]:
                    if streamer.contains(t, pixel):
                        if pixel.l != -1.0:
                            whiten(pixel)
                        else:
                            pixel.l = 0.0

                idx = pixel.idx + (400 * pixel.strand)
                if idx in self.sparkles:
                    whiten(pixel)

        self.last_frame_time = t
        self.write()

    def animate(self):
        start_time = time.time()
        self.init(start_time)
        next_frame = start_time + 1/16
        while True:
            self.render(time.time())
            while time.time() < next_frame:
                pass

            next_frame += 1/16

def random_emits(choices=None):
    if choices is None:
        choices = [
            (FROM_BOT, CLOCKWISE),
            (FROM_BOT, COUNTERCLOCKWISE),
            (FROM_TOP, CLOCKWISE),
            (FROM_TOP, COUNTERCLOCKWISE),
        ]
    def func(t):
        return random.choices(
            choices,
            k=random.randint(1, len(choices))
        )

    return func

def serial_emits(choices=None, delay=3):
    if choices is None:
        choices = [
            [(FROM_BOT, CLOCKWISE), (FROM_BOT, COUNTERCLOCKWISE)],
            [(FROM_TOP, CLOCKWISE), (FROM_TOP, COUNTERCLOCKWISE)],
        ]
    def func(t):
        return choices[int(t / delay) % len(choices)]

    return func


patterns = [
    {
        "name": "Sliding Door",
        "base_color": {
            "type": "door",
            "value": curve(easeInOutSine, [(0, 0), (6, 1), (12, 0)]),
        },
        "topology": {
            "type": "mirror",
            "value": curve(const, [(0, 4), (12, 3), (24, 6), (36, 2), (48, 5), (60, 4)]),
        },
        "flux": 1/16,
        "spread": curve(easeInOutSine, [(0, 0.5), (15, -0.5), (30, 0.5)]),
        "sparkles": 0.5,
        "streamers": {
            "invert": {
                "spin": curve(const, [(0, 1), (6, 0.5), (12, 1)]),
                "length": 1.0,
                "width": curve(const, [(0, 0.1), (6, 0.15), (12, 0.1)]),
                "lifetime": 6.0,
                "emits": serial_emits(),
            },
        },
    },
    {
        "name": "Crossing Streamers",
        "sparkles": 0.25,
        "streamers": {
            "base": {
                "spin": curve(const, [(0, 1), (6, 0.5), (12, 1)]),
                "length": 1.0,
                "width": curve(const, [(0, 0.1), (6, 0.15), (12, 0.1)]),
                "lifetime": 6.0,
                "emits": serial_emits(),
            },
            "invert": {
                "spin": curve(const, [(0, 1), (6, 0.5), (12, 1)]),
                "length": 1.0,
                "width": curve(const, [(0, 0.1), (6, 0.15), (12, 0.1)]),
                "lifetime": 6.0,
                "emits": serial_emits(),
            },
        },
    },
    {
        "name": "Falling Snow",
        "base_color": {
            "type": "falling",
        },
        "flitter": 0.25,
        "flux": 1/8,
        "sparkles": curve(easeInOutSine, [(0, 0.25), (6, 0.5), (12, 0.25)]),
        "streamers": {
            "base": {
                "spin": 1.0,
                "length": 1.0,
                "width": 0.1,
                "lifetime": 6.0,
                "emits": random_emits(),
            },
        },
    },
    {
        "name": "Spiral Top",
        "base_color": {
            "type": "window",
            "value": curve(linear, [(0, 0), (6, 1)]),
        },
        "topology": {
            "type": "mirror",
            "value": 3,
        },
        "flux": 1/16,
        "spin": curve(easeInOutSine, [(0, 0), (15, 3), (30, 0), (45, -3), (60, 0)]),
        "spiral": curve(linear, [(0, 0), (15, 2), (45, -2), (60, 0)]),
        "spread": 1/3,
        "sparkles": 0.15,
    },
    {
        "name": "Twisted Rainbows",
        "base_color": {
            "type": "ncolors",
            "value": 3,
        },
        "topology": {
            "type": "repeat",
            "value": curve(const, [
                (0, 1),
                (12, 3),
                (24, 5),
                (36, 4),
                (48, 2),
                (60, 1)
            ]),
        },
        "spin": 2.0,
        "spread": curve(easeInOutCubic, [(0, 1/4), (3, 0), (6, -1/4), (9, 0), (12, 1/4)]),
        "spiral": curve(const, [
            (0, -3), (3, 3),
            (9, -1.5), (15, 1.5),
            (21, -0.5), (27, 0.5),
            (33, -1), (39, 1),
            (45, -2), (51, 2),
            (57, -3), (60, -3)
        ]),
        "streamers": {
            "base": {
                "spin": 2.0,
                "length": 1.0,
                "width": 0.25,
                "lifetime": 3.0,
                "emits": random_emits(),
            },
        },
    },
    {
        "name": "Rainbro",
        "base_color": {
            "type": "base",
        },
        "topology": {
            "type": "repeat",
            "value": curve(const, [
                (0, 6),
                (7.5, 8),
                (22.5, 4),
                (37.5, 2),
                (52.5, 3),
                (60, 6),
            ]),
        },
        "flitter": 0.1,
        "flux": 1/16,
        "spin": 6,
        "spiral": curve(easeInOutSine, [(0, -2), (7.5, 2), (15, -2)]),
        "spread": curve(easeInOutSine, [(0, 1), (15, -1), (30, 1)]),
    }
]

lights = Lights()
animation = Blender(lights, patterns)
animation.animate()
