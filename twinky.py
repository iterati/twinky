import curses

from pytweening import (
    linear,
    easeInSine,
    easeOutSine,
    easeInOutSine,
    easeOutBounce,
    easeInOutBounce,
    easeInOutCubic,
    easeInOutElastic,
)

from colors import (
    BaseColor,
    WindowColor,
    SplitColor,
    FallingColor,
    ColorFuncs,
    periodic_choices,
)
from core import (
    Blender,
    Color,
    ControllablePattern,
    rand,
    choice,
)
from param import (
    Curve,
    CombinedCurve,
    const,
)
from streamer import (
    Direction,
    Spin,
    StreamerFuncs,
    RandomColorStreamerFunc,
    setcolor_streamer,
    streamer_choices,
    combined_choices,
)
from topologies import (
    DistortTopology,
    MirrorTopology,
    RepeatTopology,
    TurntTopology,
)
from ui import get_thread_and_menu


def mk_bounce(period, v):
    return [
        (0, 0),
        (period * 0.25, v),
        (period * 0.5, 0),
        (period * 0.75, -v),
        (period, 0),
    ]


FRACS = [
    ("1/8", 1/8),
    ("1/6", 1/6),
    ("1/5", 1/5),
    ("1/4", 1/4),
    ("1/3", 1/3),
    ("1/2", 1/2),
    ("2/3", 2/3),
    ("3/4", 3/4),
]
SINES = [
    ("1/4:6",  Curve(easeInOutSine, [(0, 0), (3, 1/4), (6, 0)])),
    ("1/3:6",  Curve(easeInOutSine, [(0, 0), (3, 1/3), (6, 0)])),
    ("1/2:6",  Curve(easeInOutSine, [(0, 0), (3, 1/2), (6, 0)])),
    ("2/3:6",  Curve(easeInOutSine, [(0, 0), (3, 2/3), (6, 0)])),
    ("3/4:6",  Curve(easeInOutSine, [(0, 0), (3, 3/4), (6, 0)])),
    (  "1:6",  Curve(easeInOutSine, [(0, 0), (3, 1),   (6, 0)])),
    ("1/4:12", Curve(easeInOutSine, [(0, 0), (6, 1/4), (12, 0)])),
    ("1/3:12", Curve(easeInOutSine, [(0, 0), (6, 1/3), (12, 0)])),
    ("1/2:12", Curve(easeInOutSine, [(0, 0), (6, 1/2), (12, 0)])),
    ("2/3:12", Curve(easeInOutSine, [(0, 0), (6, 2/3), (12, 0)])),
    ("3/4:12", Curve(easeInOutSine, [(0, 0), (6, 3/4), (12, 0)])),
    (  "1:12", Curve(easeInOutSine, [(0, 0), (6, 1),   (12, 0)])),
    ("1/4:30", Curve(easeInOutSine, [(0, 0), (15, 1/4), (30, 0)])),
    ("1/3:30", Curve(easeInOutSine, [(0, 0), (15, 1/3), (30, 0)])),
    ("1/2:30", Curve(easeInOutSine, [(0, 0), (15, 1/2), (30, 0)])),
    ("2/3:30", Curve(easeInOutSine, [(0, 0), (15, 2/3), (30, 0)])),
    ("3/4:30", Curve(easeInOutSine, [(0, 0), (15, 3/4), (30, 0)])),
    (  "1:30", Curve(easeInOutSine, [(0, 0), (15, 1),   (30, 0)])),
]
QUARTER_SINES = [
    ("0.25\u21c5 6",  Curve(easeInOutSine, [(0, 0),    (3, 0.25), (6, 0)])),
    ("0.25\u21f5 6",  Curve(easeInOutSine, [(0, 0.25), (3, 0),    (6, 0.25)])),
    ("0.50\u21c5 6",  Curve(easeInOutSine, [(0, 0),    (3, 0.50), (6, 0)])),
    ("0.50\u21f5 6",  Curve(easeInOutSine, [(0, 0.50), (3, 0),    (6, 0.50)])),
    ("0.75\u21c5 6",  Curve(easeInOutSine, [(0, 0),    (3, 0.75), (6, 0)])),
    ("0.75\u21f5 6",  Curve(easeInOutSine, [(0, 0.75), (3, 0),    (6, 0.75)])),
    ("1.00\u21c5 6",  Curve(easeInOutSine, [(0, 0),    (3, 1),    (6, 0)])),
    ("1.00\u21f5 6",  Curve(easeInOutSine, [(0, 1),    (3, 0),    (6, 1)])),
    ("0.25\u21c5 12", Curve(easeInOutSine, [(0, 0),    (6, 0.25), (12, 0)])),
    ("0.25\u21f5 12", Curve(easeInOutSine, [(0, 0.25), (6, 0),    (12, 0.25)])),
    ("0.50\u21c5 12", Curve(easeInOutSine, [(0, 0),    (6, 0.5),  (12, 0)])),
    ("0.50\u21f5 12", Curve(easeInOutSine, [(0, 0.5),  (6, 0),    (12, 0.5)])),
    ("0.75\u21c5 12", Curve(easeInOutSine, [(0, 0),    (6, 0.75), (12, 0)])),
    ("0.75\u21f5 12", Curve(easeInOutSine, [(0, 0.75), (6, 0),    (12, 0.75)])),
    ("1.00\u21c5 12", Curve(easeInOutSine, [(0, 0),    (6, 1),    (12, 0)])),
    ("1.00\u21f5 12", Curve(easeInOutSine, [(0, 1),    (6, 0),    (12, 1)])),
    ("0.25\u21c5 30", Curve(easeInOutSine, [(0, 0),    (15, 0.25), (30, 0)])),
    ("0.25\u21f5 30", Curve(easeInOutSine, [(0, 0.25), (15, 0),    (30, 0.25)])),
    ("0.50\u21c5 30", Curve(easeInOutSine, [(0, 0),    (15, 0.5),  (30, 0)])),
    ("0.50\u21f5 30", Curve(easeInOutSine, [(0, 0.5),  (15, 0),    (30, 0.5)])),
    ("0.75\u21c5 30", Curve(easeInOutSine, [(0, 0),    (15, 0.75), (30, 0)])),
    ("0.75\u21f5 30", Curve(easeInOutSine, [(0, 0.75), (15, 0),    (30, 0.75)])),
    ("1.00\u21c5 30", Curve(easeInOutSine, [(0, 0),    (15, 1),    (30, 0)])),
    ("1.00\u21f5 30", Curve(easeInOutSine, [(0, 1),    (15, 0),    (30, 1)])),
]
BOUNCES = [
    ( "1/4:6",  Curve(easeInOutSine, mk_bounce(6, 1/4))),
    ( "1/3:6",  Curve(easeInOutSine, mk_bounce(6, 1/3))),
    ( "1/2:6",  Curve(easeInOutSine, mk_bounce(6, 1/2))),
    ( "2/3:6",  Curve(easeInOutSine, mk_bounce(6, 2/3))),
    ( "3/4:6",  Curve(easeInOutSine, mk_bounce(6, 3/4))),
    (   "1:6",  Curve(easeInOutSine, mk_bounce(6, 1))),
    ("1/4:12",  Curve(easeInOutSine, mk_bounce(12, 1/4))),
    ("1/3:12",  Curve(easeInOutSine, mk_bounce(12, 1/3))),
    ("1/2:12",  Curve(easeInOutSine, mk_bounce(12, 1/2))),
    ("2/3:12",  Curve(easeInOutSine, mk_bounce(12, 2/3))),
    ("3/4:12",  Curve(easeInOutSine, mk_bounce(12, 3/4))),
    (  "1:12",  Curve(easeInOutSine, mk_bounce(12, 1))),
    ("1/4:30",  Curve(easeInOutSine, mk_bounce(30, 1/4))),
    ("1/3:30",  Curve(easeInOutSine, mk_bounce(30, 1/3))),
    ("1/2:30",  Curve(easeInOutSine, mk_bounce(30, 1/2))),
    ("2/3:30",  Curve(easeInOutSine, mk_bounce(30, 2/3))),
    ("3/4:30",  Curve(easeInOutSine, mk_bounce(30, 3/4))),
    (  "1:30",  Curve(easeInOutSine, mk_bounce(30, 1))),
]
ONE_ZERO = [("1", 1), ("off", 0)]
INTS16 = [("1", 1), ("2", 2), ("3", 3), ("4", 4), ("5", 5), ("6", 6)]
INTS18 = INTS16 + [("7", 7), ("8", 8)]
INTS26 = INTS16[1:] 
INTS28 = INTS18[1:]
HALVES053 = [("0.5", 0.5), ("1", 1), ("1.5", 1.5), ("2", 2), ("2.5", 2.5), ("3", 3)]
HALVES056 = HALVES053 + [("4", 4), ("5", 5), ("6", 6)]
QUARTERS = [("0.25", 0.25), ("0.5", 0.5), ("0.75", 0.75), ("1.0", 1.0)]

