from pytweening import (
    linear,
    easeInSine,
    easeOutSine,
    easeInOutSine,
    easeInBounce,
    easeOutBounce,
    easeInOutBounce,
    easeInQuad,
    easeOutQuad,
    easeInOutQuad,
)
import random
from typing import Callable
from colors import (
    Color,
    ColorFuncs,
    BaseColor,
    SplitColor,
    WindowColor,
    FallingColor,
    periodic_choices,
)
from param import (
    Curve,
    Param,
    const,
    rand,
    choice,
)
from streamer import (
    Direction,
    Spin,
    StreamerFunc,
    RandomColorStreamerFunc,
    StreamerValue,
    StreamerParam,
    StreamerChoices,
    CombinedChoices,
)
from topologies import (
    SpiralTopology,
    Topology,
    DistortTopology,
    MirrorTopology,
    RepeatTopology,
)
from utils import (mk_bounce, mk_bump)

class Option:
    def __init__(self, name: str, value):
        self.name = name
        self.value = value

    def __repr__(self) -> str:
        return f"{self.name}:{self.value}"

ZERO = [Option("0", 0)]
FRACS = [Option(n, v) for n, v in [
    ("1/8", 1/8),
    ("1/6", 1/6),
    ("1/5", 1/5),
    ("1/4", 1/4),
    ("1/3", 1/3),
    ("1/2", 1/2),
    ("2/3", 2/3),
    ("3/4", 3/4),
    ("1",   1),
]]
INTS16 = [Option(str(v), v) for v in range(1, 7)]
INTS26 = INTS16[1:] 
INTS18 = [Option(str(v), v) for v in range(1, 9)]
INTS28 = INTS18[1:]
HALVES053 = [Option(str(v * 0.5), v * 0.5) for v in range(1, 7)]
HALVES056 = HALVES053 + [Option(str(v), v) for v in range(4, 7)]
DIRECTIONS = [Option("\u21ba ", 1), Option("\u21bb ", -1)]
PERIODS = [Option(str(v), v) for v in [3, 5, 6, 10, 12, 15, 20, 30, 60]]
CURVES = [Option(n, f) for n, f in [
    ("linear", linear),
    ("sineI", easeInSine),
    ("sineO", easeOutSine),
    ("sineIO", easeInOutSine),
    ("quadI", easeInQuad),
    ("quadO", easeOutQuad),
    ("quadIO", easeInOutQuad),
    ("bounceI", easeInBounce),
    ("bounceO", easeOutBounce),
    ("bounceIO", easeInOutBounce),
]]

class Control:
    def __init__(self, name: str, options: list[Option]):
        self.name = name
        self.options = options
        self.selected_idx = 0
        self.selected = options[0]

    def set(self, idx: int):
        self.selected_idx = idx % len(self.options)
        self.selected = self.options[self.selected_idx]

    def change(self, step: int=1):
        self.set(self.selected_idx + step)

    def randomize(self):
        idx = random.randint(0, len(self.options) - 1)
        self.set(idx)

    @property
    def value(self):
        return self.selected.value

    def __repr__(self) -> str:
        return f"{self.name}({self.selected})"

class ToggleControl(Control):
    def __init__(self, name: str):
        super(ToggleControl, self).__init__(name, [Option("On", True), Option("Off", False)])

class Feature:
    def __init__(self, name: str, controls: list[Control]):
        self.name = name
        self.controls = controls

    @property
    def value(self) -> dict:
        return {}

    def visible_controls(self) -> list[Control]:
        return self.controls

    def randomize(self):
        for control in self.controls:
            control.randomize()

    def change(self, idx: int, step: int=1):
        try:
            self.visible_controls()[idx].change(step)
        except Exception as ex:
            print(idx, len(self.visible_controls()), True)
            raise ex

    def set(self, cidx: int, oidx: int):
        try:
            self.visible_controls()[cidx].set(oidx)
        except Exception:
            raise ValueError(f"{cidx}, {len(self.visible_controls())}")

class BumpFeature(Feature):
    def __init__(self,
                 name: str,
                 attr_name: str):
        self.attr_name = attr_name
        self._enabled = ToggleControl("Enabled")
        self._start = Control("Start", ZERO + FRACS)
        self._end = Control("End", ZERO + FRACS)
        self._curved = ToggleControl("Curved")
        self._curve = Control("Curve", CURVES)
        self._period = Control("Period", PERIODS)

        super(BumpFeature, self).__init__(name, [
            self._enabled,
            self._start,
            self._end,
            self._curved,
            self._curve,
            self._period,
        ])

    @property
    def value(self) -> dict:
        if not self._enabled.value:
            val = 0
        elif not self._curved.value:
            val = self._start.value
        else:
            val = Curve(self._curve.value, mk_bump(
                self._period.value,
                self._start.value,
                self._end.value,
            ))
        return {self.attr_name: val}

    def visible_controls(self) -> list[Control]:
        if not self._enabled.value:
            return self.controls[:1]
        if not self._curved.value:
            return [self._enabled, self._start, self._curved]
        else:
            return self.controls

