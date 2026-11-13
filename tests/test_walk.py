"""The walk, the Blender's autopilot: its steps by Reach and Pace, pins, Stay, Back and Nudge, on the
simulated tree."""
import random

import pytest

import commands
import walk
from control import BasicBitch, CircusTent, SlidingDoor
from support import FRAME, blender, frames, quiet
from test_music import FakeClock

def picks(pattern) -> list[list[int]]:
    return [[c.selected_idx for c in f.controls] for f in pattern.features]

def moved(before, after) -> list[tuple[int, int, int]]:
    """Each control that moved: its feature, its index and how far."""
    return [(fidx, cidx, b - a)
            for fidx, (fa, fb) in enumerate(zip(before, after))
            for cidx, (a, b) in enumerate(zip(fa, fb)) if a != b]

def walker(patterns):
    b = blender(patterns)
    b.pixels = b.pixels[::20]  # the walk steps the same, for a quicker render
    return b

def reach(b, name: str):
    b.walk.reach.set([o.name for o in walk.REACHES].index(name))

def pace(b, name: str):
    b.walk.pace.set([o.name for o in walk.PACES].index(name))

@pytest.fixture
def stepping(monkeypatch):
    # every step a control's, unless a test asks for rerolls or changes
    monkeypatch.setattr(walk, "REROLL", 0.0)
    monkeypatch.setattr(walk, "CHANGE", 0.0)

@pytest.mark.parametrize("name, most", [("near", 1), ("far", 3), ("any", None)])
def test_a_step_moves_one_control_of_one_feature_by_reach(stepping, name, most):
    random.seed(1)
    b = walker([BasicBitch(), CircusTent()])
    reach(b, name)
    sizes = set()
    t = 0.0
    for _ in range(200):
        t += FRAME
        b.render(t)
        before = picks(b.pattern)
        commands.nudge(b)
        assert b.glide_from is not None and b.glide_start == t
        [(fidx, cidx, size)] = moved(before, picks(b.pattern))
        feature = b.pattern.features[fidx]
        control = feature.controls[cidx]
        # a visible control, moved without wrapping round its options
        assert control in feature.visible_controls()
        assert 0 <= before[fidx][cidx] + size < len(control.options)
        sizes.add(abs(size))
    assert b.pattern.name == "Basic Bitch" and not b.transitioning
    if most is None:
        # any option: as far as across the longest list
        assert max(sizes) >= 5
    else:
        assert sizes == set(range(1, most + 1))

def test_a_pinned_feature_never_moves_nor_rerolls(monkeypatch):
    random.seed(2)
    monkeypatch.setattr(walk, "CHANGE", 0.0)
    monkeypatch.setattr(walk, "REROLL", 0.5)
    b = walker([BasicBitch(), CircusTent()])
    reach(b, "any")
    commands.toggle_pin(0)(b)
    commands.toggle_pin(2)(b)
    before = picks(b.pattern)
    for _ in range(300):
        commands.nudge(b)
    after = picks(b.pattern)
    seen = {fidx for fidx, _, _ in moved(before, after)}
    assert after[0] == before[0] and after[2] == before[2]
    assert seen and not seen & {0, 2}
    # a pin flipped again lets go
    commands.toggle_pin(2)(b)
    assert b.walk.pins == {0}

def test_pins_clear_when_the_pattern_changes():
    b = walker([BasicBitch(), CircusTent()])
    commands.toggle_pin(1)(b)
    commands.switch_pattern(1)(b)
    assert b.walk.pins == set()
    commands.toggle_pin(1)(b)  # pinned during the change: the last pattern's feature
    for _ in frames(b, FRAME, 7):
        pass
    assert b.pattern.name == "Circus Tent" and b.walk.pins == set()

def test_music_cannot_be_pinned():
    b = walker([BasicBitch(), CircusTent()])
    commands.toggle_pin(len(b.pattern.features))(b)
    assert b.walk.pins == set()

def test_stay_never_changes_the_pattern(monkeypatch):
    random.seed(3)
    monkeypatch.setattr(walk, "CHANGE", 1.0)
    for name in ["near", "jump"]:
        b = walker([BasicBitch(), CircusTent()])
        reach(b, name)
        pace(b, "fast")
        commands.toggle_stay(b)
        assert b.walk.stay.value
        before = picks(b.pattern)
        for _ in frames(b, 0, 130):
            assert not b.transitioning
        assert b.pattern.name == "Basic Bitch" and moved(before, picks(b.pattern))

def test_at_jump_the_pattern_changes_freshly_randomized_every_60_s():
    random.seed(4)
    b = walker([BasicBitch(), CircusTent()])
    assert b.walk.jumping
    pace(b, "fast")  # no say at jump
    before = picks(b.pattern)
    for _ in frames(b, 0, 60):
        pass
    assert not b.transitioning and picks(b.pattern) == before
    for _ in frames(b, 60, 60 + FRAME):
        pass
    assert b.transitioning and b.change.start == 60 and b.change.run.pattern.name == "Circus Tent"
    assert b.next_pattern.dirty  # randomized as it came in
    for _ in frames(b, 60 + FRAME, 121):
        pass
    assert b.transitioning and b.change.start == 120 and b.change.run.pattern.name == "Basic Bitch"

def test_pace_sets_the_seconds_between_steps(stepping):
    for name, (seconds, _) in [(o.name, o.value) for o in walk.PACES]:
        b = walker([BasicBitch(), CircusTent()])
        reach(b, "near")
        pace(b, name)
        steps = []
        for t, _ in frames(b, 0, 16 + FRAME):
            if b.walk.last_step == t and t > 0:
                steps.append(t)
        assert steps == pytest.approx([seconds * k for k in range(1, round(16 / seconds) + 1)])