class FadeOptions:
    default = ("fade", [
        ("off", 0.0),
        ("linear",    Curve(linear,           [(0, 0), (1, -1)])),
        ("reverse",   Curve(linear,           [(0, -1), (1, 0)])),
        ("ioSine",    Curve(easeInOutSine,    [(0, -1), (0.5, 0), (1, -1)])),
        ("oiSine",    Curve(easeInOutSine,    [(0, 0), (0.5, -1), (1, 0)])),
        ("ioCubic",   Curve(easeInOutCubic,   [(0, -1), (0.5, 0), (1, -1)])),
        ("oiCubic",   Curve(easeInOutCubic,   [(0, 0), (0.5, -1), (1, 0)])),
        ("ioBounce",  Curve(easeInOutBounce,  [(0, -1), (0.5, 0), (1, -1)])),
        ("oiBounce",  Curve(easeInOutBounce,  [(0, 0), (0.5, -1), (1, 0)])),
        ("ioElastic", Curve(easeInOutElastic, [(0, -1), (0.5, 0), (1, -1)])),
        ("oiElastic", Curve(easeInOutElastic, [(0, 0), (0.5, -1), (1, 0)])),
    ])

class FlashOptions:
    default = ("flash", FRACS + QUARTER_SINES + ONE_ZERO)

class FlickerOptions:
    default = ("flicker", FRACS + QUARTER_SINES + ONE_ZERO)

class FlitterOptions:
    default = ("flitter", FRACS + QUARTER_SINES + ONE_ZERO)

class FluxOptions:
    default = ("flux", FRACS + BOUNCES + ONE_ZERO)

class RainbowOptions:
    default = ("rainbow", FRACS + SINES + ONE_ZERO)

class SpinOptions:
    default = ("spin", [
        ("\u21bb 0.5", -0.5),
        ("\u21bb 1", -1),
        ("\u21bb 2", -2),
        ("\u21bb 3", -3),
        ("\u21bb 4", -4),
        ("\u21bb 5", -5),
        ("\u21bb 6", -6),
        ("\u21ba 0.5", 0.5),
        ("\u21ba 1", 1),
        ("\u21ba 2", 2),
        ("\u21ba 3", 3),
        ("\u21ba 4", 4),
        ("\u21ba 5", 5),
        ("\u21ba 6", 6),
        ("1x\u21bb\u21ba x1", Curve(easeInOutSine, mk_bounce(60, 1))),
        ("2x\u21bb\u21ba x1", Curve(easeInOutSine, mk_bounce(60, 2))),
        ("1x\u21bb\u21ba x2", Curve(easeInOutSine, mk_bounce(30, 1))),
        ("2x\u21bb\u21ba x2", Curve(easeInOutSine, mk_bounce(30, 2))),
        ("off", 0),
    ])

class SpiralOptions:
    const = ("spiral", [
        ("stepped", Curve(const, [
            (0, -3), (3, 3),
            (9, -1.5), (15, 1.5),
            (21, -0.5), (27, 0.5),
            (33, -1), (39, 1),
            (45, -2), (51, 2),
            (57, -3), (60, -3)
        ])),
        ("flip0.5", Curve(const, mk_bounce(12, 0.5))),
        ("flip1.0", Curve(const, mk_bounce(12, 1))),
        ("flip1.5", Curve(const, mk_bounce(12, 1.5))),
        ("flip2.0", Curve(const, mk_bounce(12, 2))),
        ("flip3.0", Curve(const, mk_bounce(12, 3))),
    ])
    curved = ("spiral", [
        ("0.5:12", Curve(easeInOutSine, mk_bounce(12, 0.5))),
        ("1.0:12", Curve(easeInOutSine, mk_bounce(12, 1))),
        ("1.5:12", Curve(easeInOutSine, mk_bounce(12, 1.5))),
        ("2.0:12", Curve(easeInOutSine, mk_bounce(12, 2))),
        ("3.0:12", Curve(easeInOutSine, mk_bounce(12, 3))),
        ("0.5:30", Curve(easeInOutSine, mk_bounce(30, 0.5))),
        ("1.0:30", Curve(easeInOutSine, mk_bounce(30, 1))),
        ("1.5:30", Curve(easeInOutSine, mk_bounce(30, 1.5))),
        ("2.0:30", Curve(easeInOutSine, mk_bounce(30, 2))),
        ("3.0:30", Curve(easeInOutSine, mk_bounce(30, 3))),
        ("0.5:60", Curve(easeInOutSine, mk_bounce(60, 0.5))),
        ("1.0:60", Curve(easeInOutSine, mk_bounce(60, 1))),
        ("1.5:60", Curve(easeInOutSine, mk_bounce(60, 1.5))),
        ("2.0:60", Curve(easeInOutSine, mk_bounce(60, 2))),
        ("3.0:60", Curve(easeInOutSine, mk_bounce(60, 3))),
    ])
    