class BounceFeature(Feature):
    def __init__(self,
                 name: str,
                 attr_name: str):
        self.attr_name = attr_name
        self._enabled = ToggleControl("Enabled")
        self._curved = ToggleControl("Curved")
        self._curve = Control("Curve", CURVES)
        self._period = Control("Period", PERIODS)
        self._value = Control("Value", FRACS)

        super(BounceFeature, self).__init__(name, [
            self._enabled,
            self._value,
            self._curved,
            self._curve,
            self._period,
        ])

    @property
    def value(self) -> dict:
        if not self._enabled.value:
            val = 0
        elif not self._curved.value:
            val = self._value.value
        else:
            val = Curve(self._curve.value, mk_bounce(
                self._period.value,
                self._value.value,
            ))
        return {self.attr_name: val}

    def visible_controls(self):
        if not self._enabled.value:
            return self.controls[:1]
        if not self._curved.value:
            return [self._enabled, self._value, self._curved]
        else:
            return self.controls

class FlashFeature(BumpFeature):
    def __init__(self):
        super(FlashFeature, self).__init__("Flash", "flash")

class FlickerFeature(BumpFeature):
    def __init__(self):
        super(FlickerFeature, self).__init__("Flicker", "flicker")

class FlitterFeature(BumpFeature):
    def __init__(self):
        super(FlitterFeature, self).__init__("Flitter", "flitter")

class FluxFeature(BounceFeature):
    def __init__(self):
        super(FluxFeature, self).__init__("Flux", "flux")

class SparklesFeature(Feature):
    def _mk_sparkle(self,
                    w: float | None=None,
                    h: float | None=None,
                    s: float | None=None,
                    l: float | None=None,
                    make_white: bool=False):
        def func(color: Color) -> Color:
            if color.l != -1.0 and make_white:
                return Color(w=0.75, s=0.0, l=-0.75)
            return Color(
                w=w if w is not None else color.w,
                h=h if h is not None else color.h,
                s=s if s is not None else color.s,
                l=l if l is not None else color.l,
            )
        return func

    def random_sparkle(self, color: Color) -> Color:
        return Color(
            w=color.w,
            h=color.h + rand(-0.5, 0.5)(0),
            s=color.s,
            l=color.l,
        )

    def rainbow_sparkle(self, color: Color) -> Color:
        if self.rainbow is None:
            return color
        return Color(
            w=color.w,
            h=color.h + rand(-self.rainbow.value / 2, self.rainbow.value / 2)(0),
            s=color.s,
            l=color.l,
        )

    def flux_sparkle(self, color: Color) -> Color:
        if self.flux is None:
            return color
        return Color(
            w=color.w,
            h=color.h + rand(-self.flux._value.value / 2, self.flux._value.value / 2)(0),
            s=color.s,
            l=color.l,
        )

    def __init__(self, rainbow: Control | None=None, flux: FluxFeature | None=None):
        self.rainbow = rainbow
        self.flux = flux
        effects = [
            ("base", self._mk_sparkle(l=0)),
            ("base_whiten", self._mk_sparkle(l=0, make_white=True)),
            ("blank", self._mk_sparkle(l=-1)),
            ("invert", self._mk_sparkle(h=0.5, l=0)),
            ("invert_whiten", self._mk_sparkle(h=0.5, l=0, make_white=True)),
            ("whiten", self._mk_sparkle(w=0.75, s=0, l=-0.75)),
            ("random", self.random_sparkle),
        ]
        if self.rainbow is not None:
            effects.append(("Rainbow", self.rainbow_sparkle))
        if self.flux is not None:
            effects.append(("Flux", self.flux_sparkle))

        self._enabled = ToggleControl("Enabled")
        self._curved = ToggleControl("Curved")
        self._curve = Control("Curve", CURVES)
        self._period = Control("Period", PERIODS)
        self._start = Control("Start", ZERO + FRACS)
        self._end = Control("End", ZERO + FRACS)
        self._effect = Control("Effect", [Option(n, v) for n, v in effects]) 

        super(SparklesFeature, self).__init__("Sparkles", [
            self._enabled,
            self._start,
            self._end,
            self._curved,
            self._curve,
            self._period,
            self._effect,
        ])

    def visible_controls(self) -> list[Control]:
        if not self._enabled.value:
            return [self._enabled]
        if not self._curved.value:
            return [
                self._enabled,
                self._curved,
                self._start,
                self._effect,
            ]
        return self.controls

    @property
    def value(self) -> dict:
        if not self._enabled.value:
            sparkles = 0
        elif self._curved.value:
            sparkles = Curve(self._curve.value, mk_bump(
                self._period.value,
                self._start.value,
                self._end.value))
        else:
            sparkles = self._start.value
        return {
            "sparkles": sparkles,
            "sparkle_func": self._effect.value,
        }

    def randomize(self):
        for c in self.controls:
            c.randomize()

class SpiralFeature(Feature):
    def __init__(self):
        self._enabled = ToggleControl("Enabled")
        self._spirals = Control("Spirals", FRACS)
        self._direction = Control("Direction", DIRECTIONS)
        self._curve = Control("Curve", CURVES)
        self._period = Control("Period", PERIODS)
        
        super(SpiralFeature, self).__init__("Spiral", [
            self._enabled,
            self._spirals,
            self._direction,
            self._curve,
            self._period,
        ])

    @property
    def value(self):
        if not self._enabled.value:
            val = 0
        else:
            val = Curve(self._curve.value, mk_bounce(
                self._period.value,
                self._spirals.value * self._direction.value,
            ))
        return {"spiral": val}

    def visible_controls(self) -> list[Control]:
        if not self._enabled.value:
            return [self._enabled]
        else:
            return self.controls

