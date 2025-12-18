import curses

from pytweening import (
    linear,
    easeInSine,
    easeOutSine,
    easeInOutSine,
    easeInBounce,
    easeOutBounce,
    easeInOutBounce,
    easeInCubic,
    easeOutCubic,
    easeInOutCubic,
    easeInElastic,
    easeOutElastic,
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
    Random,
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
    MirrorTopology,
    RepeatTopology,
    TurntTopology,
    DistortTopology,
)
from ui import get_thread_and_menu


FRACS = [
    ("1/8", 1/8),
    ("1/6", 1/6),
    ("1/5", 1/5),
    ("1/4", 1/4),
    ("1/3", 1/3),
    ("1/2", 1/2),
    ("2/3", 2/3),
    ("3/4", 3/4),
    ("4/5", 4/5),
    ("5/6", 5/6),
    ("7/8", 7/8),
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
    ("0.25\u21c5 6", Curve(easeInOutSine, [(0, 0),    (3, 0.25), (6, 0)])),
    ("0.25\u21f5 6", Curve(easeInOutSine, [(0, 0.25), (3, 0),    (6, 0.25)])),
    ("0.50\u21c5 6", Curve(easeInOutSine, [(0, 0),    (3, 0.50), (6, 0)])),
    ("0.50\u21f5 6", Curve(easeInOutSine, [(0, 0.50), (3, 0),    (6, 0.50)])),
    ("0.75\u21c5 6", Curve(easeInOutSine, [(0, 0),    (3, 0.75), (6, 0)])),
    ("0.75\u21f5 6", Curve(easeInOutSine, [(0, 0.75), (3, 0),    (6, 0.75)])),
    ("1.00\u21c5 6", Curve(easeInOutSine, [(0, 0),    (3, 1),    (6, 0)])),
    ("1.00\u21f5 6", Curve(easeInOutSine, [(0, 1),    (3, 0),    (6, 1)])),
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
    ("1/4:6",  Curve(easeInOutSine, [(0, 0), (1.5, 1/4), (3, 0), (4.5, -1/4), (6, 0)])),
    ("1/3:6",  Curve(easeInOutSine, [(0, 0), (1.5, 1/3), (3, 0), (4.5, -1/3), (6, 0)])),
    ("1/2:6",  Curve(easeInOutSine, [(0, 0), (1.5, 1/2), (3, 0), (4.5, -1/2), (6, 0)])),
    ("2/3:6",  Curve(easeInOutSine, [(0, 0), (1.5, 2/3), (3, 0), (4.5, -2/3), (6, 0)])),
    ("3/4:6",  Curve(easeInOutSine, [(0, 0), (1.5, 3/4), (3, 0), (4.5, -3/4), (6, 0)])),
    (  "1:6",  Curve(easeInOutSine, [(0, 0), (1.5, 1),   (3, 0), (4.5, -1),   (6, 0)])),
    ("1/4:12", Curve(easeInOutSine, [(0, 0), (3, 1/4), (6, 0), (9, -1/4), (12, 0)])),
    ("1/3:12", Curve(easeInOutSine, [(0, 0), (3, 1/3), (6, 0), (9, -1/3), (12, 0)])),
    ("1/2:12", Curve(easeInOutSine, [(0, 0), (3, 1/2), (6, 0), (9, -1/2), (12, 0)])),
    ("2/3:12", Curve(easeInOutSine, [(0, 0), (3, 2/3), (6, 0), (9, -2/3), (12, 0)])),
    ("3/4:12", Curve(easeInOutSine, [(0, 0), (3, 3/4), (6, 0), (9, -3/4), (12, 0)])),
    (  "1:12", Curve(easeInOutSine, [(0, 0), (3, 1),   (6, 0), (9, -1),   (12, 0)])),
    ("1/4:30", Curve(easeInOutSine, [(0, 0), (7.5, 1/4), (15, 0), (22.5, -1/4), (30, 0)])),
    ("1/3:30", Curve(easeInOutSine, [(0, 0), (7.5, 1/3), (15, 0), (22.5, -1/3), (30, 0)])),
    ("1/2:30", Curve(easeInOutSine, [(0, 0), (7.5, 1/2), (15, 0), (22.5, -1/2), (30, 0)])),
    ("2/3:30", Curve(easeInOutSine, [(0, 0), (7.5, 2/3), (15, 0), (22.5, -2/3), (30, 0)])),
    ("3/4:30", Curve(easeInOutSine, [(0, 0), (7.5, 3/4), (15, 0), (22.5, -3/4), (30, 0)])),
    (  "1:30", Curve(easeInOutSine, [(0, 0), (7.5, 1),   (15, 0), (22.5, -1),   (30, 0)])),
]
ONE_ZERO = [("1", 1), ("off", 0)]
INTS16 = [("1", 1), ("2", 2), ("3", 3), ("4", 4), ("5", 5), ("6", 6)]
INTS18 = INTS16 + [("7", 7), ("8", 8)]
INTS26 = INTS16[1:] 
INTS28 = INTS18[1:]
HALVES053 = [("0.5", 0.5), ("1", 1), ("1.5", 1.5), ("2", 2), ("2.5", 2.5), ("3", 3)]
HALVES056 = HALVES053 + [("4", 4), ("5", 5), ("6", 6)]
QUARTERS = [("0.25", 0.25), ("0.5", 0.5), ("0.75", 0.75), ("1.0", 1.0)]

