"""How the blender changes patterns, mixes them and moves its effects."""
import random
import statistics

import pytest

from colors import BaseColor, Color
from control import BasicBitch, CircusTent, Confetti, SlidingDoor, WiredPattern
from support import FRAME, blender, delta, frames, quiet, tree_bytes
from topologies import DistortTopology
from pytweening import linear

def flat(b, colors):
    """Has each pattern render one color over the whole tree, so a mix shows as plain numbers."""
    def render(run, now):
        return [colors[run.pattern.name]] * len(b.pixels)
    b._render = render

def test_no_jump_at_a_change_start_or_end():
    # Basic Bitch with its pulse and effects off fading into a quiet Sliding Door: the frames
    # where the change starts (60 s) and ends (66 s) move the tree no more than a few usual frames
    random.seed(1)
    basic = quiet(BasicBitch())
    basic.features[0].controls[0].set(1)
    basic.update(set_dirty=False)
    b = blender([basic, quiet(SlidingDoor())])
    moves = []
    last = None
    for t, _ in frames(b, 50, 76):
        now = tree_bytes(b)
        if last is not None:
            moves.append((t, delta(now, last)))
        last = now
    usual = statistics.median(m for _, m in moves)
    at_edges = [m for t, m in moves if t in [60, 66]]
    assert len(at_edges) == 2
    assert max(at_edges) <= 3 * usual + 1

def test_a_manual_switch_fades_steadily():
    b = blender([BasicBitch(), CircusTent()])
    flat(b, {"Basic Bitch": (0.0, 0, 0, 0), "Circus Tent": (255.0, 0, 0, 0)})
    b.render(23 - FRAME)
    b.start_transition(1)  # as the TUI's Enter does, between frames
    b.change.shape = "crossfade"
    shares = [b.render(k * FRAME)[0][0] / 255 for k in range(round(23 / FRAME), round(31 / FRAME))]
    assert shares[0] < 0.01
    assert all(later >= earlier for earlier, later in zip(shares, shares[1:]))
    assert all(share == 1 for share in shares[round(6 / FRAME):])
    assert max(later - earlier for earlier, later in zip(shares, shares[1:])) < 0.05

def test_a_switch_during_a_change_fades_from_where_it_was():
    b = blender([BasicBitch(), CircusTent(), SlidingDoor()])
    b.next_pattern = b.patterns[1]
    flat(b, {"Basic Bitch": (0.0, 0, 0, 0), "Circus Tent": (255.0, 0, 0, 0), "Sliding Door": (0.0, 255, 0, 0)})
    seen = []
    for k in range(round(59 / FRAME), round(74 / FRAME)):
        t = k * FRAME
        if t == 63:
            b.start_transition(2)
            b.change.shape = "crossfade"
        seen.append((t, b.render(t)[0]))
    at_switch = next(frame for t, frame in seen if t == 63)
    after = [frame for t, frame in seen if t >= 63]
    # from the frozen mix, the old patterns only fade and the new one only grows: nothing snaps back
    assert all(b2[0] <= a2[0] and b2[1] >= a2[1] for a2, b2 in zip(after, after[1:]))
    assert abs(after[1][0] - at_switch[0]) < 5
    assert after[-1] == (0.0, 255, 0, 0)
    assert b.pattern.name == "Sliding Door"

def test_a_saved_pattern_launches_streamers_every_turn():
    random.seed(3)
    confetti = Confetti()
    confetti.randomize()
    feature = confetti.features[0]
    feature._delay.set(0)
    feature._min.set(1)
    feature._max.set(3)
    confetti.update(set_dirty=False)
    confetti.configured = True
    b = blender([confetti, quiet(BasicBitch())])
    b.pixels = b.pixels[::20]  # the streamers launch the same, for a quicker render
    launched = {}
    seen = set()
    for t, _ in frames(b, 0, 200):
        for run in [b.run] + ([b.change.run] if b.change else []):
            if run.pattern is confetti:
                turn = round(run.start)
                new = set(run.streamers) - seen  # the streamers themselves, kept, so no id is reused
                launched[turn] = launched.get(turn, 0) + len(new)
                seen |= new
    # Confetti's turns start fading in at 0 and 120 s (Basic Bitch's at 60 s)
    assert sorted(launched) == [0, 120]
    assert launched[120] > 0.5 * launched[0] > 0

def test_both_patterns_bring_their_own_streamers_into_a_change():
    random.seed(6)
    confetti = Confetti()
    confetti.randomize()
    confetti.features[0]._min.set(1)
    confetti.update()
    b = blender([quiet(BasicBitch()), confetti])
    for _ in frames(b, 0, 63):
        pass
    assert b.change is not None and b.change.run.pattern is confetti
    assert b.change.run.streamers
    assert b.run.streamers == []