class SpiralTopologyFeature(Feature):
    def __init__(self,
                 toggleable=True,
                 force_curve=False):
        self._repeats = Control("Repeats", INTS26)
        self._mirrored = ToggleControl("Mirrored")
        self._enabled = ToggleControl("Enabled")
        self._value = Control("Twists", [Option(str(v), v) for v in [
            1, 1.5, 2, 3
        ]])
        self._direction = Control("Direction", DIRECTIONS + [Option("both", "both")])
        self._mid = Control("Mid", ZERO + FRACS)
        self._curved = ToggleControl("Curved")
        self._curve = Control("Curve", CURVES)
        self._period = Control("Period", PERIODS)
        self.force_curve = force_curve
        self.toggleable = toggleable
        features = [
            self._repeats,
            self._mirrored,
            self._enabled,
            self._value,
            self._direction,
            self._mid,
            self._curved,
            self._curve,
            self._period,
        ]
        if not toggleable:
            features.remove(self._enabled)
        if not force_curve:
            features.remove(self._curved)
        
        super(SpiralTopologyFeature, self).__init__("Spiral", features)

    @property
    def value_param(self):
        if not self._enabled.value and self.toggleable:
            return 0
        if not self._curved.value and not self.force_curve:
            return self._value.value
        if self._direction.value == "both":
            return Curve(self._curve.value, mk_bounce(
                self._period.value,
                self._value.value,
                -self._value.value,
            ))
        return Curve(self._curve.value, mk_bounce(
            self._period.value,
            self._value.value * self._direction.value,
        ))

    @property
    def value(self):
        Topology = MirrorTopology if self._mirrored.value else RepeatTopology
        return {"topologies": [
            Topology(self._repeats.value),
            SpiralTopology(self.value_param, self._mid.value)
        ]}

    def visible_controls(self) -> list[Control]:
        if self.force_curve:
            curve = [self._value, self._direction, self._mid, self._curve, self._period]
        else:
            curve = [self._value, self._direction, self._mid, self._curved]
            if self._curved.value:
                curve += [self._curve, self._period]

        if self.toggleable:
            controls = [self._repeats, self._mirrored, self._enabled]
            if self._enabled.value:
                controls += curve
                controls.extend(curve)
        else:
            controls = [self._repeats, self._mirrored] + curve

        return controls

class SpinFeature(Feature):
    def __init__(self):
        self._enabled = ToggleControl("Enabled")
        self._spin = Control("Spin", ZERO + FRACS)
        self._direction = Control("Direction", DIRECTIONS)
        self._curve = Control("Curve", CURVES)
        self._period = Control("Period", PERIODS)
        
        super(SpinFeature, self).__init__("Spin", [
            self._enabled,
            self._spin,
            self._direction,
            self._curve,
            self._period,
        ])

    @property
    def value_param(self):
        if not self._enabled.value:
            return 0
        return Curve(self._curve.value, mk_bounce(
            self._period.value,
            self._spin.value * self._direction.value,
        ))

    @property
    def value(self):
        return {"spin": self.value_param}

    def visible_controls(self) -> list[Control]:
        if not self._enabled.value:
            return [self._enabled]
        else:
            return self.controls

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

class WiredPattern(Pattern):
    def __init__(self, name, **kwargs):
        super(WiredPattern, self).__init__(name, **kwargs)
        self.features: list[Feature] = []

    def update(self):
        for feature in self.features:
            for attr, val in feature.value.items():
                setattr(self, attr, val)

    def change(self, fidx: int, cidx: int, step: int=1):
        self.features[fidx].change(cidx, step)
        self.update()

    def set(self, fidx: int, cidx: int, oidx: int):
        try:
            self.features[fidx].set(cidx, oidx)
        except Exception:
            raise ValueError(f"{fidx},{cidx},{oidx}")
        self.update()

    def randomize(self):
        for c in self.features:
            c.randomize()
        self.update()
    
class RepeatTopologyFeature(Feature):
    def __init__(self):
        self._count = Control("Repeats", INTS16)
        self._mirrored = ToggleControl("Mirrored")
        super(RepeatTopologyFeature, self).__init__("Repeats", [
            self._count,
            self._mirrored,
        ])

    @property
    def value(self):
        Topology = RepeatTopology if self._mirrored.value else MirrorTopology
        return {"topologies": [Topology(self._count.value)]}

class BasicBitchFeature(Feature):
    def __init__(self):
        self._enabled = ToggleControl("Enabled")
        self._curve = Control("Curve", CURVES)
        self._period = Control("Period", PERIODS)
        self._intensity = Control("Intentsity", ZERO + HALVES056)

        super(BasicBitchFeature, self).__init__("Pulse", [
            self._enabled,
            self._curve,
            self._period,
            self._intensity,
        ])

    @property
    def value(self):
        if not self._enabled.value:
            val = BaseColor(l=0)
        else:
            val = BaseColor(l=Curve(self._curve.value, mk_bump(
                self._period.value,
                -self._intensity.value,
            )))
        return {"base_color": val}

