from pytweening import (
    linear,
    easeInSine,
    easeOutSine,
    easeInOutSine,
    easeOutBounce,
    easeInOutBounce,
    easeInOutCubic,
)
import random
import time

from core import (
    Lights,
    Animation,
)


DEBUG = False
# DEBUG = True
CHANGE = "none"
# CHANGE = "transition"
CURR_PATTERN = -2
NEXT_PATTERN = 1

FROM_BOT = 0
FROM_TOP = 1
CLOCKWISE = 0
COUNTERCLOCKWISE = 1

def getv(v, t):
    return v(t) if callable(v) else v

def const(v):
    return 0

class curve:
    def __init__(self, shape, control_points):
        self.shape = shape
        self.control_points = control_points

    @property
    def length(self):
        return self.control_points[-1][0]

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

    def __repr__(self):
        return f"{self.shape}: {self.control_points}"

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

def ncolors(n=2, norm=True):
    def func(t, pixel_t):
        r = int(pixel_t * getv(n, t))
        return r / n if norm else r

    return func


class Streamer:
    def __init__(self,
                 initial_t,
                 move_dir=FROM_TOP,
                 spin_dir=CLOCKWISE,
                 angle=None,
                 spin=1.0,
                 length=1.0,
                 width=0.1,
                 lifetime=6.0,
                 func=None):
        self.initial_t = initial_t
        self.reverse = move_dir != FROM_TOP

        if move_dir == FROM_TOP:
            spin_dir = -1 if spin_dir == CLOCKWISE else 1
        else:
            spin_dir = 1 if spin_dir == CLOCKWISE else -1

        self.angle = random.random() if angle is None else angle
        self.spin = spin_dir * getv(spin, initial_t)
        self.length = getv(length, initial_t)
        self.width = getv(width, initial_t)
        self.lifetime = getv(lifetime, initial_t)
        self.func = func

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

    def __repr__(self):
        return f"{self.angle},{self.spin},{self.length},{self.width},{self.lifetime}"

    