class SparkleOptions:
    default = ("sparkles", FRACS + [
        ("L\u21c5 3",  Curve(easeInOutSine, [(0, 0.00), (1.5, 0.50), (3, 0.00)])),
        ("M\u21c5 3",  Curve(easeInOutSine, [(0, 0.25), (1.5, 0.50), (3, 0.25)])),
        ("H\u21c5 3",  Curve(easeInOutSine, [(0, 0.25), (1.5, 0.75), (3, 0.25)])),
        ("L\u21c5 6",  Curve(easeInOutSine, [(0, 0.00), (3, 0.50), (6, 0.00)])),
        ("M\u21c5 6",  Curve(easeInOutSine, [(0, 0.25), (3, 0.50), (6, 0.25)])),
        ("H\u21c5 6",  Curve(easeInOutSine, [(0, 0.25), (3, 0.75), (6, 0.25)])),
        ("L\u21c5 12", Curve(easeInOutSine, [(0, 0.00), (6, 0.50), (12, 0.00)])),
        ("M\u21c5 12", Curve(easeInOutSine, [(0, 0.25), (6, 0.50), (12, 0.25)])),
        ("H\u21c5 12", Curve(easeInOutSine, [(0, 0.25), (6, 0.75), (12, 0.25)])),
        ("L\u21c5 30", Curve(easeInOutSine, [(0, 0.00), (15, 0.50), (30, 0.00)])),
        ("M\u21c5 30", Curve(easeInOutSine, [(0, 0.25), (15, 0.50), (30, 0.25)])),
        ("H\u21c5 30", Curve(easeInOutSine, [(0, 0.25), (15, 0.75), (30, 0.25)])),
        ("off", 0),
    ])
    
class SparkleFuncOptions:
    default = ("sparkle_func", [
        ("base", ColorFuncs.BASE),
        ("base_whiten", ColorFuncs.BASE_WHITEN),
        ("blank", ColorFuncs.BLANK),
        ("invert", ColorFuncs.INVERT),
        ("invert_whiten", ColorFuncs.INVERT_WHITEN),
        ("whiten", ColorFuncs.WHITEN),
        ("random", ColorFuncs.RANDOM),
        # ("off", ColorFuncs.NOOP),
    ])
    basic = ("sparkle_func", [
        ("blank", ColorFuncs.BLANK),
        ("invert", ColorFuncs.INVERT),
        ("whiten", ColorFuncs.WHITEN),
        ("random", ColorFuncs.RANDOM),
        # ("off", ColorFuncs.NOOP),
    ])

class StreamerFuncOptions:
    default = ("streamer_func", [
        ("base", StreamerFuncs.BASE),
        ("base_whiten", StreamerFuncs.BASE_WHITEN),
        ("blank", StreamerFuncs.BLANK),
        ("invert", StreamerFuncs.INVERT),
        ("invert_whiten", StreamerFuncs.INVERT_WHITEN),
        ("whiten", StreamerFuncs.WHITEN),
        ("random", StreamerFuncs.RANDOM),
        ("off", StreamerFuncs.NOOP),
    ])
    basic = ("streamer_func", [
        ("blank", StreamerFuncs.BLANK),
        ("invert", StreamerFuncs.INVERT),
        ("whiten", StreamerFuncs.WHITEN),
        ("random", StreamerFuncs.RANDOM),
        ("off", StreamerFuncs.NOOP),
    ])

class BasicBitch(ControllablePattern):
    def __init__(self):
        self.controls = [
            FlashOptions.default,
            FlickerOptions.default,
            FlitterOptions.default,
            FluxOptions.default,
            SparkleOptions.default,
            SparkleFuncOptions.basic,
        ]

        super(BasicBitch, self).__init__(
            "Basic Bitch",
            base_color=BaseColor(l=0),
            flash=0.0,
            flicker=0.0,
            flitter=0.0,
            flux=0.0,
        )

class CircusTent(ControllablePattern):
    def __init__(self):
        self._rainbow = 1
        self._repeats = 3
        self._delay = 1.5
        self._streamer_func = StreamerFuncs.WHITEN
        
        self.controls = [
            ("repeats", INTS28),
            ("delay", HALVES053),
            RainbowOptions.default,
            SpinOptions.default,
            SparkleOptions.default,
            SparkleFuncOptions.basic,
            StreamerFuncOptions.basic,
        ]

        super(CircusTent, self).__init__(
            "Circus Tent",
            base_color=SplitColor(4, self.mk_split_funcs(1.5)),
            topologies=[RepeatTopology(4)],
            sparkles=0.5,
            spin=0.0,
            streamers=[],
        )

    @property
    def rainbow(self):
        return self._rainbow

    @rainbow.setter
    def rainbow(self, rainbow):
        self._rainbow = rainbow
        self.update_values()

    def mk_streamers(self):
        return streamer_choices(
            3,
            [
                [
                    {
                        "move_dir": move_dir,
                        "spin_dir": spin_dir,
                        "spin": Curve(const, [(0, 1), (3, 0.5), (6, 1)]),
                        "length": 1.0,
                        "width": Curve(const, [(0, 0.1), (3, 0.15), (6, 0.1)]),
                        "lifetime": 6.0,
                        "func": self._streamer_func,
                    } for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                ] for move_dir in [Direction.FROM_BOT, Direction.FROM_TOP]
            ],
        ) 

    def mk_split_funcs(self, delay):
        return periodic_choices(delay, [
            [
                BaseColor(h=self._rainbow * 0.25, l=-1),
                BaseColor(h=self._rainbow * 0.0, l=0, suppress=["sparkles"]),
                BaseColor(h=self._rainbow * 0.75,l=-1),
                BaseColor(h=self._rainbow * 0.5, l=0, suppress=["sparkles"]),
            ],
            [
                BaseColor(h=self._rainbow * 0.25, l=0, suppress=["sparkles"]),
                BaseColor(h=self._rainbow * 0.0, l=0, suppress=["sparkles"]),
                BaseColor(h=self._rainbow * 0.75, l=0, suppress=["sparkles"]),
                BaseColor(h=self._rainbow * 0.5, l=0, suppress=["sparkles"]),
            ],
            [
                BaseColor(h=self._rainbow * 0.25, l=0, suppress=["sparkles"]),
                BaseColor(h=self._rainbow * 0.0, l=-1),
                BaseColor(h=self._rainbow * 0.75, l=0, suppress=["sparkles"]),
                BaseColor(h=self._rainbow * 0.5, l=-1),
            ],
            [
                BaseColor(h=self._rainbow * 0.25, l=0, suppress=["sparkles"]),
                BaseColor(h=self._rainbow * 0.0, l=0, suppress=["sparkles"]),
                BaseColor(h=self._rainbow * 0.75, l=0, suppress=["sparkles"]),
                BaseColor(h=self._rainbow * 0.5, l=0, suppress=["sparkles"]),
            ],
        ]) 

    @property
    def repeats(self):
        return self._repeats

    @repeats.setter
    def repeats(self, repeats):
        self._repeats = repeats
        self.update_values()

    @property
    def delay(self):
        return self._delay

    @delay.setter
    def delay(self, delay):
        self._delay = delay
        self.update_values()

    @property
    def streamer_func(self):
        return self._streamer_func

    @streamer_func.setter
    def streamer_func(self, streamer_func):
        self._streamer_func = streamer_func
        self.update_values()

    def update_values(self):
        self.base_color = SplitColor(4, self.mk_split_funcs(self._delay))
        self.topologies = [RepeatTopology(self._repeats)]
        