class BasicBitch(WiredPattern):
    def __init__(self):
        self._flux = FluxFeature()
        super(BasicBitch, self).__init__("Basic Bitch")
        self.features = [
            BasicBitchFeature(),
            FlashFeature(),
            FlickerFeature(),
            FlitterFeature(),
            self._flux,
            SparklesFeature(flux=self._flux),
        ]

class CircusTentFeature(Feature):
    def __init__(self):
        self._delay = Control("Delay", [Option("0.25", 0.25)] + HALVES053)
        self._splits = Control("splits", [Option(str(v), v) for v in [2, 3, 4]])
        self._rainbow = Control("Rainbow", ZERO + FRACS)
        self._curved = ToggleControl("Rainbow Curved")
        self._curve = Control("Rainbow Curve", CURVES)
        self._period = Control("Rainbow Period", PERIODS)
        super(CircusTentFeature, self).__init__("Circus Tent", [
            self._delay,
            self._splits,
            self._rainbow,
            self._curved,
            self._curve,
            self._period,
        ])

    @property
    def value(self):
        if self._curved.value:
            rainbow = Curve(self._curve.value, mk_bounce(
                self._period.value,
                self._rainbow.value,
            ))
        else:
            rainbow = self._rainbow.value

        if self._splits.value == 2:
            fns = [[
                BaseColor(h=rainbow * 0.0, l=-1),
                BaseColor(h=rainbow * 0.5, l=0, suppress=["sparkles"]),
            ], [
                BaseColor(h=rainbow * 0.0, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow * 0.5, l=0, suppress=["sparkles"]),
            ], [
                BaseColor(h=rainbow * 0.0, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow * 0.5, l=-1),
            ], [
                BaseColor(h=rainbow * 0.0, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow * 0.5, l=0, suppress=["sparkles"]),
            ]]

        elif self._splits.value == 3:
            fns = [[
                BaseColor(h=rainbow * 1/3, l=-1),
                BaseColor(h=rainbow *   0, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow * 2/3, l=0, suppress=["sparkles"]),
            ], [
                BaseColor(h=rainbow * 1/3, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow *   0, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow * 2/3, l=0, suppress=["sparkles"]),
            ], [
                BaseColor(h=rainbow * 1/3, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow *   0, l=-1),
                BaseColor(h=rainbow * 2/3, l=0, suppress=["sparkles"]),
            ], [
                BaseColor(h=rainbow * 1/3, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow *   0, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow * 2/3, l=0, suppress=["sparkles"]),
            ], [
                BaseColor(h=rainbow * 1/3, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow *   0, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow * 2/3, l=-1),
            ], [
                BaseColor(h=rainbow * 1/3, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow *   0, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow * 2/3, l=0, suppress=["sparkles"]),
            ]]
        else:
            fns = [[
                BaseColor(h=rainbow * 0.00, l=-1),
                BaseColor(h=rainbow * 0.25, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow * 0.50, l=-1),
                BaseColor(h=rainbow * 0.75, l=0, suppress=["sparkles"]),
            ], [
                BaseColor(h=rainbow * 0.00, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow * 0.25, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow * 0.50, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow * 0.75, l=0, suppress=["sparkles"]),
            ], [
                BaseColor(h=rainbow * 0.00, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow * 0.25, l=-1),
                BaseColor(h=rainbow * 0.50, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow * 0.75, l=-1),
            ], [
                BaseColor(h=rainbow * 0.00, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow * 0.25, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow * 0.50, l=0, suppress=["sparkles"]),
                BaseColor(h=rainbow * 0.75, l=0, suppress=["sparkles"]),
            ]]
        return {
            "base_color": SplitColor(
                self._splits.value,
                periodic_choices(self._delay.value, fns),
            )}

class CircusTent(WiredPattern):
    def __init__(self):
        self._base = CircusTentFeature()
        self._flux = FluxFeature()
        super(CircusTent, self).__init__("Circus Tent")
        self.features = [
            self._base,
            SpiralTopologyFeature(),
            SpinFeature(),
            FlickerFeature(),
            FlitterFeature(),
            self._flux,
            SparklesFeature(rainbow=self._base._rainbow, flux=self._flux),
        ]