def whiten(pixel):
    pixel.w = 0.75
    pixel.s = 0.0
    pixel.l = -0.75


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
        self.pattern_end = t + 60.0
        if DEBUG:
            self.curr_pattern = self.patterns[CURR_PATTERN]
            self.next_pattern = self.patterns[NEXT_PATTERN]
            if CHANGE == "transition":
                self.pattern_start = t - 54.0
                self.pattern_end = t + 6.0
        else:
            self.curr_pattern = random.choice(self.patterns)
            self.next_pattern = random.choice([p for p in self.patterns if p["name"] != self.curr_pattern["name"]])
            self.pattern_start = t
            self.pattern_end = t + 60.0

        self.pattern = self.curr_pattern

        self.transitioning = False
        self.pattern_hue = 0
        self.next_sparkle = t
        self.next_streamer = t
        self.sparkles = []
        self.streamers = []
        self.last_frame_time = t
        print(self.pattern["name"])

    def merge_patterns(self):
        def mk_curve(attr):
            return curve(easeInOutSine, [
                (0, getv(self.curr_pattern.get(attr, 0.0), 60)),
                (6, getv(self.next_pattern.get(attr, 0.0), 0))
            ])

        return {
            "name": f"{self.curr_pattern['name']}->{self.next_pattern['name']}",
            "topology": {"type": "merging"},
            "base_color": {"type": "merging"},
            "flash": mk_curve("flash"),
            "flicker": mk_curve("flicker"),
            "flitter": mk_curve("flitter"),
            "flux": mk_curve("flux"),
            "sparkles": mk_curve("sparkles"),
            "spin": mk_curve("spin"),
            "spiral": mk_curve("spiral"),
            "spread": mk_curve("spread"),
            "streamers": self.next_pattern.get("streamers", {}).copy(),
        } 

    def render(self, t):
        if t >= self.pattern_end and not (DEBUG and CHANGE == "none"):
            if not self.transitioning:
                self.pattern = self.merge_patterns()
                self.pattern_hue = curve(linear, [(0, 0), (60, 1)])(t)
                self.transitioning = True
                self.pattern_end = t + 6.0
            else:
                self.transitioning = False
                self.pattern_end = t + 60.0
                self.curr_pattern = self.next_pattern
                self.next_pattern = random.choice([p for p in self.patterns if p["name"] != self.curr_pattern["name"]])
                self.pattern = self.curr_pattern

            self.pattern_start = t
            print(self.pattern["name"])

        self.triggered = False
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
            streamer_f = self.pattern.get("streamers", [])
            streamer_defs = getv(streamer_f, t - self.pattern_start)
            self.streamers.extend([
                Streamer(t, **streamer_def)
                for streamer_def in streamer_defs
            ])
            self.next_streamer = self.next_streamer + self.streamer_delay

        new_streamers = []
        for streamer in self.streamers:
            if streamer.alive(t):
                new_streamers.append(streamer)

        self.streamers = new_streamers

        flash_v = getv(self.pattern.get("flash", 0.0), t - self.pattern_start)
        flash_fn = rand(0.0, flash_v)
        flicker_v = getv(self.pattern.get("flicker", 0.0), t - self.pattern_start)
        flicker_fn = rand(0.0 - flicker_v, 0.0)
        flitter_v = getv(self.pattern.get("flitter", 0.0), t - self.pattern_start)
        flitter_fn = rand(1.0 - flitter_v, 1.0)
        flux_v = getv(self.pattern.get("flux", 0.0), t - self.pattern_start)
        flux_fn = rand(-flux_v / 2, flux_v / 2)
        spin = getv(self.pattern.get("spin", 0.0), t - self.pattern_start)
        spiral = getv(self.pattern.get("spiral", 0.0), t - self.pattern_start)
        spread = getv(self.pattern.get("spread", 0.0), t - self.pattern_start)

        for pixel in self.pixels:
            suppress_fx = []
            # if spin = 1, we add 6 degrees (1/60) to t every second
            pixel.t = (pixel.t + ((1/60) * (t - self.last_frame_time) * spin)) % 1
            pixel_t = pixel._t + (spiral * pixel.y) % 1
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
                            0,
                            base_hue + (pxt * spread) + (iteration * spread),
                            1,
                            0,
                            []
                        )
                elif color_type == "door":
                    door_v = base_color["value"]
                    door_fn = window(door_v)
                    flip = base_color.get("flip", False)
                    side = door_fn(t - self.pattern_start, pxt)
                    target = 0
                    if callable(door_v) and flip:
                        target = int((t - self.pattern_start) / door_v.length) % 2

                    if side == target:
                        return (0, base_hue, 1, 0, ["streamers", "sparkles"])
                    else:
                        return (0, base_hue, 1, -1, [])
                elif color_type == "ncolors":
                    ncolor_v = getv(base_color["value"], t - self.pattern_start)
                    ncolor_fn = ncolors(ncolor_v)
                    pxt = ncolor_fn(t - self.pattern_start, pxt)
                    return (0, base_hue + (pxt * ncolor_v * spread), 1, 0, [])
                elif color_type == "panels":
                    panel_v = getv(base_color["value"], t - self.pattern_start)
                    panel_fn = ncolors(panel_v, False)
                    side = panel_fn(t - self.pattern_start, pxt)
                    funcs = getv(base_color["funcs"], t - self.pattern_start)
                    func = funcs[side % panel_v]
                    return func(t - self.pattern_start, pxt, base_hue, spread)
                elif color_type == "falling":
                    pixel_y = (
                        pixel.y
                      + getv(curve(linear, [(0, 0), (60, 8)]), t - self.pattern_start)
                    )
                    return (
                        0,
                        self.pattern_hue + (((int(pixel_y) * 3) % 8) / 8),
                        1,
                        curve(easeInOutCubic, [(0, -1), (0.5, 0), (1, -1)])(pixel_y),
                        []
                    )
                elif color_type == "base":
                    return (0, base_hue + (spread * pxt), 1, 0, [])
                else:
                    return (0, base_hue + (spread * pxt), 1, -1, [])

            pattern_color_type = self.pattern.get("base_color", {}).get("type")
            if pattern_color_type == "merging":
                curr_w, curr_h, curr_s, curr_l, curr_ss = handle_color(self.curr_pattern, pixel_t) 
                next_w, next_h, next_s, next_l, next_ss = handle_color(self.next_pattern, pixel_t) 
                pixel.w = getv(curve(easeInOutSine, [(0, curr_w), (6, next_w)]), t - self.pattern_start)
                pixel.h = getv(curve(easeInOutSine, [(0, curr_h), (6, next_h)]), t - self.pattern_start)
                pixel.s = getv(curve(easeInOutSine, [(0, curr_s), (6, next_s)]), t - self.pattern_start)
                pixel.l = getv(curve(easeInOutSine, [(0, curr_l), (6, next_l)]), t - self.pattern_start)
                suppress_fx = curr_ss + next_ss
                # overrides
                if self.curr_pattern.get("base_color", {}).get("type") == "door" and curr_l == -1.0:
                    pixel.w, pixel.h, pixel.s, pixel.l = next_w, next_h, next_s, next_l
                elif self.next_pattern.get("base_color", {}).get("type") == "door" and next_l == -1.0:
                    pixel.w, pixel.h, pixel.s, pixel.l = curr_w, curr_h, curr_s, curr_l
            else:
                pixel.w, pixel.h, pixel.s, pixel.l, suppress_fx = handle_color(self.pattern, pixel_t)
                    
            # finish color
            if "flicker" not in suppress_fx:
                pixel.w += flicker_fn(t - self.pattern_start)
                
            if "flux" not in suppress_fx:
                pixel.h += flux_fn(t - self.pattern_start)

            if "flitter" not in suppress_fx:
                pixel.s += flitter_fn(t - self.pattern_start)

            if "flash" not in suppress_fx:
                if pixel.l != -1.0:
                    pixel.l += flash_fn(t - self.pattern_start)

            # run streamers and sparkles
            if "streamers" not in suppress_fx:
                for streamer in self.streamers:
                    if streamer.contains(t, pixel):
                        streamer.func(t - self.pattern_start, pixel)

            if "sparkles" not in suppress_fx:
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