def make_option(name, values):
    return (name, [(str(i), i) for i in values])

class SparkleFuncOptions:
    default = ("sparkle_func", [
        ("base", ColorFuncs.BASE),
        ("base_whiten", ColorFuncs.BASE_WHITEN),
        ("blank", ColorFuncs.BLANK),
        ("invert", ColorFuncs.INVERT),
        ("invert_whiten", ColorFuncs.INVERT_WHITEN),
        ("whiten", ColorFuncs.WHITEN),
    ])
    basic = ("sparkle_func", [
        ("blank", ColorFuncs.BLANK),
        ("invert", ColorFuncs.INVERT),
        ("whiten", ColorFuncs.WHITEN),
    ])

class StreamerFuncOptions:
    default = ("streamer_func", [
        ("base", StreamerFuncs.BASE),
        ("base_whiten", StreamerFuncs.BASE_WHITEN),
        ("blank", StreamerFuncs.BLANK),
        ("invert", StreamerFuncs.INVERT),
        ("invert_whiten", StreamerFuncs.INVERT_WHITEN),
        ("whiten", StreamerFuncs.WHITEN),
        ("off", StreamerFuncs.NOOP),
    ])
    basic = ("streamer_func", [
        ("blank", StreamerFuncs.BLANK),
        ("invert", StreamerFuncs.INVERT),
        ("whiten", StreamerFuncs.WHITEN),
        ("off", StreamerFuncs.NOOP),
    ])

class RainbowOptions:
    default = make_option("rainbow", FRACS + SINES + ONE_ZERO)

class FlashOptions:
    default = ("flash", FRACS + QUARTER_SINES + ONE_ZERO)

class FlickerOptions:
    default = ("flicker", FRACS + QUARTER_SINES + ONE_ZERO)

class FlitterOptions:
    default = ("flitter", FRACS + QUARTER_SINES + ONE_ZERO)

