import curses

from pytweening import (
    linear,
    easeInSine,
    easeOutSine,
    easeInOutSine,
    easeOutBounce,
    easeInOutCubic,
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


# Done
class BasicBitch(ControllablePattern):
    controls = [
        ("flash", [
            ("0.25", 0.25),
            ("0.5", 0.5),
            ("0.75", 0.75),
            ("1", 1.0),
            ("Off", 0.0),
        ]),
        ("flicker", [
            ("updown:6", Curve(easeInOutSine, [(0, 0), (3, 0.5), (6, 0)])),
            ("downup:6", Curve(easeInOutSine, [(0, 0.5), (3, 0), (6, 0.5)])),
            ("updown:12", Curve(easeInOutSine, [(0, 0), (6, 0.5), (12, 0)])),
            ("downup:12", Curve(easeInOutSine, [(0, 0.5), (6, 0), (12, 0.5)])),
            ("Off", 0.0),
         ]),
        ("flitter", [
            ("updown:6", Curve(easeInOutSine, [(0, 0), (3, 0.5), (6, 0)])),
            ("downup:6", Curve(easeInOutSine, [(0, 0.5), (3, 0), (6, 0.5)])),
            ("updown:12", Curve(easeInOutSine, [(0, 0), (6, 0.5), (12, 0)])),
            ("downup:12", Curve(easeInOutSine, [(0, 0.5), (6, 0), (12, 0.5)])),
            ("Off", 0.0),
        ]),
        ("flux", [
            ("1/3:6", Curve(easeInOutSine, [(0, 0), (1.5, 1/3), (3, 0), (4.5, -1/3), (6, 0)])),
            ("2/3:6", Curve(easeInOutSine, [(0, 0), (1.5, 2/3), (3, 0), (4.5, -2/3), (6, 0)])),
            ("3/3:6", Curve(easeInOutSine, [(0, 0), (1.5, 1), (3, 0), (4.5, -1), (6, 0)])),
            ("1/3:12", Curve(easeInOutSine, [(0, 0), (3, 1/3), (6, 0), (9, -1/3), (12, 0)])),
            ("2/3:12", Curve(easeInOutSine, [(0, 0), (3, 2/3), (6, 0), (9, -2/3), (12, 0)])),
            ("3/3:12", Curve(easeInOutSine, [(0, 0), (3, 1), (6, 0), (9, -1), (12, 0)])),
            ("Off", 0.0),
        ]),
    ]
    set_controls = [
        1,
        0,
        1,
        2,
    ]

    def __init__(self):
        self._flicker_max = 0.5
        self._flicker_t = 6.0
        self._flitter_max = 0.5
        self._flitter_t = 6.0

        super(BasicBitch, self).__init__(
            "Basic Bitch",
            base_color=BaseColor(l=0),
            flash=0.0,
            flicker=0.0,
            flitter=0.0,
            flux=0.0,
        )


# Done
class CircusTent(ControllablePattern):
    @staticmethod
    def mk_streamers():
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
                        "func": StreamerFuncs.WHITEN,
                    } for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                ] for move_dir in [Direction.FROM_BOT, Direction.FROM_TOP]
            ],
        ) 

    @staticmethod
    def mk_split_funcs(delay):
        return periodic_choices(delay, [
            [
                BaseColor(h=0.25, l=-1),
                BaseColor(h=0.0, l=0, suppress=["sparkles"]),
                BaseColor(h=0.75,l=-1),
                BaseColor(h=0.5, l=0, suppress=["sparkles"]),
            ],
            [
                BaseColor(h=0.25, l=0, suppress=["sparkles"]),
                BaseColor(h=0.0, l=0, suppress=["sparkles"]),
                BaseColor(h=0.75, l=0, suppress=["sparkles"]),
                BaseColor(h=0.5, l=0, suppress=["sparkles"]),
            ],
            [
                BaseColor(h=0.25, l=0, suppress=["sparkles"]),
                BaseColor(l=-1),
                BaseColor(h=0.75, l=0, suppress=["sparkles"]),
                BaseColor(l=-1),
            ],
            [
                BaseColor(h=0.25, l=0, suppress=["sparkles"]),
                BaseColor(h=0.0, l=0, suppress=["sparkles"]),
                BaseColor(h=0.75, l=0, suppress=["sparkles"]),
                BaseColor(h=0.5, l=0, suppress=["sparkles"]),
            ],
        ]) 

    controls = [
        ("base_color", [("1.5", SplitColor(4, mk_split_funcs(1.5))), ("3", SplitColor(4, mk_split_funcs(3)))]),
        ("topologies", [("r3", [RepeatTopology(3)]), ("r4", [RepeatTopology(4)]), ("r5", [RepeatTopology(5)]), ("r6", [RepeatTopology(6)])]),
        ("spin", [
            ("1xC-CC", Curve(easeInOutSine, [(0, 0), (15, 1), (30, 0), (45, -1), (60, 0)])),
            ("1xCC-C", Curve(easeInOutSine, [(0, 0), (15, -1), (30, 0), (45, 1), (60, 0)])),
            ("2xC-CC", Curve(easeInOutSine, [(0, 0), (7.5, 1), (15, 0), (22.5, -1), (30, 0)])),
            ("2xCC-C", Curve(easeInOutSine, [(0, 0), (7.5, -1), (15, 0), (22.5, 1), (30, 0)])),
        ]),
        ("sparkles", [("0.25", 0.25), ("0.5", 0.5), ("0.75", 0.75), ("Off", 0.0)]),
        ("streamers", [("On", mk_streamers()), ("Off", [])]),
    ]
    set_controls = [
        1,
        1,
        0,
        1,
        1,
    ]

    def __init__(self):
        super(CircusTent, self).__init__(
            "Circus Tent",
            base_color=SplitColor(4, self.mk_split_funcs(1.5)),
            topologies=[RepeatTopology(4)],
            sparkles=0.5,
            spin=0.0,
            streamers=[],
        )

        