class CoiledSpringFeature(Feature):
    def __init__(self,
                 topology: SpiralTopologyFeature,
                 spin: SpinFeature):
        self.topology = topology
        self.spin = spin
        self._delay = Control("Delay", [Option(str(v), v) for v in [
            0.5, 1, 1.5, 2, 3
        ]])
        self._split = Control("Split", FRACS)
        self._split_curved = ToggleControl("Split Curved")
        self._split_curve = Control("Split Curve", CURVES)
        self._split_period = Control("Split Period", PERIODS)
        self._rainbow = Control("Rainbow", FRACS)
        self._rainbow_curved = ToggleControl("Rainbow Curved")
        self._rainbow_curve = Control("Rainbow Curve", CURVES)
        self._rainbow_period = Control("Rainbow Period", PERIODS)

        super(CoiledSpringFeature, self).__init__("Coiled Spring", [
            self._delay,
            self._split,
            self._split_curved,
            self._split_curve,
            self._split_period,
            self._rainbow,
            self._rainbow_curved,
            self._rainbow_curve,
            self._rainbow_period,
        ])

    @property
    def value(self):
        if self._split_curved.value:
            split = Curve(self._split_curve.value, mk_bump(
                self._split_period.value,
                self._split.value))
        else:
            split = self._split.value
        if self._rainbow_curved.value:
            rainbow = Curve(self._rainbow_curve.value, mk_bump(
                self._rainbow_period.value,
                self._rainbow.value))
        else:
            rainbow = self._rainbow.value

        base_color = WindowColor(1 - split, [
            BaseColor(w=0.75, s=0, l=-0.75, suppress=["sparkles", "streamers"]),
            BaseColor(),
        ])

        streamers = StreamerChoices(self._delay.value, [[StreamerValue(
            move_dir=Direction.FROM_BOT,
            spin_dir=Spin.CLOCKWISE,
            angle=(i / self.topology._repeats.value) + self.spin.value_param,
            spin=self.topology.value_param,
            length=2.0,
            width=split / self.topology._value.value,
            lifetime=self._delay.value,
            func=StreamerFunc(
                h= (i + o) * (rainbow / self.topology._value.value),
                w=0,
                s=1,
                l=0.0,
            ),
        ) for i in range(int(self.topology._value.value))] for o in range(4)])

        return {
            "base_color": base_color,
            "streamers": streamers,
        }

    def visible_controls(self) -> list[Control]:
        if self._split_curved.value:
            split = [self._split, self._split_curved, self._split_curve, self._split_period]
        else:
            split = [self._split, self._split_curved]
        if self._rainbow_curved.value:
            rainbow = [self._rainbow, self._rainbow_curved, self._rainbow_curve, self._rainbow_period]
        else:
            rainbow = [self._rainbow, self._rainbow_curved]
        return [self._delay] + split + rainbow

class CoiledSpring(WiredPattern):
    def __init__(self):
        self._topology = SpiralTopologyFeature(toggleable=False, force_curve=True)
        self._spin = SpinFeature()
        super(CoiledSpring, self).__init__("Coiled Spring")
        self.features = [
            CoiledSpringFeature(self._topology, self._spin),
            self._topology,
            self._spin,
            FlickerFeature(),
            FlitterFeature(),
            FluxFeature(),
        ]

class ConfettiFeature(Feature):
    def __init__(self):
        self._direction = Control("Direction", [Option(n, v) for n, v in [
            ("\u2193 ", [Direction.FROM_TOP]),
            ("\u2191 ", [Direction.FROM_BOT]),
            ("\u21c5 ", [Direction.FROM_TOP, Direction.FROM_TOP]),
        ]])
        self._delay = Control("Delay", [Option(str(v), v) for v in [
            0.25, 0.5, 0.75, 1.0, 1.5
        ]])
        self._min = Control("Min Streamers", [Option(str(v), v) for v in range(2)])
        self._max = Control("Max Streamers", [Option(str(v), v) for v in range(1, 5)])
        self._rainbow = Control("Rainbow", ZERO + FRACS)
        self._rainbow_curved = ToggleControl("Rainbow Curved")
        self._rainbow_curve = Control("Rainbow Curved", CURVES)
        self._rainbow_period = Control("Rainbow Period", PERIODS)
        super(ConfettiFeature, self).__init__("Confetti", [
            self._direction,
            self._delay,
            self._min,
            self._max,
            self._rainbow,
            self._rainbow_curved,
            self._rainbow_curve,
            self._rainbow_period,
        ])

    @property
    def value(self):
        if self._rainbow_curved.value:
            rainbow = Curve(self._rainbow_curve.value, mk_bounce(
                self._rainbow_period.value,
                self._rainbow.value,
                -self._rainbow.value,
            ))
        else:
            rainbow = self._rainbow.value
        streamers = CombinedChoices([
            StreamerChoices(
                self._delay.value, [[
                    StreamerValue(
                        move_dir=move_dir,
                        spin_dir=spin_dir,
                        spin=spin,
                        width=width,
                        length=choice([0.25, 0.5]),
                        lifetime=rand(3, 6),
                        func=RandomColorStreamerFunc(-rainbow / 2, rainbow / 2, w=0, s=1, l=0),
                    )
                    for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                    for spin, width in [(0.5, 0.1), (1, 0.15), (1.5, 0.2)]
                    for _ in range(4)
                ]],
                choose=(self._min.value, self._max.value))
            for move_dir in self._direction.value
        ])
        return {"streamers": streamers}
        
class Confetti(WiredPattern):
    def __init__(self):
        self._base = ConfettiFeature()
        self._flux = FluxFeature()
        super(Confetti, self).__init__("Confetti")
        self.features = [
            self._base,
            FlickerFeature(),
            FlitterFeature(),
            self._flux,
            SparklesFeature(
                rainbow=self._base._rainbow,
                flux=self._flux,
            ),
        ]