class FluxOptions:
    default = ("flux", FRACS + BOUNCES + ONE_ZERO)

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
        ("1x\u21bb\u21ba x1", Curve(easeInOutSine, [(0, 0), (15, -1), (30, 0), (45, 1), (60, 0)])),
        ("1x\u21ba\u21bb x1", Curve(easeInOutSine, [(0, 0), (15, 1), (30, 0), (45, -1), (60, 0)])),
        ("2x\u21bb\u21ba x1", Curve(easeInOutSine, [(0, 0), (7.5, -1), (15, 0), (22.5, 1), (30, 0)])),
        ("2x\u21ba\u21bb x1", Curve(easeInOutSine, [(0, 0), (7.5, 1), (15, 0), (22.5, -1), (30, 0)])),
        ("1x\u21bb\u21ba x2", Curve(easeInOutSine, [(0, 0), (15, -2), (30, 0), (45, 2), (60, 0)])),
        ("1x\u21ba\u21bb x2", Curve(easeInOutSine, [(0, 0), (15, 2), (30, 0), (45, -2), (60, 0)])),
        ("2x\u21bb\u21ba x2", Curve(easeInOutSine, [(0, 0), (7.5, -2), (15, 0), (22.5, 2), (30, 0)])),
        ("2x\u21ba\u21bb x2", Curve(easeInOutSine, [(0, 0), (7.5, 2), (15, 0), (22.5, -2), (30, 0)])),
        ("off", 0),
    ])

class SparkleOptions:
    default = ("sparkles", FRACS + [
        ("L\u21c5 6",  Curve(easeInOutSine, [(0, 0.00), (3, 0.50), (6, 0.00)])),
        ("L\u21f5 6",  Curve(easeInOutSine, [(0, 0.50), (3, 0.00), (6, 0.50)])),
        ("M\u21c5 6",  Curve(easeInOutSine, [(0, 0.25), (3, 0.50), (6, 0.25)])),
        ("M\u21f5 6",  Curve(easeInOutSine, [(0, 0.50), (3, 0.25), (6, 0.50)])),
        ("H\u21c5 6",  Curve(easeInOutSine, [(0, 0.25), (3, 0.75), (6, 0.25)])),
        ("H\u21f5 6",  Curve(easeInOutSine, [(0, 0.75), (3, 0.25), (6, 0.75)])),
        ("L\u21c5 12", Curve(easeInOutSine, [(0, 0.00), (6, 0.50), (12, 0.00)])),
        ("L\u21f5 12", Curve(easeInOutSine, [(0, 0.50), (6, 0.00), (12, 0.50)])),
        ("M\u21c5 12", Curve(easeInOutSine, [(0, 0.25), (6, 0.50), (12, 0.25)])),
        ("M\u21f5 12", Curve(easeInOutSine, [(0, 0.50), (6, 0.25), (12, 0.50)])),
        ("H\u21c5 12", Curve(easeInOutSine, [(0, 0.25), (6, 0.75), (12, 0.25)])),
        ("H\u21f5 12", Curve(easeInOutSine, [(0, 0.75), (6, 0.25), (12, 0.75)])),
        ("L\u21c5 30", Curve(easeInOutSine, [(0, 0.00), (15, 0.50), (30, 0.00)])),
        ("L\u21f5 30", Curve(easeInOutSine, [(0, 0.50), (15, 0.00), (30, 0.50)])),
        ("M\u21c5 30", Curve(easeInOutSine, [(0, 0.25), (15, 0.50), (30, 0.25)])),
        ("M\u21f5 30", Curve(easeInOutSine, [(0, 0.50), (15, 0.25), (30, 0.50)])),
        ("H\u21c5 30", Curve(easeInOutSine, [(0, 0.25), (15, 0.75), (30, 0.25)])),
        ("H\u21f5 30", Curve(easeInOutSine, [(0, 0.75), (15, 0.25), (30, 0.75)])),
        ("off", 0),
    ])
    
# Done: flash, flicker, flitter, flux, sparkle
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


# Done: repeats, delay, rainbow, spin, streamer, sparkle
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

        
# Done: rainbow, spin, repeat, spirals, split, width
class CoiledSpring(ControllablePattern):
    def __init__(self):
        self._rainbow = 1
        self._repeats = 3
        self._split = 0.25
        self._width = 0.1
        self._spirals = 2

        self.controls = [
            RainbowOptions.default,
            SpinOptions.default,
            ("repeats", INTS28),
            ("spirals", HALVES053),
            ("split", FRACS),
            ("width", FRACS),
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
                    (15, -self._spirals),
                    (30, self._spirals)]),
                "length": 2.0,
                "width": self._width / self._repeats,
                "lifetime": 2.0,
                "func": setcolor_streamer(h=i * (self._rainbow / 4), w=0, s=1, l=0.0),
            } for i in range(self._repeats)
        ] for o in range(4)])