def base_streamer(t, pixel):
    if pixel.l != -1.0:
        whiten(pixel)
    else:
        pixel.l = 0.0

def invert_streamer(t, pixel):
    pixel.h += 0.5
    pixel.l = 0.0

def color_streamer(h=0.0):
    def func(t, pixel):
        pixel.h += h
        pixel.l = 0.0

    return func

def random_streamers(func, move_dirs=None, spin_dirs=None, spin_widths=None):
    if move_dirs is None:
        move_dirs = [FROM_BOT, FROM_TOP]

    if spin_dirs is None:
        spin_dirs = [CLOCKWISE, COUNTERCLOCKWISE]

    if spin_widths is None:
        spin_widths = [(0.5, 0.1), (1, 0.15), (1.5, 0.2)]

    choices = [
        {
            "move_dir": move_dir,
            "spin_dir": spin_dir,
            "spin": spin,
            "width": width,
            "length": 1.0,
            "lifetime": 6.0,
            "func": func,
        }
        for move_dir in move_dirs
        for spin_dir in spin_dirs
        for spin, width in spin_widths
    ]
    def func(t):
        return random.choices(
            choices,
            k=random.randint(1, 4)
        )

    return func

def falling_snow_streamers():
    streamers = random_streamers(base_streamer)
    def func(t):
        return streamers(t)

    return func

def confetti_streamers():
    streamers = [
        random_streamers(color_streamer(i/4), move_dirs=[FROM_TOP])
        for i in range(4)
    ] 
    def func(t):
        r = []
        for s in streamers:
            r.extend(s(t))
        return r

    return func

def twisted_rainbows_streamers():
    choices = [
        {
            "move_dir": move_dir,
            "spin_dir": spin_dir,
            "spin": 2.0,
            "length": 2.0,
            "width": 0.25,
            "lifetime": 3,
            "func": base_streamer,
        }
        for move_dir in [FROM_BOT, FROM_TOP]
        for spin_dir in [CLOCKWISE, COUNTERCLOCKWISE]
    ]
    def func(t):
        return random.choices(
            choices,
            k=random.randint(1, 2),
        )

    return func

def sliding_door_streamers(delay=3, reverse=False, func=None):
    choices = [
        [
            {
                "move_dir": move_dir,
                "spin_dir": spin_dir,
                "spin": curve(const, [(0, 1), (6, 0.5), (12, 1)]),
                "length": 1.0,
                "width": curve(const, [(0, 0.1), (6, 0.15), (12, 0.1)]),
                "lifetime": 6.0,
                "func": func,
            }
            for spin_dir in [CLOCKWISE, COUNTERCLOCKWISE]
         ]
        for move_dir in [FROM_BOT, FROM_TOP]
    ]

    if reverse:
        choices.reverse()

    def func(t):
        return choices[int(t / delay) % len(choices)]

    return func

def crossing_streamers():
    bases = sliding_door_streamers(func=base_streamer)
    inverts = sliding_door_streamers(reverse=True, func=invert_streamer)
    def func(t):
        return bases(t) + inverts(t)

    return func

