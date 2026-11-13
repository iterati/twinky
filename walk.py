"""The walk, the Blender's autopilot: every so often one control of one feature steps to an option near
its own and the tree glides there; now and then a whole feature rerolls, and rarely the pattern changes.
Its live controls are Pace, Reach, Stay, a pin on each of the pattern's features, Back and Nudge."""
from collections import deque
import math
import random

from control import Control, Feature, Option, ToggleControl, WiredPattern

# the seconds between steps, or while the music's beat is sure, the bars
PACES = [Option(n, v) for n, v in [
    ("slow", (8.0, 4)),
    ("easy", (4.0, 2)),
    ("brisk", (2.0, 1)),
    ("fast", (1.0, 1)),
]]
# how many options away a step may go; at jump, the old autopilot: a freshly randomized pattern every
# pattern_length seconds
REACHES = [Option(n, v) for n, v in [
    ("near", 1),
    ("far", 3),
    ("any", math.inf),
    ("jump", None),
]]
# the share of steps that reroll a whole feature, and that change the pattern
REROLL = 0.1
CHANGE = 0.03
# the steps Back can undo
BACK_STEPS = 10

def movable(feature: Feature) -> list[int]:
    """The feature's visible controls a step can move, by their index among the visible ones."""
    return [i for i, c in enumerate(feature.visible_controls()) if len(c.options) > 1]

class Walk:
    def __init__(self):
        self.pace = Control("Pace", PACES)
        self.pace.set(1)
        self.reach = Control("Reach", REACHES)
        self.stay = ToggleControl("Stay")
        self.stay.set(1)  # Off
        self.pins: set[int] = set()  # the pattern on show's features the walk holds still, by index
        # where each step left from: the pattern, its picks by name, and whether it was changed since its save
        self.back_steps: deque[tuple[WiredPattern, dict, bool]] = deque(maxlen=BACK_STEPS)
        self.last_step = 0.0

    @property
    def jumping(self) -> bool:
        return self.reach.value is None

    def toggle_pin(self, fidx: int):
        self.pins ^= {fidx}

    def due(self, b) -> bool:
        """Whether the walk steps on the Blender's frame now. At jump, as the old autopilot, a minute
        from the pattern's start, in drive from a bar line; else Pace's seconds from the last step, or
        while the beat is sure, on every so many bar lines."""
        if self.jumping:
            since = self.last_step if self.stay.value else b.run.start
            return (b._t >= since + b.pattern_length
                    and (not b.lands_on_bars or (b.on_beat is not None and b.on_beat[0] % 4 == 0)))
        seconds, bars = self.pace.value
        if b.beating:
            return b.on_beat is not None and b.on_beat[0] % (4 * bars) == 0
        return b._t >= self.last_step + seconds

    def left(self, b) -> float:
        """The seconds to the walk's next step."""
        if self.jumping:
            since = self.last_step if self.stay.value else b.run.start
            return since + b.pattern_length - b._t
        seconds, bars = self.pace.value
        if b.beating:
            beats = 4 * bars
            return (beats - (b.sound.beat % beats)) * 60 / b.sound.bpm
        return self.last_step + seconds - b._t

    def step(self, b):
        """One step on the Blender: the pattern's change, unless Stay is on; else on a pattern not
        saved, one control of one unpinned feature moved by Reach, or a share of the time the whole
        feature rerolled, gliding there. At jump, the pattern's change, or with Stay every unpinned
        feature rerolled."""
        self.last_step = b._t
        pattern = b.pattern
        roll = None if self.jumping else random.random()
        if not self.stay.value and (roll is None or roll < CHANGE):
            self.back_steps.append((pattern, pattern._to_dict(), pattern.dirty))
            b.start_transition(bars=b.lands_on_bars)
            return
        if pattern.configured:
            return
        features = [fidx for fidx, f in enumerate(pattern.features) if fidx not in self.pins and movable(f)]
        if not features:
            return
        self.back_steps.append((pattern, pattern._to_dict(), pattern.dirty))
        if roll is None:
            for fidx in features:
                pattern.features[fidx].randomize()
            pattern.update()
        elif roll < CHANGE + REROLL:
            pattern.features[random.choice(features)].randomize()
            pattern.update()
        else:
            fidx = random.choice(features)
            cidx = random.choice(movable(pattern.features[fidx]))
            control = pattern.features[fidx].visible_controls()[cidx]
            now = control.selected_idx
            step = random.choice([k - now for k in range(len(control.options)) if 0 < abs(k - now) <= self.reach.value])
            pattern.change(fidx, cidx, step)
        b.glide()

    def back(self, b):
        """Undoes the last step kept: the pattern it left from, back on show if it isn't, with its
        controls as they were."""
        if not self.back_steps:
            return
        pattern, picks, dirty = self.back_steps.pop()
        on_show = b.change.run.pattern if b.change is not None else b.pattern
        if pattern is not on_show:
            b.start_transition(b.patterns.index(pattern))
        pattern._from_dict(picks)
        pattern.dirty = dirty
        if pattern is on_show:
            b.glide()