def test_with_music_on_the_walk_steps_on_bar_lines(stepping):
    b = walker([quiet(BasicBitch()), quiet(SlidingDoor())])
    b.pattern.configured = False
    reach(b, "near")
    b.beat = FakeClock(120.0, 0.3)
    for name, (_, bars) in [(o.name, o.value) for o in walk.PACES]:
        pace(b, name)
        start = b._t + FRAME
        steps = []
        for t, _ in frames(b, start, start + 16):
            if b.walk.last_step == t:
                steps.append(t)
        # bar lines every 2 s from 0.3 s, a step every so many
        beats = [(t - 0.3) * 2 for t in steps]
        assert len(steps) == pytest.approx(8 / bars, abs=1)
        assert all(abs(beat - (4 * bars) * round(beat / (4 * bars))) <= FRAME * 2 for beat in beats)
        assert all(later - earlier == pytest.approx(2 * bars, abs=FRAME)
                   for earlier, later in zip(steps, steps[1:]))

def test_pause_stops_the_walk(stepping):
    b = walker([BasicBitch(), CircusTent()])
    reach(b, "near")
    commands.pauseplay(b)
    before = picks(b.pattern)
    for _ in frames(b, 0, 70):
        pass
    assert picks(b.pattern) == before and not b.transitioning

def test_back_undoes_the_last_steps_in_turn(stepping):
    random.seed(5)
    b = walker([BasicBitch(), CircusTent()])
    reach(b, "far")
    b.pattern.dirty = False
    commands.pauseplay(b)  # Back while paused too
    trail = [picks(b.pattern)]
    for _ in range(3):
        commands.nudge(b)
        trail.append(picks(b.pattern))
    assert b.mark == "*"
    for k in [2, 1, 0]:
        commands.walk_back(b)
        assert picks(b.pattern) == trail[k]
    assert b.mark == "?" and not b.walk.back_steps
    commands.walk_back(b)  # nothing left to undo
    assert picks(b.pattern) == trail[0]

def test_back_keeps_the_last_ten_steps(stepping):
    b = walker([BasicBitch(), CircusTent()])
    reach(b, "near")
    for _ in range(walk.BACK_STEPS + 5):
        commands.nudge(b)
    assert len(b.walk.back_steps) == walk.BACK_STEPS

def test_back_undoes_a_change_of_pattern(monkeypatch):
    random.seed(6)
    monkeypatch.setattr(walk, "REROLL", 0.0)
    monkeypatch.setattr(walk, "CHANGE", 0.0)
    b = walker([BasicBitch(), CircusTent()])
    reach(b, "near")
    commands.nudge(b)
    basic = picks(b.pattern)
    monkeypatch.setattr(walk, "CHANGE", 1.0)
    commands.nudge(b)
    assert b.change.run.pattern.name == "Circus Tent"
    for _ in frames(b, FRAME, 7):
        pass
    assert b.pattern.name == "Circus Tent"
    commands.walk_back(b)
    # back to Basic Bitch through a change, its controls as they were, though the change randomizes
    assert b.change.run.pattern.name == "Basic Bitch"
    assert picks(b.change.run.pattern) == basic
    for _ in frames(b, 7, 14):
        pass
    assert b.pattern.name == "Basic Bitch" and picks(b.pattern) == basic
    # and the step before it, in place
    commands.walk_back(b)
    assert len(moved(basic, picks(b.pattern))) == 1 and not b.walk.back_steps

def test_nudge_steps_once_now(stepping):
    random.seed(7)
    b = walker([BasicBitch(), CircusTent()])
    reach(b, "near")
    for _ in frames(b, 0, 1):
        pass
    before = picks(b.pattern)
    commands.nudge(b)
    assert len(moved(before, picks(b.pattern))) == 1
    assert b.walk.last_step == b._t and len(b.walk.back_steps) == 1

def test_a_saved_patterns_controls_are_held(monkeypatch):
    random.seed(8)
    monkeypatch.setattr(walk, "REROLL", 0.5)
    b = walker([quiet(BasicBitch()), CircusTent()])
    assert b.pattern.configured
    pace(b, "fast")
    before = picks(b.pattern)
    for name in ["near", "any", "jump"]:
        reach(b, name)
        commands.toggle_stay(b)
        for _ in range(20):
            commands.nudge(b)
        commands.toggle_stay(b)
    assert picks(b.pattern) == before and b.mark == "!" and not b.walk.back_steps
    # it may still move on to another pattern
    monkeypatch.setattr(walk, "CHANGE", 1.0)
    reach(b, "near")
    commands.nudge(b)
    assert b.change.run.pattern.name == "Circus Tent"

def test_back_gives_a_pattern_saved_since_the_step_its_mark_back(stepping, tmp_path, monkeypatch):
    monkeypatch.setattr(commands, "SAVES", str(tmp_path))
    b = walker([BasicBitch(), CircusTent()])
    reach(b, "near")
    b.pattern.dirty = False
    before = picks(b.pattern)
    commands.nudge(b)
    commands.toggle_configured(b)
    assert b.pattern.configured
    commands.walk_back(b)
    # the picks before the step, which the save does not hold: not saved, so the walk moves them again
    assert picks(b.pattern) == before and b.mark == "?" and not b.pattern.configured

def test_nudge_waits_out_a_change(stepping):
    b = walker([BasicBitch(), CircusTent()])
    reach(b, "near")
    commands.switch_pattern(1)(b)
    before = picks(b.pattern)
    commands.nudge(b)
    assert picks(b.pattern) == before and not b.walk.back_steps