# Done
class CoiledSpring(ControllablePattern):
    @property
    def repeat(self):
        return self._repeat

    @repeat.setter
    def repeat(self, repeat):
        self._repeat = repeat
        self.update_values()

    @property
    def split(self):
        return self._split

    @split.setter
    def split(self, split):
        self._split = split
        self.update_values()

    @property
    def streamer_width(self):
        return self._streamer_width

    @streamer_width.setter
    def streamer_width(self, streamer_width):
        self._streamer_width = streamer_width
        self.update_values()

    @property
    def spirals(self):
        return self._spirals

    @spirals.setter
    def spirals(self, spirals):
        self._spirals = spirals
        self.update_values()

    def update_values(self):
        self.base_color = WindowColor(
            1 - self._split,
            [
                BaseColor(w=0.75, s=0.0, l=-0.75, suppress=["sparkles", "streamers"]),
                BaseColor(l=-1),
            ],
        )
        self.topologies = [RepeatTopology(self._repeat)]
        self.streamers = streamer_choices(
            2,
            [
                [
                    {
                        "move_dir": Direction.FROM_BOT,
                        "spin_dir": o % 2,
                        "angle": (i/4),
                        "spin": Curve(easeOutBounce, [
                            (0, -self._spirals),
                            (15, self._spirals),
                            (30, -self._spirals)]),
                        "length": 1,
                        "width": self._streamer_width,
                        "lifetime": 1.0,
                        "func": setcolor_streamer(w=0, s=1, l=0.0),
                    } for i in range(4)
                ] for o in range(4)
            ],
        )
        self.spiral=Curve(easeOutBounce, [
            (0, self._spirals),
            (15, -self._spirals),
            (30, self._spirals),
        ])

    def __init__(self):
        self._repeat = 3
        self._split = 0.25
        self._streamer_width = 0.1
        self._spirals = 2

        self.controls = [
            ("repeat", [("3", 3), ("4", 4), ("5", 5)]),
            ("split", [("0.25", 0.25), ("0.5", 0.5), ("0.75", 0.75)]),
            ("streamer_width", [("0.05", 0.05), ("0.1", 0.1), ("0.15", 0.15), ("0.2", 0.2)]),
            ("spirals", [("1", 1), ("1.5", 1.5), ("2", 2), ("2.5", 2.5), ("3", 3)]),
        ]
        self.set_controls = [
            1,
            0,
            1,
            2,
        ]

        super(CoiledSpring, self).__init__(
            "Coiled Spring",
            base_color=WindowColor(
                0.75,
                [
                    BaseColor(w=0.75, s=0.0, l=-0.75, suppress=["sparkles", "streamers"]),
                    BaseColor(h=0.5, l=-1),
                ],
            ),
            topologies=[RepeatTopology(4)],
            spiral=0,
            streamers=[]
        )