class CoiledSpring(ControllablePattern):
    def __init__(self):
        self._rainbow = 1
        self._repeats = 3
        self._split = 0.25
        self._width = 0.1
        self._spirals = 2
        self._speed = 1

        self.controls = [
            ("split", FRACS),
            ("repeats", INTS28),
            ("speed", INTS16),
            ("spirals", HALVES053),
            ("width", FRACS),
            RainbowOptions.default,
            SpinOptions.default,
        ]

        super(CoiledSpring, self).__init__(
            "Coiled Spring",
            base_color=WindowColor(0.75, [
                BaseColor(w=0.75, s=0.0, l=-0.75, suppress=["sparkles", "streamers"]),
                BaseColor(l=-1),
            ]),
            topologies=[RepeatTopology(self._repeats)],
            spiral=0,
            streamers=[],
        )

    def update_values(self):
        self.base_color = WindowColor(1 - self._split, [
            BaseColor(w=0.75, s=0.0, l=-0.75, suppress=["sparkles", "streamers"]),
            BaseColor(l=-1),
        ])
        self.topologies = [RepeatTopology(self._repeats)]
        self.spiral=Curve(easeOutBounce, [
            (0, self._spirals),
            (15, -self._spirals),
            (30, self._spirals),
        ])
        self.streamers = streamer_choices(2, [[
            {
                "move_dir": Direction.FROM_BOT,
                "spin_dir": Spin.CLOCKWISE,
                "angle": (i/self._repeats) + (o/(self._repeats * 4)),
                "spin": Curve(easeOutBounce, [
                    (0, self._spirals),
                    (30 / self._speed, -self._spirals),
                    (60 / self._speed, self._spirals)]),
                "length": 2.0,
                "width": self._width / self._repeats,
                "lifetime": 2.0,
                "func": setcolor_streamer(h=i * (self._rainbow / 4), w=0, s=1, l=0.0),
            } for i in range(self._repeats)
        ] for o in range(4)])

    @property
    def rainbow(self):
        return self._rainbow

    @rainbow.setter
    def rainbow(self, rainbow):
        self._rainbow = rainbow
        self.update_values()

    @property
    def repeats(self):
        return self._repeats

    @repeats.setter
    def repeats(self, repeats):
        self._repeats = repeats
        self.update_values()

    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, speed):
        self._speed = speed
        self.update_values()

    @property
    def split(self):
        return self._split

    @split.setter
    def split(self, split):
        self._split = split
        self.update_values()

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        self._width = width
        self.update_values()

    @property
    def spirals(self):
        return self._spirals

    @spirals.setter
    def spirals(self, spirals):
        self._spirals = spirals
        self.update_values()

class Confetti(ControllablePattern):
    def __init__(self):
        self._delay = 0.25
        self._direction = "FROM_TOP"
        self._intensity = "low"
        self._rainbow = 1.0

        self.controls = [
            ("direction", [
                ("\u2193", Direction.FROM_TOP),
                ("\u2191", Direction.FROM_BOT),
                ("\u21c5", "BOTH"),
            ]),
            ("delay", QUARTERS),
            ("intensity", [
                ("low", "low"),
                ("medium", "medium"),
                ("high", "high"),
            ]),
            FlickerOptions.default,
            FlitterOptions.default,
            FluxOptions.default,
            RainbowOptions.default,
            SparkleOptions.default,
            SparkleFuncOptions.default,
        ]

        super(Confetti, self).__init__(
            "Confetti",
            sparkles=0,
            streamers=self.mk_streamer_choices(self._delay, Direction.FROM_TOP, (1, 1)),
        )
    
    def update_values(self):
        if self._intensity == "low":
            choose = (0, 1)
        elif self._intensity == "medium":
            choose = (0, 2)
        else:
            choose = (1, 2)
            
        if self._direction == "BOTH":
            self.streamers = combined_choices([
                self.mk_streamer_choices(self._delay, Direction.FROM_TOP, choose),
                self.mk_streamer_choices(self._delay, Direction.FROM_BOT, choose),
            ])
        else:
            self.streamers = self.mk_streamer_choices(
                self._delay, self._direction, (choose[0] * 2, choose[1] * 2))

    def mk_streamer_choices(self, delay, move_dir, choose):
        return streamer_choices(delay,
            [[
                {
                    "move_dir": move_dir,
                    "spin_dir": spin_dir,
                    "spin": spin,
                    "width": width,
                    "length": lambda _: choice([0.25, 0.5])(),
                    "lifetime": lambda _: rand(3, 6)(),
                    "func": RandomColorStreamerFunc(
                        -self._rainbow / 2, self.rainbow / 2, w=0, s=1, l=0),
                }
                for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                for spin, width in [(0.5, 0.1), (1, 0.15), (1.5, 0.2)]
                for _ in range(4)
            ]],
            choose=choose)

    @property
    def delay(self):
        return self._delay

    @delay.setter
    def delay(self, delay):
        self._delay = delay
        self.update_values()

    @property
    def direction(self):
        return self._direction

    @direction.setter
    def direction(self, direction):
        self._direction = direction
        self.update_values()

    @property
    def intensity(self):
        return self._intensity

    @intensity.setter
    def intensity(self, intensity):
        self._intensity = intensity
        self.update_values()

    @property
    def rainbow(self):
        return self._rainbow

    @rainbow.setter
    def rainbow(self, rainbow):
        self._rainbow = rainbow
        self.update_values()