class FallingSnowFeature(Feature):
    def __init__(self):
        self._colors = Control("Colors", [Option(str(v), v) for v in [
            6, 8, 10, 12, 16,
        ]])
        self._skip = Control("Color Skip", [Option(n, v) for n, v in [
            ("1/8", 1/8),
            ("1/6", 1/6),
            ("1/4", 1/4),
            ("1/3", 1/3),
            ("3/8", 3/8),
            ("1/2", 1/2),
            ("2/3", 2/3),
            ("5/8", 5/8),
            ("3/4", 3/4),
            ("5/6", 5/6),
            ("7/8", 7/8),
        ]])
        self._fade = Control("Fade", ZERO + [Option("linear", "linear")] + CURVES)
        self._fade_direction = Control("Fade Direction", [Option(n, v) for n, v in [
            ("\u2193 ", 1),
            ("\u2191 ", -1),
        ]])

        super(FallingSnowFeature, self).__init__("Falling Snow", [
            self._colors,
            self._skip,
            self._fade,
            self._fade_direction,
        ])

    @property
    def value(self):
        if self._fade.value == 0:
            fade = self._fade.value
        elif self._fade.value == "linear":
            if self._fade_direction.value == 1:
                fade = Curve(linear, [(0, 0), (1, -1)])
            else:
                fade = Curve(linear, [(0, -1), (1, 0)])
        else:
            if self._fade_direction.value == 1:
                fade = Curve(self._fade.value, mk_bump(1, 0, -1))
            else:
                fade = Curve(self._fade.value, mk_bump(1, -1, 0))

        return {"base_color": FallingColor(
            self._colors.value,
            self._skip.value,
            fade_func=fade,
        )}

class FallingSnow(WiredPattern):
    def __init__(self):
        self._flux = FluxFeature()
        super(FallingSnow, self).__init__("Falling Snow")
        self.features = [
            FallingSnowFeature(),
            FlickerFeature(),
            FlitterFeature(),
            self._flux,
            SparklesFeature(flux=self._flux),
        ]

class GalaxusFeature(Feature):
    def __init__(self):
        self._spirals = Control("Spirals", INTS28)
        self._delay = Control("Delay", HALVES056)
        self._width = Control("Width", FRACS)
        self._width_curved = ToggleControl("Width Curved")
        self._width_curve = Control("Width Curve", CURVES)
        self._width_period = Control("Width Period", PERIODS)
        self._rainbow = Control("Rainbow", FRACS)
        self._rainbow_curved = ToggleControl("Rainbow Curved")
        self._rainbow_curve = Control("Rainbow Curve", CURVES)
        self._rainbow_period = Control("Rainbow Period", PERIODS)
        super(GalaxusFeature, self).__init__("Galaxus", [
            self._spirals,
            self._delay,
            self._width,
            self._width_curved,
            self._width_curve,
            self._width_period,
            self._rainbow,
            self._rainbow_curved,
            self._rainbow_curve,
            self._rainbow_period,
        ])

    @property
    def value(self):
        if self._width_curved.value:
            width = Curve(self._width_curve.value, mk_bump(
                self._width_period.value,
                self._width.value,
            ))
        else:
            width = self._width.value
        if self._rainbow_curved.value:
            rainbow = Curve(self._rainbow_curve.value, mk_bump(
                self._rainbow_period.value,
                self._rainbow.value,
            ))
        else:
            rainbow = self._rainbow.value

        funcs = [StreamerFunc(l=0, ignore_color=True, h=Curve(
            self._rainbow_curve.value,
            mk_bounce(self._rainbow_period.value, 0, i * rainbow)
        )) for i in [1, -1]]
        streamers = [
            [
                [
                    StreamerValue(
                        move_dir=move_dir,
                        spin_dir=spin_dir,
                        angle=offset + (i / self._spirals.value) + (o / (self._spirals.value ** 2)),
                        spin=0.5,
                        length=1.5,
                        width=width / self._spirals.value,
                        lifetime=1.5 * self._delay.value,
                        func=func,
                    ) for i in range(self._spirals.value)
                ]
                for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                for o in range(self._spirals.value)
            ] for move_dir, offset, func in zip(
                [Direction.FROM_BOT, Direction.FROM_TOP],
                [0, 0.5 / self._spirals.value],
                funcs,
            )
        ]
        return {"streamers": CombinedChoices([
            StreamerChoices(self._delay.value, streamers[0]),
            StreamerChoices(self._delay.value, streamers[1],
                             delay_offset=self._delay.value / 2),
        ])}

    def visible_controls(self) -> list[Control]:
        if not self._width_curved.value:
            width = [self._width, self._width_curved]
        else:
            width = [self._width, self._width_curved, self._width_curve, self._width_period]
        if not self._rainbow_curved.value:
            rainbow = [self._rainbow, self._rainbow_curved]
        else:
            rainbow = [self._rainbow, self._rainbow_curved, self._rainbow_curve, self._rainbow_period]

        return [self._spirals, self._delay] + width + rainbow

class Galaxus(WiredPattern):
    def __init__(self):
        self._base = GalaxusFeature()
        self._flux = FluxFeature()
        super(Galaxus, self).__init__("Galaxus")
        self.features = [
            GalaxusFeature(),
            FlickerFeature(),
            FlitterFeature(),
            self._flux,
            SparklesFeature(
                rainbow=self._base._rainbow,
                flux=self._flux,
            ),
        ]