def spiral_streamers(move_dir, offset=0.0, delay=3, lifetime=12.0, func=None):
    if not func:
        raise ValueError("func")

    choices = [
        [
            {
                "move_dir": move_dir,
                "spin_dir": CLOCKWISE if o % 2 == 0 else COUNTERCLOCKWISE,
                "angle": (i/4) + offset + (o/5),
                "spin": 2,
                "length": 1,
                "width": 0.05,
                "lifetime": lifetime,
                "func": func,
            }
            for i in range(4)
         ]
        for o in range(5)
    ]
    def func(t):
        return choices[int(t / delay) % len(choices)]

    return func

def galaxus_streamers():
    bases = spiral_streamers(FROM_BOT, func=base_streamer)
    inverts = spiral_streamers(FROM_TOP, func=invert_streamer)
    def func(t):
        return bases(t) + inverts(t)

    return func

def base(w=0.0, h=0.0, s=1.0, l=0.0, suppress=None):
    if suppress is None:
        suppress = []

    def func(t, pxt, base_hue, spread):
        return (w, base_hue + getv(h, t), s, l, suppress)

    return func

def circus_tent_funcs(delay=6):
    choices = [
        [
            base(h=0.25, suppress=["sparkles"]),
            base(l=-1),
            base(l=-1),
            base(h=0.75, suppress=["sparkles"]),
        ],
        [
            base(l=-1),
            base(h=0.0, suppress=["sparkles"]),
            base(h=0.0, suppress=["sparkles"]),
            base(l=-1),
        ],
        [
            base(h=0.75, suppress=["sparkles"]),
            base(l=-1),
            base(l=-1),
            base(h=0.25, suppress=["sparkles"]),
        ],
        [
            base(l=-1),
            base(h=0.0, suppress=["sparkles"]),
            base(h=0.0, suppress=["sparkles"]),
            base(l=-1),
        ],
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
        "streamers": sliding_door_streamers(func=invert_streamer),
    },
    {
        "name": "Crossing Streamers",
        "sparkles": 0.25,
        "streamers": crossing_streamers(),
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
            "base": falling_snow_streamers(),
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
        "streamers": twisted_rainbows_streamers(),
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
    },
    {
        "name": "Galaxus",
        "base_color": {
            "type": "blank",
        },
        "sparkles": 0.25,
        "streamers": galaxus_streamers(),
    },
    {
        "name": "Basic Bitch",
        "base_color": {
            "type": "base",
        },
        "flash": 1.0,
        "flitter": curve(easeInOutSine, [(0, 0.75), (3, 0), (6, 0.75)]),
        "flux": curve(easeInOutSine, [(0, 0), (6, 2/3), (12, 0)]),
    },
    {
        "name": "Spread Eagle",
        "base_color": {
            "type": "base",
        },
        "topology": {
            "type": "mirror",
            "value": 2,
        },
        "spin": 2.0,
        "spiral": curve(const, [(0, 0), (12, 1), (24, -1), (36, 0.5), (48, -0.5), (60, 0)]),
        "spread": curve(easeInSine, [(0, 0), (3, 3/8), (6, 0), (9, -3/8), (12, 0)]),
        "streamers": spiral_streamers(FROM_TOP, lifetime=6.0, func=invert_streamer),
    },
    {
        "name": "Circus Tent",
        "base_color": {
            "type": "panels",
            "value": 4,
            "funcs": circus_tent_funcs(0.5),
        },
        "topology": {
            "type": "mirror",
            "value": 3,
        },
        "sparkles": 0.5,
        "spin": 10,
        "streamers": {
            "base": sliding_door_streamers(func=base_streamer),
        },
    },
    {
        "name": "Coiled Spring",
        "base_color": {
            "type": "panels",
            "value": 4,
            "funcs": [
                base(w=0.75, s=0.0, l=-0.75, suppress=["sparkles", "streamers"]),
                base(h=0.5, l=-1),
                base(h=0.5, l=-1),
                base(h=0.5, l=-1),
            ],
        },
        "topology": {
            "type": "repeat",
            "value": 3,
        },
        "spiral": curve(easeOutBounce, [(0, 2), (15, -2), (30, 2)]),
        "streamers": spiral_streamers(FROM_BOT, func=base_streamer),
    },
    {
        "name": "Confetti",
        "streamers": confetti_streamers(),
        "sparkles": 0.2,
    }
]

lights = Lights()
animation = Blender(lights, patterns)
animation.animate()