class FallingSnow(ControllablePattern):
    def __init__(self):
        self._colors = 8
        self._fade = easeInOutCubic
        
        self.controls = [
            ("colors", [("6", 6), ("8", 8), ("10", 10), ("12", 12)]),
            FadeOptions.default,
            FlitterOptions.default,
            FluxOptions.default,
            SparkleOptions.default,
            SparkleFuncOptions.basic,
            ("streamers", [
                ("light", self.mk_streamers("light")),
                ("medium", self.mk_streamers("medium")),
                ("heavy", self.mk_streamers("heavy")),
                ("off", []),
            ]),
        ]

        super(FallingSnow, self).__init__(
            "Falling Snow",
            base_color=FallingColor(),
            flitter=0.25,
            flux=1/8,
            sparkles=Curve(easeInOutSine, [(0, 0.25), (6, 0.5), (12, 0.25)]),
            streamers=[],
        )

    def mk_streamers(self, weight):
        if weight == "light":
            func = setcolor_streamer(w=0.2, l=-1)
            choose = (0, 1)
        elif weight == "medium":
            func = setcolor_streamer(w=1/3, l=-0.75)
            choose = (0, 2)
        else:
            func = setcolor_streamer(w=0.5, l=-0.5)
            choose = (0, 4)

        return streamer_choices(
            1,
            [[
                {
                    "move_dir": move_dir,
                    "spin_dir": spin_dir,
                    "spin": spin,
                    "width": width,
                    "length": 0.5,
                    "lifetime": lifetime,
                    "func": func,
                }
                    for move_dir in [Direction.FROM_BOT, Direction.FROM_TOP]
                    for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                    for lifetime in [3, 4.5, 6, 7.5]
                    for spin, width in [(2, 0.2), (3, 0.15)]
            ]],
            choose=choose,
        ) 

    @property
    def colors(self):
        return self._colors

    @colors.setter
    def colors(self, colors):
        self._colors = colors
        self.update_values()

    @property
    def fade(self):
        return self._fade

    @fade.setter
    def fade(self, fade):
        self._fade = fade
        self.update_values()

    def update_values(self):
        base_hue = self.base_color.base_hue
        self.base_color = FallingColor(
            self._colors,
            (self._colors // 2) - 1,
            fade_func=self._fade,
        )
        self.base_color.init(base_hue)

class Galaxus(ControllablePattern):
    def __init__(self):
        self._speed = 2
        self._spins = 3
        self._spirals = 6
        self._width = 0.1
        self._wobble = 0.25

        self.controls = [
            ("speed", HALVES056),
            ("wobble", FRACS + ONE_ZERO),
            ("spirals", INTS28),
            ("width", FRACS + ONE_ZERO),
            FluxOptions.default,
            SparkleOptions.default,
            SparkleFuncOptions.default,
        ]

        super(Galaxus, self).__init__(
            "Galaxus",
            sparkles=0.25,
            sparkle_func=self._sparkle_func,
            streamers=self.mk_streamers(),
        )

    @staticmethod
    def _sparkle_func(color: Color) -> Color:
        if color.l == -1.0:
            return ColorFuncs.WHITEN(color)
        else:
            return color

    def mk_streamers(self):
        streamers = [
            [
                [
                    {
                        "move_dir": move_dir,
                        "spin_dir": spin_dir,
                        "angle": offset + (i / self._spirals) + (o / (self._spirals * self._spins)),
                        "spin": 0.5,
                        "length": 1,
                        "width": self._width / self._spirals,
                        "lifetime": self._speed * 1.5,
                        "func": func,
                    } for i in range(self._spirals)
                ] for o in range(self._spins)
            ] for move_dir, spin_dir, offset, func in zip(
                [Direction.FROM_BOT, Direction.FROM_TOP],
                [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE],
                [0, 0.5 / self._spirals],
                [
                    setcolor_streamer(
                        l=0,
                        h=Curve(easeInOutSine, [
                            (0, 0),
                            (7.5, -self._wobble),
                            (15, 0),
                            (22.5, self._wobble),
                            (30, 0),
                        ]),
                    ),
                    setcolor_streamer(
                        l=0,
                        h=Curve(easeInOutSine, [
                            (0, 0.5),
                            (5, 0.5 - self._wobble),
                            (10, 0.5),
                            (15, 0.5 + self._wobble),
                            (20, 0.5),
                        ]),
                    ),
                ],
            )
        ]
        return combined_choices([
            streamer_choices(self._speed, streamers[0]),
            streamer_choices(self._speed, streamers[1], delay_offset=self._speed / 2),
        ])

    @property
    def wobble(self):
        return self._wobble

    @wobble.setter
    def wobble(self, wobble):
        self._wobble = wobble
        self.update_values()

    @property
    def spins(self):
        return self._spins

    @spins.setter
    def spins(self, spins):
        self._spins = spins
        self.update_values()

    @property
    def spirals(self):
        return self._spirals

    @spirals.setter
    def spirals(self, spirals):
        self._spirals = spirals
        self.update_values()

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        self._width = width
        self.update_values()

    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, speed):
        self._speed = speed
        self.update_values()

    def update_values(self):
        self.streamers = self.mk_streamers()