class GroovyFeature(Feature):
    def __init__(self):
        self._distort = Control("Distort", FRACS[:-3])
        self._distort_curved = ToggleControl("Distort Curved")
        self._distort_curve = Control("Distort Curve", CURVES)
        self._distort_period = Control("Distort Period", PERIODS[2:])
        self._distort_mid = Control("Distort Mid", FRACS[:-3])
        self._distort_mid_curved = ToggleControl("Distort Mid Curved")
        self._distort_mid_curve = Control("Distort Mid Curve", CURVES)
        self._distort_mid_period = Control("Distort Mid Period", PERIODS[2:])
        self._rainbow = Control("Rainbow", FRACS)
        self._rainbow_curved = ToggleControl("Rainbow Curved")
        self._rainbow_curve = Control("Rainbow Curve", CURVES)
        self._rainbow_period = Control("Rainbow Period", PERIODS)

        super(GroovyFeature, self).__init__("Groovy", [
            self._distort,
            self._distort_curve,
            self._distort_period,
            self._distort_mid,
            self._distort_mid_curve,
            self._distort_mid_period,
            self._rainbow,
            self._rainbow_curved,
            self._rainbow_curve,
            self._rainbow_period,
        ])

    @property
    def value(self):
        distort = Curve(self._distort_curve.value, mk_bounce(
            self._distort_period.value,
            self._distort.value,
            -self._distort.value,
        ))
        distort_mid = Curve(self._distort_mid_curve.value, mk_bounce(
            self._distort_mid_period.value,
            -self._distort_mid.value,
        ))
        if self._rainbow_curved.value:
            rainbow = Curve(self._rainbow_curve.value, mk_bounce(
                self._rainbow_period.value,
                -self._rainbow.value,
            ))
        else:
            rainbow = self._rainbow.value
        return {
            "base_color": SplitColor(6, [
                BaseColor(h=-rainbow, l=0.0, spread=False, suppress=["sparkles"]),
                BaseColor(l=-1),
                BaseColor(l=0.0, spread=False, suppress=["sparkles"]),
                BaseColor(l=0.0, spread=False, suppress=["sparkles"]),
                BaseColor(l=-1),
                BaseColor(h=rainbow, l=0.0, spread=False, suppress=["sparkles"]),
            ]),
            "topologies": [
                DistortTopology(
                    self._distort_curve.value,
                    distort,
                    -distort,
                    distort_mid,
                ),
                MirrorTopology(2),
            ],
        }

    def visible_controls(self) -> list[Control]:
        if not self._rainbow_curved.value:
            return [
                self._distort,
                self._distort_curve,
                self._distort_period,
                self._distort_mid,
                self._distort_mid_curve,
                self._distort_mid_period,
            ] + [
                self._rainbow,
                self._rainbow_curved
            ]
        else:
            return self.controls

class Groovy(WiredPattern):
    def __init__(self):
        self._base = GroovyFeature() 
        self._flux = FluxFeature()
        super(Groovy, self).__init__("Groovy")
        self.features = [
            self._base,
            FlickerFeature(),
            FlitterFeature(),
            self._flux,
            SparklesFeature(
                rainbow=self._base._rainbow,
                flux=self._flux,
            ),
        ]

class RainbowStormFeature(Feature):
    def __init__(self):
        self._fade = Control("Fade", ZERO + [Option("linear", "linear")] + CURVES)
        self._fade_direction = Control("Fade Direction", [Option(n, v) for n, v in [
            ("\u2193 ", 1),
            ("\u2191 ", -1),
        ]])
        self._period0 = Control("Period0", PERIODS)
        self._period1 = Control("Period1", PERIODS)
        self._period2 = Control("Period2", PERIODS)
        self._period3 = Control("Period3", PERIODS)
        self._rainbow = Control("Rainbow", FRACS)
        self._rainbow_curved = ToggleControl("Rainbow Curved")
        self._rainbow_curve = Control("Rainbow Curve", CURVES)
        self._rainbow_period = Control("Rainbow Period", PERIODS)
        super(RainbowStormFeature, self).__init__("Rainbow Storm", [
            self._fade,
            self._fade_direction,
            self._period0,
            self._period1,
            self._period2,
            self._rainbow,
            self._rainbow_curved,
            self._rainbow_curve,
            self._rainbow_period,
        ])

    @property
    def value(self):
        if self._fade.value == 0:
            fade = self._fade.value
        elif self._fade.value == "linear":
            if self._fade_direction.value == 1:
                fade = Curve(linear, [(0, 0), (1, -1)])
            else:
                fade = Curve(linear, [(0, -1), (1, 0)])
        else:
            if self._fade_direction.value == 1:
                fade = Curve(self._fade.value, mk_bump(1, 0, -1))
            else:
                fade = Curve(self._fade.value, mk_bump(1, -1, 0))
            
        if self._rainbow_curved.value:
            rainbow = Curve(self._rainbow_curve.value, mk_bounce(
                self._rainbow_period.value,
                self._rainbow.value,
                -self._rainbow.value
            )) / 2
        else:
            rainbow = self._rainbow.value / 2
        return {
            "base_color": SplitColor(3, [
                FallingColor(8, 3/8, period=self._period0.value, fade_func=fade),
                FallingColor(12, 5/12, period=self._period1.value,
                             hue_func=rainbow,
                             fade_func=fade),
                FallingColor(16, 7/16, period=self._period2.value,
                             hue_func=-rainbow,
                             fade_func=fade),
            ])
        }

    def visible_controls(self) -> list[Control]:
        if not self._rainbow_curved.value:
            return self.controls[:-3]
        else:
            return self.controls
    