# Done
class Confetti(ControllablePattern):
    @staticmethod
    def mk_streamer_choices(move_dir, choose=(4,8)):
        return streamer_choices(1,
            [[
                {
                    "move_dir": move_dir,
                    "spin_dir": spin_dir,
                    "spin": spin,
                    "width": width,
                    "length": lambda _: choice([0.25, 0.5])(),
                    "lifetime": lambda _: rand(3, 6)(),
                    "func": setcolor_streamer(w=0, h=i/4, s=1, l=0.0),
                }
                    for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                    for spin, width in [(0.5, 0.1), (1, 0.15), (1.5, 0.2)]
                    for i in range(4)
            ]],
            choose=choose)

    @property
    def streamer_dir(self):
        return self._streamer_dir

    @streamer_dir.setter
    def streamer_dir(self, streamer_dir):
        self._streamer_dir = streamer_dir

    def update_values(self):
        if self._streamer_dir == "BOTH":
            self.streamers = combined_choices([
                self.mk_streamer_choices(Direction.FROM_TOP, (2,4)),
                self.mk_streamer_choices(Direction.FROM_BOT, (2,4)),
            ])
        else:
            self.streamers = self.mk_streamer_choices(self._streamer_dir)

    def __init__(self):
        self._move_dir = "FROM_TOP"

        self.controls = [
            ("sparkles", [("0.25", 0.25), ("0.5", 0.5), ("0.75", 0.75), ("Off", 0)]),
            ("streamer_dir", [
                ("FROM_TOP", Direction.FROM_TOP),
                ("FROM_BOT", Direction.FROM_BOT),
                ("BOTH", "BOTH"),
            ]),
        ]
        self.set_controls = [
            2,
            0,
        ]

        super(Confetti, self).__init__(
            "Confetti",
            sparkles=0,
            streamers=[],
        )
    

class FallingSnow(ControllablePattern):
    @staticmethod
    def mk_streamers():
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
                   "func": setcolor_streamer(w=0.2, h=0, l=-1),
               }
                    for move_dir in [Direction.FROM_BOT, Direction.FROM_TOP]
                    for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                    for lifetime in [3, 4.5, 6, 7.5]
                    for spin, width in [(2, 0.2), (3, 0.15)]
           ]],
           choose=(0, 1),
       ) 

    controls = [
        ("streamers", [("On", mk_streamers()), ("Off", [])])
    ]
    set_controls = [
        0,
    ]

    def __init__(self):
        super(FallingSnow, self).__init__(
            "Falling Snow",
            base_color=FallingColor(),
            flitter=0.25,
            flux=1/8,
            sparkles=Curve(easeInOutSine, [(0, 0.25), (6, 0.5), (12, 0.25)]),
            streamers=[],
        )


class Galaxus(ControllablePattern):
    @staticmethod
    def sparkle_func(color: Color) -> Color:
        if color.l == -1.0:
            return ColorFuncs.WHITEN(color)
        else:
            return color

    @staticmethod
    def mk_streamers():
        streamers = [
            [
                [
                    {
                        "move_dir": move_dir,
                        "spin_dir": spin_dir,
                        "angle": (i / 6) + (o / (6 * 3)),
                        "spin": 0.5,
                        "length": 1,
                        "width": 0.1,
                        "lifetime": 2,
                        "func": func,
                    } for i in range(6)
                ] for o in range(3)
            ] for move_dir, spin_dir, func in zip(
                [Direction.FROM_BOT, Direction.FROM_TOP],
                [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE],
                [
                    setcolor_streamer(
                        l=0,
                        h=Curve(easeInOutSine, [(0, 0), (7.5, -0.25), (15, 0), (22.5, 0.25), (30, 0)]),
                    ),
                    setcolor_streamer(
                        l=0,
                        h=Curve(easeInOutSine, [(0, 0.5), (5, 0.25), (10, 0.5), (15, 0.75), (20, 0.5)]),
                    ),
                ],
            )
        ]
        return combined_choices([
            streamer_choices(2, streamers[0]),
            streamer_choices(2, streamers[1], delay_offset=1),
        ])

    controls = [
        ("streamers", [("On", mk_streamers()), ("Off", [])])
    ]
    set_controls = [
        0
    ]

    def __init__(self):
        super(Galaxus, self).__init__(
            "Galaxus",
            sparkles=0.25,
            sparkle_func=self.sparkle_func,
            streamers=[],
        )