# Done: sparkle, rainbow, intensity, delay, direction
class Confetti(ControllablePattern):
    def __init__(self):
        self._delay = 0.25
        self._direction = "FROM_TOP"
        self._intensity = "low"
        self._rainbow = 1.0

        self.controls = [
            RainbowOptions.default,
            FlickerOptions.default,
            FlitterOptions.default,
            FluxOptions.default,
            ("direction", [
                ("\u2193", Direction.FROM_TOP),
                ("\u2191", Direction.FROM_BOT),
                ("\u21c5", "BOTH"),
            ]),
            ("intensity", [("low", "low"), ("medium", "medium"), ("high", "high")]),
            make_option("delay", [0.25, 0.5, 0.75, 1]),
            SparkleOptions.default,
            SparkleFuncOptions.default,
        ]

        super(Confetti, self).__init__(
            "Confetti",
            sparkles=0,
            streamers=[],
        )
    
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


# Done: colors, fade, flux, sparkle, streamers
class FallingSnow(ControllablePattern):
    def __init__(self):
        self._colors = 8
        self._fade = easeInOutCubic
        
        self.controls = [
            make_option("colors", [6, 8, 10, 12, 16]),
            FluxOptions.default,
            FlitterOptions.default,
            ("fade", [
                ("solid", 0.0),
                ("linear", Curve(linear, [(0, 0), (1, -1)])),
                ("reverse", Curve(linear, [(0, -1), (1, 0)])),
                ("ioSine", Curve(easeInOutSine, [(0, -1), (0.5, 0), (1, -1)])),
                ("oiSine", Curve(easeInOutSine, [(0, 0), (0.5, -1), (1, 0)])),
                ("ioCubic", Curve(easeInOutCubic, [(0, -1), (0.5, 0), (1, -1)])),
                ("oiCubic", Curve(easeInOutCubic, [(0, 0), (0.5, -1), (1, 0)])),
                ("ioBounce", Curve(easeInOutBounce, [(0, -1), (0.5, 0), (1, -1)])),
                ("oiBounce", Curve(easeInOutBounce, [(0, 0), (0.5, -1), (1, 0)])),
                ("ioElastic", Curve(easeInOutElastic, [(0, -1), (0.5, 0), (1, -1)])),
                ("oiElastic", Curve(easeInOutElastic, [(0, 0), (0.5, -1), (1, 0)])),
            ]),
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
    

# Done: sparkle, wobble, spins, spirals, speed, width
class Galaxus(ControllablePattern):
    def __init__(self):
        self._speed = 2
        self._spins = 3
        self._spirals = 6
        self._width = 0.1
        self._wobble = 0.25

        self.controls = [
            FluxOptions.default,
            ("spirals", INTS28),
            ("speed", HALVES056),
            ("wobble", FRACS + ONE_ZERO),
            ("width", FRACS + ONE_ZERO),
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


# Done: rainbow, distortion, mid_distortion, mirrors, sparkle
class Groovy(ControllablePattern):
    def __init__(self):
        self._rainbow = 1/8
        self._distortion = 0.5
        self._mid_distortion = 0.5
        self._mirrors = 2

        self.controls = [
            RainbowOptions.default,
            FlitterOptions.default,
            FlickerOptions.default,
            FluxOptions.default,
            ("distortion", FRACS),
            ("mid_distortion", FRACS),
            ("mirrors", INTS28),
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
    def mirrors(self):
        return self._mirrors

    @mirrors.setter
    def mirrors(self, mirrors):
        self._mirrors = mirrors
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
            MirrorTopology(self._mirrors),
        ]
    

# Done: rainbow, flitter, flux, spin, repeats, spiral
class Rainbro(ControllablePattern):
    def __init__(self):
        self._spirals = 2
        self._rainbow = 1
        self._repeats = 0

        self.controls = [
            RainbowOptions.default,
            FlitterOptions.default,
            FluxOptions.default,
            SpinOptions.default,
            ("repeats", [("jumble", 0)] + INTS28),
            ("spirals", HALVES053),
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
    def spirals(self):
        return self._spirals

    @spirals.setter
    def spirals(self, spirals):
        self._spirals = spirals
        self.update_values()

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
        self.spiral = Curve(easeInOutSine, [
            (0, -self._spirals),
            (7.5, self._spirals),
            (15, -self._spirals),
        ])
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


# Done: rainbow, flux, sparkle, speed, mirror, streamers
class SlidingDoor(ControllablePattern):
    def __init__(self):
        self._mirror = 0
        self._rainbow = 0
        self._speed = 1

        self.controls = [
            RainbowOptions.default,
            FluxOptions.default,
            ("mirror", [("jumble", 0), INTS28]),
            ("speed", INTS26),
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
                setcolor_streamer(h=0.25, l=0, make_white=True),
                setcolor_streamer(h=-0.25, l=0.75, make_white=True),
            ]
        ]
        return combined_choices([
            streamer_choices(3, streamers[0]),
            streamer_choices(3, streamers[1]),
        ])
        

# Done: flux, spin, sparkle, spread, mirror, speed, spirals
class SpiralTop(ControllablePattern):
    def __init__(self):
        self._mirror = 2
        self._speed = 1
        self._spirals = 1

        self.controls = [
            FluxOptions.default,
            SpinOptions.default,
            SparkleOptions.default,
            ("spread", FRACS),
            ("mirror", INTS28),
            ("speed", INTS16),
            ("spirals", HALVES053),
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


# Done: spin, sparkle, rainbow, delay, splits, repeats, flux
class TurningWindows(ControllablePattern):
    def __init__(self, splits=8, repeats=4):
        self._delay = 0.25
        self._splits = 8
        self._repeats = 4
        self._rainbow = 1

        self.controls = [
            SpinOptions.default,
            SparkleOptions.default,
            RainbowOptions.default,
            FluxOptions.default,
            ("delay", QUARTERS),
            ("splits", INTS28),
            ("repeats", INTS18),
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


# Done: spin, rainbow, flux, repeats, splits, spiral, streamer_func
class TwistedRainbows(ControllablePattern):
    def __init__(self):
        self._repeats = 0
        self._rainbow = 1
        self._splits = 3
        self._streamer_func = StreamerFuncs.WHITEN

        self.controls = [
            SpinOptions.default,
            RainbowOptions.default,
            FluxOptions.default,
            ("repeats", [("jumble", 0)] + INTS28),
            ("splits", INTS28),
            ("spiral", [
                ("stepped", Curve(const, [
                    (0, -3), (3, 3),
                    (9, -1.5), (15, 1.5),
                    (21, -0.5), (27, 0.5),
                    (33, -1), (39, 1),
                    (45, -2), (51, 2),
                    (57, -3), (60, -3)
                ])),
                ("flip0.5", Curve(const, [(0, -0.5), (3, 0.5), (9, -0.5), (12, -0.5)])),
                ("flip1", Curve(const, [(0, -1), (3, 1), (9, -1), (12, -1)])),
                ("flip1.5", Curve(const, [(0, -1.5), (3, 1.5), (9, -1.5), (12, -1.5)])),
                ("flip2", Curve(const, [(0, -2), (3, 2), (9, -2), (12, -2)])),
                ("flip3", Curve(const, [(0, -3), (3, 3), (9, -3), (12, -3)])),
            ]),
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
    ]
    animation = Blender(patterns)
    animation_thread, draw_menu = get_thread_and_menu(animation)
    animation_thread.start()
    curses.wrapper(draw_menu)
    animation_thread.join()