class Groovy(ControllablePattern):
    def __init__(self):
        self._rainbow = 1/8
        self._distortion = 0.5
        self._mid_distortion = 0.5
        self._mirror = 2

        self.controls = [
            ("mirror", INTS28),
            ("distortion", FRACS),
            ("mid_distortion", FRACS),
            FlickerOptions.default,
            FlitterOptions.default,
            FluxOptions.default,
            RainbowOptions.default,
            SparkleOptions.default,
            SparkleFuncOptions.default,
        ]

        super(Groovy, self).__init__(
            "Groovy",
            base_color=SplitColor(
                8,
                [
                    BaseColor(
                        l=0.0, spread=False, suppress=["sparkles"],
                        h=Curve(easeInOutSine, [(0, 1/8), (15, 0), (30, 1/8)]),
                    ),
                    BaseColor(),
                    BaseColor(),
                    BaseColor(
                        l=0.0, spread=False, suppress=["sparkles"],
                    ),
                    BaseColor(
                        l=0.0, spread=False, suppress=["sparkles"],
                    ),
                    BaseColor(),
                    BaseColor(),
                    BaseColor(
                        l=0.0, spread=False, suppress=["sparkles"],
                        h=Curve(easeInOutSine, [(0, -1/8), (10, 0), (20, -1/8)]),
                    ),
                ],
            ),
            topologies=[
                DistortTopology(
                    easeInOutSine,
                    Curve(easeInOutSine, [(0, 0.5), (30, -0.5), (60, 0.5)]),
                    Curve(easeInOutSine, [(0, -0.5), (30, 0.5), (60, -0.5)]),
                    Curve(easeInOutSine, [(0, 0.5), (5, 0.3), (10, 0.5), (15, 0.7), (20, 0.5)])
                ),
                MirrorTopology(2),
            ],
            sparkles=0.25,
        )

    @property
    def rainbow(self):
        return self._rainbow

    @rainbow.setter
    def rainbow(self, rainbow):
        self._rainbow = rainbow
        self.update_values()

    @property
    def distortion(self):
        return self._distortion

    @distortion.setter
    def distortion(self, distortion):
        self._distortion = distortion
        self.update_values()

    @property
    def mid_distortion(self):
        return self._mid_distortion

    @mid_distortion.setter
    def mid_distortion(self, mid_distortion):
        self._mid_distortion = mid_distortion
        self.update_values()

    @property
    def mirror(self):
        return self._mirror

    @mirror.setter
    def mirror(self, mirror):
        self._mirror = mirror
        self.update_values()

    def update_values(self):
        self.base_color = SplitColor(
            8,
            [
                BaseColor(
                    l=0.0, spread=False, suppress=["sparkles"],
                    h=Curve(easeInOutSine, [
                        (0, self._rainbow),
                        (15, 0),
                        (30, self._rainbow),
                    ]),
                ),
                BaseColor(),
                BaseColor(),
                BaseColor(
                    l=0.0, spread=False, suppress=["sparkles"],
                ),
                BaseColor(
                    l=0.0, spread=False, suppress=["sparkles"],
                ),
                BaseColor(),
                BaseColor(),
                BaseColor(
                    l=0.0, spread=False, suppress=["sparkles"],
                    h=Curve(easeInOutSine, [
                        (0, -self._rainbow),
                        (10, 0),
                        (20, -self._rainbow)]),
                ),
            ],
        )
        self.topologies = [
            DistortTopology(
                easeInOutSine,
                Curve(easeInOutSine, [
                    (0, self._distortion),
                    (30, -self._distortion),
                    (60, self._distortion),
                ]),
                Curve(easeInOutSine, [
                    (0, -self._distortion),
                    (30, self._distortion),
                    (60, -self._distortion),
                ]),
                Curve(easeInOutSine, [
                    (0, 0.5),
                    (5, 0.5 - (0.5 * self._mid_distortion)),
                    (10, 0.5),
                    (15, 0.5 + (0.5 * self._mid_distortion)),
                    (20, 0.5),
                ])
            ),
            MirrorTopology(self._mirror),
        ]
    
class Rainbro(ControllablePattern):
    def __init__(self):
        self._rainbow = 1
        self._repeats = 0

        self.controls = [
            ("repeats", [("jumble", 0)] + INTS28),
            SpiralOptions.curved,
            FlashOptions.default,
            FlickerOptions.default,
            FlitterOptions.default,
            FluxOptions.default,
            RainbowOptions.default,
            SpinOptions.default,
            SparkleOptions.default,
            SparkleFuncOptions.default,
        ]

        super(Rainbro, self).__init__(
            "Rainbro",
            base_color=BaseColor(l=0),
            topologies=[RepeatTopology(Curve(const, [
                    (0, 6),
                    (7.5, 8),
                    (22.5, 4),
                    (37.5, 2),
                    (52.5, 3),
                    (60, 6),
            ]))],
            flitter=0.1,
            flux=1/16,
            spin=6,
            spiral=0,
            spread=0,
        )

    @property
    def rainbow(self):
        return self._rainbow

    @rainbow.setter
    def rainbow(self, rainbow):
        self._rainbow = rainbow
        self.update_values()

    @property
    def repeats(self):
        return self._repeats

    @repeats.setter
    def repeats(self, repeats):
        self._repeats = repeats
        self.update_values()

    def update_values(self):
        self.spread = Curve(easeInOutSine, [
            (0, self._rainbow),
            (15, -self._rainbow),
            (30, self._rainbow),
        ])

        if self._repeats == 0:
            self.topologies= [RepeatTopology(Curve(const, [
                    (0, 6),
                    (7.5, 8),
                    (22.5, 4),
                    (37.5, 2),
                    (52.5, 3),
                    (60, 6),
            ]))]
        else:
            self.topologies= [RepeatTopology(self._repeats)]