@pytest.mark.parametrize("ends", [
    (Color(0, 0.95, 1, 0), Color(0, 0.05, 1, 0)),  # either side of hue 0 (blue, in xled_plus's 8col)
    (Color(0, 0.6, 1, 0), Color(0, 0.66, 1, 0)),  # red to red
    (Color(0, 0.0, 1, -1), Color(0, 0.66, 1, 0)),  # an off light fading up to red
], ids=["across hue 0", "red to red", "off to red"])
def test_a_fade_stays_between_its_ends(ends):
    # mixing light: every frame of the change is W, R, G and B part way between the two patterns',
    # so a fade never passes through another hue
    start, end = (color.as_wrgb() for color in ends)
    b = blender([BasicBitch(), CircusTent()])
    b.next_pattern = b.patterns[1]
    flat(b, {"Basic Bitch": start, "Circus Tent": end})
    for k in range(round(59 / FRAME), round(67 / FRAME)):
        light = b.render(k * FRAME)[0]
        for c, lo, hi in zip(light, start, end):
            assert min(lo, hi) - 1e-9 <= c <= max(lo, hi) + 1e-9

@pytest.mark.parametrize("shape", ["crossfade", "sweep", "rise", "spiral"])
def test_each_transition_turns_the_whole_tree_over(shape):
    b = blender([BasicBitch(), CircusTent()])
    b.next_pattern = b.patterns[1]
    flat(b, {"Basic Bitch": (0.0, 0, 0, 0), "Circus Tent": (255.0, 0, 0, 0)})
    b.render(59)
    b.next_pattern.configured = True  # so the change doesn't randomize its transition
    b.next_pattern.transition = shape
    shares = {t: [light[0] / 255 for light in b.render(t)] for t in [60, 63, 66 - FRAME]}
    assert max(shares[60]) < 0.01
    assert min(shares[66 - FRAME]) > 0.99
    middle = shares[63]
    if shape == "crossfade":
        assert max(middle) - min(middle) < 1e-9
    else:
        assert min(middle) < 0.05 and max(middle) > 0.95
        key = {"sweep": lambda p: p.t, "rise": lambda p: p.y, "spiral": lambda p: (2 * p.y) + p.t}[shape]
        # the lights that turn over first are on, the last off, with a soft edge between
        order = sorted(zip(map(key, b.pixels), middle))
        assert all(later <= earlier + 1e-9 for (_, earlier), (_, later) in zip(order, order[1:]))
        assert sum(0.05 < share < 0.95 for share in middle) > 20

def test_a_control_change_glides():
    random.seed(7)
    pattern = quiet(SlidingDoor())
    b = blender([pattern, BasicBitch()])
    for _ in frames(b, 0, 10):
        pass
    before = tree_bytes(b)
    pattern.set(0, 2, 5)  # its Rainbow
    b.glide()
    moves = [delta(before, tree_bytes(b)) for _ in frames(b, 10, 10 + FRAME)]
    for _ in frames(b, 10 + FRAME, 11):
        pass
    assert b.glide_from is None
    assert moves[0] < 5

def lit_pattern(name, **kwargs):
    pattern = WiredPattern(name, **kwargs)
    pattern.configured = True
    return pattern

def test_flash_dims_lit_lights_and_flitter_spares_white():
    b = blender([
        lit_pattern("Lit", base_color=BaseColor(l=0), flash=0.5),
        lit_pattern("White", base_color=BaseColor(w=1, s=0, l=-0.75), flitter=1),
    ])
    lit = sum(BaseColor(l=0)(0, 0, 0, 0, 0)[0][1].as_wrgb())
    frame = b._render(b.run, 1)
    assert sum(map(sum, frame)) / len(frame) < 0.9 * lit
    white = BaseColor(w=1, s=0, l=-0.75)(0, 0, 0, 0, 0)[0][1].as_wrgb()
    b.run = type(b.run)(b.patterns[1], 0)
    assert all(light == white for light in b._render(b.run, 1))

@pytest.mark.parametrize("grain, least", [("smooth", 0.9), ("raw", -1)])
def test_the_grain_of_flicker(grain, least):
    random.seed(8)
    pattern = quiet(BasicBitch())
    flicker = pattern.features[1]
    flicker.controls[0].set(0)  # Enabled
    flicker.controls[1].set(6)  # Start 1/2
    pattern.features[-1]._grain.set(["smooth", "raw"].index(grain))
    pattern.update(set_dirty=False)
    b = blender([pattern, CircusTent()])
    ws = [frame[100][0] for _, frame in frames(b, 0, 20)]
    m = statistics.mean(ws)
    lag1 = sum((ws[i] - m) * (ws[i - 1] - m) for i in range(1, len(ws))) / sum((w - m) ** 2 for w in ws)
    assert lag1 > least
    if grain == "raw":
        assert lag1 < 0.5

def test_smooth_sparkles_fade_in_and_out():
    random.seed(9)
    pattern = quiet(BasicBitch())
    sparkles = pattern.features[4]
    sparkles.controls[0].set(0)  # Enabled
    sparkles.controls[1].set(1)  # Start 1/8
    pattern.update(set_dirty=False)
    b = blender([pattern, CircusTent()])
    for _ in frames(b, 0, 5):
        pass
    strengths = [b._sparkle(b.run, idx, 5 - FRAME) for idx in range(len(b.pixels))]
    assert any(0.05 < s < 0.95 for s in strengths)

@pytest.mark.parametrize("mid", [m / 8 for m in range(-4, 5)])
def test_groovys_twist_has_no_tear(mid):
    twist = DistortTopology(linear, 0.25, -0.25, mid)(0)
    heights = [i / 400 for i in range(400)]
    values = [twist(0.0, y) for y in heights]
    assert max(abs(b - a) for a, b in zip(values, values[1:])) < 0.02