class RainbowStorm(WiredPattern):
    def __init__(self):
        self._base = RainbowStormFeature()
        self._flux = FluxFeature()
        super(RainbowStorm, self).__init__("Rainbow Storm")
        self.features = [
            self._base,
            SpiralTopologyFeature(),
            SpinFeature(),
            FlickerFeature(),
            FlitterFeature(),
            self._flux,
            SparklesFeature(
                rainbow=self._base._rainbow,
                flux=self._flux,
            ),
        ]

class SlidingDoorFeature(Feature):
    def __init__(self):
        self._window_curve = Control("Window Curve", CURVES)
        self._window_period = Control("Window Period", PERIODS)
        self._rainbow = Control("Rainbow", FRACS)
        self._rainbow_curved = ToggleControl("Rainbow Curved")
        self._rainbow_curve = Control("Rainbow Curve", CURVES)
        self._rainbow_period = Control("Rainbow Period", PERIODS)
        self._streamers = ToggleControl("Streamers")
        self._streamer_delay = Control("Streamer Delay", HALVES056)
        super(SlidingDoorFeature, self).__init__("Sliding Door", [
            self._window_curve,
            self._window_period,
            self._rainbow,
            self._rainbow_curved,
            self._rainbow_curve,
            self._rainbow_period,
            self._streamers,
            self._streamer_delay,
        ])

    @property
    def value(self):
        window = Curve(self._window_curve.value, mk_bump(
            self._window_period.value, 1))

        if self._rainbow_curved.value:
            rainbow = Curve(self._rainbow_curve.value, mk_bounce(
                self._rainbow_period.value,
                self._rainbow.value,
                -self._rainbow.value,
            ))
            spread = Curve(self._rainbow_curve.value, mk_bump(
                self._rainbow_period.value,
                self._rainbow.value / 2,
                -self._rainbow.value / 2,
            ))
        else:
            rainbow = self._rainbow.value
            spread = self._rainbow.value / 2
            
        if self._streamers.value:
            s = [
                [
                    [
                        StreamerValue(
                            move_dir=move_dir,
                            spin_dir=spin_dir,
                            spin=Curve(const, mk_bump(self._streamer_delay.value * 2, 1, 0.5)),
                            length=1.0,
                            width=Curve(const, mk_bump(self._streamer_delay.value * 2, 0.1, 0.15)),
                            lifetime=2 * self._streamer_delay.value,
                            func=func,
                        ) for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                    ] for move_dir in [Direction.FROM_BOT, Direction.FROM_TOP]
                ] for func in [
                    StreamerFunc(h=rainbow * 0.25, l=0, make_white=True),
                    StreamerFunc(h=-rainbow * 0.25, l=0.75, make_white=True),
                ]
            ]
            streamers = CombinedChoices([
                StreamerChoices(self._streamer_delay.value, s[0]),
                StreamerChoices(self._streamer_delay.value, s[1]),
            ])
        else:
            streamers = []
        
        return {
            "base_color": WindowColor(window, [
                BaseColor(spread=False),
                BaseColor(h=rainbow, l=0, suppress=["sparkles", "streamers"], spread=False),
            ]),
            "spread": spread,
            "streamers": streamers,
        }

    def visible_controls(self) -> list[Control]:
        window = [self._window_curve, self._window_period]
        if not self._rainbow_curved.value:
            rainbow = [
                self._rainbow,
                self._rainbow_curved,
                self._rainbow_curve,
                self._rainbow_period,
            ]
        else:
            rainbow = [
                self._rainbow,
                self._rainbow_curved,
                self._rainbow_curve,
                self._rainbow_period,
            ]
        if not self._streamers.value:
            streamers = [self._streamers]
        else:
            streamers = [self._streamers, self._streamer_delay]
        return window + rainbow + streamers

class SlidingDoor(WiredPattern):
    def __init__(self):
        self._base = SlidingDoorFeature()
        self._flux = FluxFeature()
        super(SlidingDoor, self).__init__("Sliding Door")
        self.features = [
            self._base,
            SpiralTopologyFeature(),
            SpinFeature(),
            FlickerFeature(),
            FlitterFeature(),
            self._flux,
            SparklesFeature(
                rainbow=self._base._rainbow,
                flux=self._flux,
            ),
        ]

class SpiralTopFeature(Feature):
    def __init__(self):
        self._window_period = Control("Window Period", PERIODS[:6])
        self._window_curve = Control("Window Curve", CURVES)
        self._spread = Control("Spread", FRACS[1:-1])
        super(SpiralTopFeature, self).__init__("Spiral Top", [
            self._window_period,
            self._window_curve,
            self._spread,
        ])

    @property
    def value(self):
        return {
            "base_color": WindowColor(Curve(self._window_curve.value, [
                (0, 0),
                (self._window_period.value, 1),
            ])),
            "spread": self._spread.value,
        }

class SpiralTop(WiredPattern):
    def __init__(self):
        self._base = SpiralTopFeature() 
        self._flux = FluxFeature()
        super(SpiralTop, self).__init__("Spiral Top")
        self.features = [
            self._base,
            SpiralTopologyFeature(toggleable=False, force_curve=True),
            SpinFeature(),
            FlickerFeature(),
            FlitterFeature(),
            self._flux,
            SparklesFeature(
                rainbow=self._base._spread,
                flux=self._flux,
            ),
        ]