class SlidingDoor(ControllablePattern):
    def __init__(self):
        self._mirror = 0
        self._rainbow = 0
        self._speed = 1

        self.controls = [
            ("speed", INTS26),
            ("mirror", [("jumble", 0)] + INTS28),
            FlashOptions.default,
            FlickerOptions.default,
            FlitterOptions.default,
            FluxOptions.default,
            RainbowOptions.default,
            SparkleOptions.default,
            SparkleFuncOptions.default,
        ]

        super(SlidingDoor, self).__init__(
            "Sliding Door",
            base_color=WindowColor(
                Curve(easeInOutSine, [(0, 0), (3, 1), (6, 0)]),
                [
                    BaseColor(l=-1, spread=False),
                    BaseColor(
                        h=Curve(const, [(0, 0), (6, 0.5), (12, 0)]),
                        l=0.0,
                        suppress=["sparkles", "streamers"],
                        spread=False,
                    ),
                ],
            ),
            topologies=[MirrorTopology(Curve(const, [
                (0, 4),
                (6, 3),
                (12, 6),
                (18, 2),
                (24, 5),
                (30, 4),
            ]))],
            flux=1/16,
            spread=Curve(easeInOutSine, [(0, 0.5), (15, -0.5), (30, 0.5)]),
            sparkles=0.5,
            streamers=[],
        )

    @property
    def mirror(self):
        return self._mirror

    @mirror.setter
    def mirror(self, mirror):
        self._mirror = mirror
        self.update_values()

    @property
    def rainbow(self):
        return self._rainbow

    @rainbow.setter
    def rainbow(self, rainbow):
        self._rainbow = rainbow
        self.update_values()

    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, speed):
        self._speed = speed
        self.update_values()

    def update_values(self):
        self.base_color = WindowColor(
            Curve(easeInOutSine, [
                (0, 0),
                (15 / self._speed, 1),
                (30 / self._speed, 0),
            ]),
            [
                BaseColor(l=-1, spread=False),
                BaseColor(
                    h=Curve(const, [
                        (0, self._rainbow / 2),
                        (30 / self._speed, -self._rainbow / 2),
                        (60 / self._speed, self._rainbow / 2),
                    ]),
                    l=0,
                    suppress=["sparkles", "streamers"],
                    spread=False,
                ),
            ],
        )
        self.streamers = self.mk_streamers()
        self.spread = Curve(easeInOutSine, [
            (0, self._rainbow / 2),
            (15, -self._rainbow / 2),
            (30, self._rainbow / 2),
        ])
        mirror = Curve(const, [
            (0, 4),
            (6, 3),
            (12, 6),
            (18, 2),
            (24, 5),
            (30, 4),
        ]) if self._mirror == 0 else self._mirror
        self.topologies = [MirrorTopology(mirror)]

    def mk_streamers(self):
        streamers = [
            [
                [
                    {
                        "move_dir": move_dir,
                        "spin_dir": spin_dir,
                        "spin": Curve(const, [(0, 1), (6, 0.5), (12, 1)]),
                        "length": 1.0,
                        "width": Curve(const, [(0, 0.1), (6, 0.15), (12, 0.1)]),
                        "lifetime": 6.0,
                        "func": func,
                    } for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                ] for move_dir in [Direction.FROM_BOT, Direction.FROM_TOP]
            ] for func in [
                setcolor_streamer(h=self._rainbow * 0.25, l=0, make_white=True),
                setcolor_streamer(h=-self._rainbow * 0.25, l=0.75, make_white=True),
            ]
        ]
        return combined_choices([
            streamer_choices(3, streamers[0]),
            streamer_choices(3, streamers[1]),
        ])
        
class SpiralTop(ControllablePattern):
    def __init__(self):
        self._mirror = 2
        self._speed = 1
        self._spirals = 1

        self.controls = [
            ("mirror", INTS28),
            ("speed", INTS16),
            ("spread", FRACS),
            ("spirals", HALVES053),
            FlickerOptions.default,
            FlitterOptions.default,
            FluxOptions.default,
            SpinOptions.default,
            SparkleOptions.default,
            SparkleFuncOptions.default,
        ]

        super(SpiralTop, self).__init__(
            "Spiral Top",
            base_color=WindowColor(Curve(linear, [(0, 0), (3, 1)])),
            topologies=[MirrorTopology(3)],
            flux=1/16,
            spin=Curve(easeInSine, [(0, 0), (15, 2), (30, 0), (45, -2), (60, 0)]),
            spiral=Curve(linear, [(0, 0), (7.5, 2), (15, 0), (22.5, -2), (30, 0)]),
            spread=1/3,
            sparkles=0.15,
        )

    def update_values(self):
        self.base_color = WindowColor(Curve(linear, [(0, 0), (15 / self._speed, 1)]))
        self.topologies = [MirrorTopology(self._mirror)]
        self.spiral = Curve(easeInOutSine, [
            (0, 0),
            (15 / self._speed, self._spirals),
            (30 / self._speed, 0),
            (45 / self._speed, -self._spirals),
            (60 / self._speed, 0),
        ])

    @property
    def mirror(self):
        return self._mirror

    @mirror.setter
    def mirror(self, mirror):
        self._mirror = mirror
        self.update_values()

    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, speed):
        self._speed = speed
        self.update_values()

    @property
    def spirals(self):
        return self._spirals

    @spirals.setter
    def spirals(self, spirals):
        self._spirals = spirals
        self.update_values()

class TurningWindows(ControllablePattern):
    def __init__(self, splits=8, repeats=4):
        self._delay = 0.25
        self._splits = 8
        self._repeats = 4
        self._rainbow = 1

        self.controls = [
            ("splits", INTS28),
            ("repeats", INTS18),
            ("delay", QUARTERS),
            RainbowOptions.default,
            FlickerOptions.default,
            FlitterOptions.default,
            FluxOptions.default,
            SpinOptions.default,
            SparkleOptions.default,
            SparkleFuncOptions.default,
        ]

        base_windows = [None] * splits
        windows = []
        for i in range(splits):
            windows.append(base_windows[:i] + [BaseColor()] + base_windows[(i+1):])

        super(TurningWindows, self).__init__(
            "Turning Windows",
            base_color=SplitColor(
                splits,
                periodic_choices(0.25, windows),
                suppress=["sparkles"],
            ),
            topologies=[
                RepeatTopology(repeats),
                TurntTopology(
                    repeats,
                    CombinedCurve([
                        Curve(easeOutSine, [(0, 0), (15, 1)]),
                        Curve(easeOutSine, [(0, 0), (15, -1)]),
                    ])
                ),
            ],
            spin=0,
            spread=0,
            sparkles=0,
        )

    def update_values(self):
        base_windows = [None] * self._splits
        windows = []
        for i in range(self._splits):
            windows.append(base_windows[:i] + [BaseColor()] + base_windows[(i+1):])

        self.base_color = SplitColor(
            self._splits,
            periodic_choices(self._delay, windows),
            suppress=["sparkles"],
        )
        self.topologies = [
            RepeatTopology(self._repeats),
            TurntTopology(
                self.repeats,
                CombinedCurve([
                        Curve(easeOutSine, [(0, 0), (15, 1)]),
                        Curve(easeOutSine, [(0, 0), (15, -1)]),
                ])
            )
        ]
        self.spread = Curve(linear, [
            (0, 0),
            (15, self._rainbow),
            (30, 0),
            (45, self._rainbow),
            (60, 0),
        ])
        
    @property
    def delay(self):
        return self._delay

    @delay.setter
    def delay(self, delay):
        self._delay = delay
        self.update_values()

    @property
    def repeats(self):
        return self._repeats

    @repeats.setter
    def repeats(self, repeats):
        self._repeats = repeats
        self.update_values()

    @property
    def rainbow(self):
        return self._rainbow

    @rainbow.setter
    def rainbow(self, rainbow):
        self._rainbow = rainbow
        self.update_values()

    @property
    def splits(self):
        return self._splits

    @splits.setter
    def splits(self, splits):
        self._splits = splits
        self.update_values()