# Done
class Groovy(ControllablePattern):
    @property
    def color_spread(self):
        return self._color_spread

    @color_spread.setter
    def color_spread(self, color_spread):
        self._color_spread = color_spread
        self.update_values()

    @property
    def distortion(self):
        return self._distortion

    @distortion.setter
    def distortion(self, distortion):
        self._distortion = distortion
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
                        (0, self._color_spread),
                        (15, 0),
                        (30, self._color_spread),
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
                        (0, -self._color_spread),
                        (10, 0),
                        (20, -self._color_spread)]),
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
                    (5, 0.3),
                    (10, 0.5),
                    (15, 0.7),
                    (20, 0.5),
                ])
            ),
            MirrorTopology(self._mirrors),
        ]
    
    def __init__(self):
        self._color_spread = 1/8
        self._distortion = 0.5
        self._mirrors = 2

        self.controls = [
            ("color_spread", [("1/8", 1/8), ("2/8", 2/8), ("3/8", 3/8), ("4/8", 4/8)]),
            ("distortion", [("1/5", 1/5), ("1/4", 1/4), ("1/3", 1/3), ("1/2", 1/2)]),
            ("mirrors", [("2", 2), ("3", 3), ("4", 4), ("5", 5)]),
            ("sparkles", [("0.25", 0.25), ("0.5", 0.5), ("0.75", 0.75), ("Off", 0)]),
        ]
        self.set_controls = [
            0,
            3,
            0,
            0,
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


# Done
class Rainbro(ControllablePattern):
    @property
    def spirals(self):
        return self._spirals

    @spirals.setter
    def spirals(self, spirals):
        self._spirals = spirals
        self.update_values()

    @property
    def color_spread(self):
        return self._color_spread

    @color_spread.setter
    def color_spread(self, spirals):
        self._color_spread = spirals
        self.update_values()

    def update_values(self):
        self.spiral = Curve(easeInOutSine, [
            (0, -self._spirals),
            (7.5, self._spirals),
            (15, -self._spirals),
        ])
        self.spread = Curve(easeInOutSine, [
            (0, self._color_spread),
            (15, -self._color_spread),
            (30, self._color_spread),
        ])

    def __init__(self):
        self._spirals = 2
        self._color_spread = 1

        self.controls = [
            ("flux", [("1/8", 1/8), ("2/8", 2/8), ("3/8", 3/8), ("4/8", 4/8), ("Off", 0)]),
            ("spin", [("1", 1), ("2", 2), ("3", 3), ("4", 4), ("5", 5), ("6", 6), ("Off", 0)]),
            ("spirals", [("1", 1), ("2", 2), ("3", 3), ("Off", 0)]),
            ("color_spread", [("1/3", 1/3), ("1/2", 1/2), ("2/3", 2/3), ("3/4", 3/4), ("1", 1)]),
        ]
        self.set_controls = [
            0,
            5,
            1,
            4,
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
            spiral=Curve(easeInOutSine, [(0, -2), (7.5, 2), (15, -2)]),
            spread=Curve(easeInOutSine, [(0, 1), (15, -1), (30, 1)]),
        )


class SlidingDoor(ControllablePattern):
    @staticmethod
    def mk_streamers():
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
        
    controls = [
        ("streamers", [("On", mk_streamers()), ("Off", [])]),
    ]
    set_controls = [
        0,
    ]

    def __init__(self):
        super(SlidingDoor, self).__init__(
            "Sliding Door",
            base_color=WindowColor(
                Curve(easeInOutSine, [(0, 0), (3, 1), (6, 0)]),
                [
                    BaseColor(l=-1, spread=False),
                    BaseColor(
                        h=Curve(const, [(0, 0), (6, 0.5), (12, 0)]),
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


class SpiralTop(ControllablePattern):
    controls = []
    set_controls = []

    def __init__(self):
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


class TurningWindows(ControllablePattern):
    controls = []
    set_controls = []

    def __init__(self, splits=8, repeats=4):
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
            spin=Curve(easeInOutSine, [(0, 0), (15, -1), (30, 0), (45, 1), (60, 0)]),
            spread=Curve(linear, [(0, 0), (15, 3.0/splits), (30, 0), (45, -3.0/splits), (60, 0)]),
            sparkles=0.75,
        )


class TwistedRainbows(ControllablePattern):
    controls = [
    ]
    set_controls = [
    ]

    def __init__(self):
        super(TwistedRainbows, self).__init__(
            "Twisted Rainbows",
            base_color=SplitColor(3),
            topologies=[RepeatTopology(Curve(const, [
                (0, 1),
                (12, 3),
                (24, 5),
                (36, 4),
                (48, 2),
                (60, 1)
            ]))],
            spin=2.0,
            spread=Curve(easeInOutCubic, [
                (0, 1/4),
                (3, 0),
                (6, -1/4),
                (9, 0),
                (12, 1/4),
            ]),
            spiral=Curve(const, [
                (0, -3), (3, 3),
                (9, -1.5), (15, 1.5),
                (21, -0.5), (27, 0.5),
                (33, -1), (39, 1),
                (45, -2), (51, 2),
                (57, -3), (60, -3)
            ]),
            streamers=streamer_choices(
                1,
                [[
                    {
                        "move_dir": move_dir,
                        "spin_dir": spin_dir,
                        "spin": 2.0,
                        "length": 2.0,
                        "width": 0.15,
                        "lifetime": 3,
                        "func": StreamerFuncs.WHITEN,
                    }
                    for move_dir in [Direction.FROM_BOT, Direction.FROM_TOP]
                    for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                ]],
                choose=(0, 2),
            )
        )


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
    animation = Blender(
        patterns,
        start_idx=7,
        pause_change=False,
    )
    animation_thread, draw_menu = get_thread_and_menu(animation)
    animation_thread.start()
    curses.wrapper(draw_menu)
    animation_thread.join()