class TwistedRainbows(ControllablePattern):
    def __init__(self):
        self._repeats = 0
        self._rainbow = 1
        self._splits = 3
        self._streamer_func = StreamerFuncs.WHITEN

        self.controls = [
            ("splits", INTS28),
            ("repeats", [("jumble", 0)] + INTS28),
            SpinOptions.default,
            FlickerOptions.default,
            FlitterOptions.default,
            FluxOptions.default,
            RainbowOptions.default,
            SpiralOptions.const,
            StreamerFuncOptions.basic,
        ]

        super(TwistedRainbows, self).__init__(
            "Twisted Rainbows",
            base_color=SplitColor(3),
            topologies=[RepeatTopology(2)],
            spin=0,
            spread=0,
            spiral=0,
            streamers=[],
        )

    def update_values(self):
        if self._repeats == 0:
           repeats = Curve(const, [
                (0, 1),
                (12, 3),
                (24, 5),
                (36, 4),
                (48, 2),
                (60, 1)
            ]) 
        else:
            repeats = self._repeats

        self.base_color = SplitColor(self._splits)
        self.topologies = [RepeatTopology(repeats)]
        self.spread = Curve(easeInOutCubic, [
            (0, self._rainbow / 2),
            (3, 0),
            (6, -self._rainbow / 2),
            (9, 0),
            (12, self._rainbow / 2),
        ])
        self.spiral = Curve(const, [
            (0, -3), (3, 3),
            (9, -1.5), (15, 1.5),
            (21, -0.5), (27, 0.5),
            (33, -1), (39, 1),
            (45, -2), (51, 2),
            (57, -3), (60, -3)
        ])
        self.streamers = streamer_choices(
            1,
            [[
                {
                    "move_dir": move_dir,
                    "spin_dir": spin_dir,
                    "spin": 2.0,
                    "length": 2.0,
                    "width": 0.15,
                    "lifetime": 3,
                    "func": self._streamer_func,
                }
                    for move_dir in [Direction.FROM_BOT, Direction.FROM_TOP]
                    for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
            ]],
            choose=(0, 2),
        )

    @property
    def streamer_func(self):
        return self._streamer_func

    @streamer_func.setter
    def streamer_func(self, streamer_func):
        self._streamer_func = streamer_func
        self.update_values()

    @property
    def repeats(self):
        return self._repeats

    @repeats.setter
    def repeats(self, repeats):
        self._repeats = repeats
        self.update_values()

    @property
    def rainbow(self):
        return self._rainbow

    @rainbow.setter
    def rainbow(self, rainbow):
        self._rainbow = rainbow
        self.update_values()

    @property
    def splits(self):
        return self._splits

    @splits.setter
    def splits(self, splits):
        self._splits = splits
        self.update_values()

class DroppingPlates(ControllablePattern):
    def __init__(self):
        self._fade = None
        self._mirror = 4
        self._rainbow = 1
        self._speed = 1

        self.controls = [
            ("mirror", INTS28),
            ("speed", INTS16),
            FadeOptions.default,
            FlashOptions.default,
            FlickerOptions.default,
            FlitterOptions.default,
            FluxOptions.default,
            RainbowOptions.default,
            SpiralOptions.curved,
            SparkleOptions.default,
            SparkleFuncOptions.default,
        ]

        super(DroppingPlates, self).__init__(
            "Dropping Plates",
            base_color=SplitColor(3, [
                FallingColor(
                    8, 3,
                ),
                FallingColor(
                    12, 5,
                    hue_func=Curve(linear, [(0, -1), (60, 1)]),
                ),
                FallingColor(
                    16, 7,
                    hue_func=Curve(linear, [(0, 1), (60, -1)]),
                ),
            ]),
            topologies=[MirrorTopology(4)],
        )

    def update_values(self):
        self.base_color = SplitColor(3, [
            FallingColor(8, 3,
                         speed=self._speed,
                         fade_func=self._fade),
            FallingColor(12, 5,
                         speed=self._speed,
                         fade_func=self._fade,
                         hue_func=Curve(linear, [(0, -self._rainbow), (60, self._rainbow)])),
            FallingColor(16, 7,
                         speed=self._speed,
                         fade_func=self._fade,
                         hue_func=Curve(linear, [(0, self._rainbow), (60, -self._rainbow)])),
        ])
        self.topologies = [MirrorTopology(self._mirror)]

    @property
    def fade(self):
        return self._fade

    @fade.setter
    def fade(self, fade):
        self._fade = fade
        self.update_values()

    @property
    def mirror(self):
        return self._mirror

    @mirror.setter
    def mirror(self, mirror):
        self._mirror = mirror
        self.update_values()

    @property
    def rainbow(self):
        return self._rainbow

    @rainbow.setter
    def rainbow(self, rainbow):
        self._rainbow = rainbow
        self.update_values()

    @property
    def speed(self):
        return self._speed

    @speed.setter
    def speed(self, speed):
        self._speed = speed
        self.update_values()

class Pulsar(ControllablePattern):
    def __init__(self):
        self._color_speed = 5
        self._pulse_speed = 5

        self.controls = [
            ("color_speed", INTS16),
            ("pulse_speed", INTS16),
            FlashOptions.default,
            FlickerOptions.default,
            FlitterOptions.default,
            FluxOptions.default,
            SparkleOptions.default,
            SparkleFuncOptions.default,
        ]

        super(Pulsar, self).__init__(
            "Pulsar",
            base_color=BaseColor(),
        )

    def update_values(self):
        self.base_color = BaseColor(
            h=Curve(linear, [
                (0, -1),
                (15 / self._color_speed, 1),
                (30 / self._color_speed, -1),
            ]), l=Curve(easeInOutSine, [
                (0, -1),
                (15 / self._pulse_speed, 0),
                (30 / self._pulse_speed, -1),
            ]))

    @property
    def color_speed(self):
        return self._color_speed

    @color_speed.setter
    def color_speed(self, color_speed):
        self._color_speed = color_speed
        self.update_values()

    @property
    def pulse_speed(self):
        return self._pulse_speed

    @pulse_speed.setter
    def pulse_speed(self, pulse_speed):
        self._pulse_speed = pulse_speed
        self.update_values()

if __name__ == "__main__":
    patterns = [
        BasicBitch(),
        CircusTent(),
        CoiledSpring(),
        Confetti(),
        FallingSnow(),
        Galaxus(),
        Groovy(),
        Rainbro(),
        SlidingDoor(),
        SpiralTop(),
        TurningWindows(),
        TwistedRainbows(),
        DroppingPlates(),
        Pulsar(),
    ]
    animation = Blender(patterns)
    # animation = Blender(patterns, -1, True)
    animation_thread, draw_menu = get_thread_and_menu(animation)
    animation_thread.start()
    curses.wrapper(draw_menu)
    animation_thread.join()
