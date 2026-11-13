"""The three hints on the simulated tree: T1a's pattern cases (through a change, every option, the
seam), their soft edges, their colour as linear light, their clock in beats, and the music's links;
their sweeps, layers, Ride and tick, and that each keeps changing over a minute."""
import json
import os
import random

import pytest

import commands
import look
from core import Pixel
from hints import HINTS, TICK, HiddenField, Hint, HintFeature, PaletteColor, Slices, Wash, tick
from palette import oklch_to_linear
from param import getv
from support import FRAME, blender, frames, in_range
from test_music import FakeClock, music

def name(cls) -> str:
    return cls.__name__

def next_hint(cls):
    return HINTS[(HINTS.index(cls) + 1) % len(HINTS)]

def pick(pattern, **picks):
    """Sets the hint's own controls by name, Count="6" and so on, and saves it as configured so a
    change doesn't randomize it again."""
    for control in pattern.features[0].controls:
        if control.name.lower() in picks:
            control.set([o.name for o in control.options].index(picks[control.name.lower()]))
    pattern.update(set_dirty=False)
    pattern.configured = True
    return pattern

@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("cls", HINTS, ids=name)
def test_hint_through_a_change(cls, seed):
    # 60 s of the hint, its 6 s change into the next one, and 4 s after
    random.seed(seed)
    other = next_hint(cls)
    b = blender([cls(), other()])
    changed = False
    lit = 0.0
    for t, frame in frames(b, 0, 70):
        assert len(frame) == 800
        assert in_range(frame), f"{t}"
        assert [len(interface.frames[-1]) for interface in b.lights.interfaces] == [1600, 1600]
        changed |= b.transitioning
        lit = max(lit, max(map(sum, frame)))
    assert changed
    assert b.pattern.name == other().name
    assert lit > 100

@pytest.mark.parametrize("cls", HINTS, ids=name)
def test_every_option_of_every_control(cls):
    random.seed(4)
    pattern = cls()
    b = blender([pattern, next_hint(cls)()])
    t = 0.0
    for feature in pattern.features:
        for cidx, control in enumerate(feature.controls):
            for oidx, option in enumerate(control.options):
                feature.fset(cidx, oidx)
                pattern.update()
                for _ in range(4):
                    frame = b.render(t)
                    b.write(frame)
                    t += FRAME
                    assert in_range(frame), f"{feature.name} {control.name} {option.name}"
            control.randomize()

@pytest.mark.parametrize("seed", [5, 6, 7])
@pytest.mark.parametrize("cls", HINTS, ids=name)
def test_seam_at_angle_0(cls, seed):
    # lights just either side of angle 0 at the same height agree as the hints move: angle 0 is no edge
    random.seed(seed)
    pattern = cls()
    pattern.randomize()
    pattern.configured = True
    b = blender([pattern, next_hint(cls)()])
    eps = 0.0002
    b.pixels = []
    for i in range(19):
        for t in [eps, 1 - eps]:
            pixel = Pixel(len(b.pixels), -1.0, (i + 1) / 20, 0.0)
            pixel.t = t
            b.pixels.append(pixel)
    worst = 0.0
    for _, frame in frames(b, 0, 40):
        for a, c in zip(frame[0::2], frame[1::2]):
            worst = max(worst, *(abs(x - y) for x, y in zip(a, c)))
    assert worst <= 16

SLICES = {"count": "6", "period": "16", "motion": "glide", "lean": "1", "lean period": "32", "softness": "1/2"}
FASTEST = {
    "Slices around": (Slices, {"axis": "around"} | SLICES),
    "Slices up": (Slices, {"axis": "up"} | SLICES),
    "Slices leaned": (Slices, {"axis": "leaned"} | SLICES),
    "Hidden Field": (HiddenField, {"lattice": "1/4", "period": "128", "twinkle": "4", "reveal": "1",
                                   "reveal period": "16"}),
}

@pytest.mark.parametrize("bpm", [None, 180.0])
@pytest.mark.parametrize("hint", list(FASTEST))
def test_soft_edges_no_light_jumps_from_off_to_full_in_a_frame(hint, bpm):
    # at the fastest and sharpest options, and the music's fastest tempo: every light rises and falls
    # over frames, never from off to its full brightness in one
    random.seed(9)
    cls, picks = FASTEST[hint]
    pattern = pick(cls(), **picks)
    pattern.features[1].controls[1].set(0)  # Grain smooth
    b = blender([pattern, Wash()])
    if bpm is not None:
        b.beat = FakeClock(bpm, 0.0)
        music(b, flash="off", palette="Off", spin_lock="off")
    levels = [[sum(light) for light in frame] for _, frame in frames(b, 0, 30)]
    full = [max(light) for light in zip(*levels)]
    assert max(full) > 100
    worst = max(abs(after[i] - before[i]) / full[i]
                for before, after in zip(levels, levels[1:]) for i in range(len(full)) if full[i] > 20)
    assert worst < 0.5
    # and the shape moves: lights do change
    assert max(abs(a - c) for a, c in zip(levels[0], levels[-1])) > 20

def test_the_palettes_colour_reaches_the_lights_as_linear_light():
    lch = (0.62, 0.14, 250.0)
    color = PaletteColor(lch)
    assert color.as_wrgb() == pytest.approx((0, *(255 * c for c in oklch_to_linear(lch))))
    color.l = -0.5
    assert color.as_wrgb() == pytest.approx((0, *(127.5 * c for c in oklch_to_linear(lch))))
    color.l = 1.0
    assert color.as_wrgb() == pytest.approx((0, 255, 255, 255))
    color.l = -1.0
    assert color.as_wrgb() == (0, 0, 0, 0)

def test_a_hints_periods_count_beats_while_music_plays_and_seconds_otherwise():
    pattern = pick(Wash(), period="16")
    b = blender([pattern, Slices()])
    running = pattern.features[0].running
    for _ in frames(b, 0, 4):
        pass
    assert running.phase == pytest.approx(4 / 16, abs=FRAME / 16)
    b.beat = FakeClock(120.0, 0.0)
    for _ in frames(b, 4, 8):
        pass
    # 4 s more at 120 bpm: 8 beats
    assert running.phase == pytest.approx((4 + 8) / 16, abs=2 * FRAME / 16)

def test_the_beat_flash_shows_on_a_hint():
    random.seed(10)
    b = blender([pick(Wash(), wave="cos"), Slices()])
    b.beat = FakeClock(120.0, 0.0, drive=0.0)
    music(b, flash="whole tree", palette="Off", spin_lock="off")
    level = {t: sum(map(sum, frame)) / len(frame) for t, frame in frames(b, 0, 4)}
    for beat in [1.0, 1.5, 2.0, 3.5]:
        assert level[beat] > 1.3 * level[beat - 0.25]
        assert level[beat + FRAME] < level[beat]

def test_the_spin_lock_turns_a_hint():
    b = blender([pick(Slices(), period="64"), Wash()])
    b.beat = FakeClock(120.0, 0.0)
    music(b, flash="off", spin_lock="4 bars")
    for _ in frames(b, 0, 12):
        pass
    still = b.render(12.0)
    b.spin_angle += 0.1
    assert b._render(b.run, 12.0) != still

@pytest.mark.parametrize("cls", HINTS, ids=name)
def test_a_hints_save_round_trips_by_name(cls, tmp_path, monkeypatch):
    random.seed(11)
    monkeypatch.setattr(commands, "SAVES", str(tmp_path))
    pattern = cls()
    assert len({c.name for f in pattern.features for c in f.controls}) == sum(len(f.controls) for f in pattern.features)
    pattern.randomize()
    commands.toggle_configured(type("Animation", (), {"pattern": pattern})())
    with open(tmp_path / os.path.basename(commands.save_path(pattern))) as file:
        assert json.load(file) == pattern._to_dict()
    loaded = commands.load_pattern(cls())
    assert loaded.configured and loaded._to_dict() == pattern._to_dict()

def test_the_hints_join_the_rotation(tmp_path, monkeypatch):
    monkeypatch.setattr(commands, "SAVES", str(tmp_path))
    monkeypatch.setattr(look, "LOOKS", str(tmp_path / "looks"))
    names = [p.name for p in commands.start_patterns()]
    assert names[10:13] == ["Wash", "Slices", "Hidden Field"]
    assert len(set(names)) == 23

def test_a_curved_knob_sweeps_between_its_values_over_its_period():
    # Span from its rest, 3/2, to its value and back each period, eased as its Curve: seconds here
    pattern = pick(Wash(), span="1/4", **{"span curved": "On", "span curve": "linear", "span period": "16"})
    feature = pattern.features[0]
    b = blender([pattern, Slices()])
    spans = {t: feature.swept[0] for t, _ in frames(b, 0, 17)}
    assert spans[0.0] == pytest.approx(3/2)
    assert spans[4.0] == pytest.approx((3/2 + 1/4) / 2, abs=1e-6)
    assert spans[8.0] == pytest.approx(1/4)
    assert spans[16.0] == pytest.approx(3/2)
    assert min(spans.values()) == pytest.approx(1/4) and max(spans.values()) == pytest.approx(3/2)
    # and Curved off, the value
    pick(pattern, **{"span curved": "Off"})
    for _ in frames(b, 17, 18):
        pass
    assert feature.swept[0] == 1/4
    assert [c.name for c in feature.visible_controls()].count("Span Period") == 0

def test_with_music_beating_a_curved_knob_counts_beats_and_turns_on_bar_lines():
    # the music's bar lines half a beat off the hint's start: its clock is drawn onto them
    pattern = pick(Wash(), span="1/4", **{"span curved": "On", "span curve": "linear", "span period": "16"})
    feature = pattern.features[0]
    b = blender([pattern, Slices()])
    b.beat = FakeClock(120.0, 0.25)
    music(b, flash="off", palette="Off", spin_lock="off")
    seen = []
    for _ in frames(b, 0, 24):
        seen.append((b.sound.beat, getv(feature.span, feature.clock)))
    settled = seen[8 * 16:]
    # 16 beats a period: 8 s at 120 bpm, the far end and back
    ends = [beat for (_, before), (beat, span), (_, after) in zip(settled, settled[1:], settled[2:])
            if before > span < after]
    assert ends and all(abs(beat - (4 * round(beat / 4))) < 2 * 0.125 for beat in ends)
    assert min(span for _, span in settled) == pytest.approx(1/4, abs=0.02)
    assert all(abs(((feature.clock - beat + 2) % 4) - 2) < 1e-3 for beat, _ in seen[-1:])

class TwoLayers(HintFeature):
    def __init__(self):
        super(TwoLayers, self).__init__("Two Layers", [], [])

    def layers(self, x, y):
        return [(0.25, (0.6, 0.1, 30.0), 0.0), (0.5, (0.5, 0.12, 200.0), -0.5)]

def test_a_layered_hint_gives_its_layers_colours():
    layers = Hint(TwoLayers())(0.0, 0.3, 0.0, 0.2, 0.5, None)
    assert [weight for weight, _, _ in layers] == [0.25, 0.5, 0.25]
    a, b, off = (color.as_wrgb() for _, color, _ in layers)
    assert a == pytest.approx((0, *(255 * c for c in oklch_to_linear((0.6, 0.1, 30.0)))))
    assert b == pytest.approx((0, *(127.5 * c for c in oklch_to_linear((0.5, 0.12, 200.0)))))
    assert off == (0, 0, 0, 0)

def test_wash_round_crossfades_two_whole_turns_of_the_palette():
    # a Span of 1/4 is half a turn round the trunk: half each of no turn and one, as bright as the wave
    pattern = pick(Wash(), axis="round", span="1/4", **{"span curved": "Off"})
    feature = pattern.features[0]
    feature.frame(1.0, 1.0)
    (a, _, _), (b, _, _) = feature.layers(0.3, 0.6)
    assert a == pytest.approx(b) and 0 < a + b <= 1

@pytest.mark.parametrize("ride", ["On", "Off"])
def test_ride_turns_the_palette_with_the_base_hue(ride):
    pattern = pick(Wash(), ride=ride)
    feature = pattern.features[0]
    feature.frame(1.0, 1.0)
    (_, lch, _), = feature.layers(0.3, 0.6)
    hint = pattern.base_color
    for blend in [0.0, 0.25, 0.6]:
        (_, color, _), _ = hint(0.0, blend, 0.0, 0.3, 0.6, None)
        turned = 360 * blend if ride == "On" else 0.0
        assert color.as_wrgb() == pytest.approx((0, *(255 * c for c in oklch_to_linear((lch[0], lch[1], lch[2] + turned)))))

def test_the_tick_steps_and_holds():
    assert tick(2.0) == 2.0
    # it steps in TICK of the beat, overshooting, then holds on the next
    assert max(tick(2 + (k * TICK / 20)) for k in range(21)) > 3.05
    assert tick(2 + TICK) == pytest.approx(3.0)
    assert all(tick(2 + TICK + (k * (1 - TICK) / 10)) == pytest.approx(3.0) for k in range(10))

def test_slices_tick_on_the_beat_with_music():
    pattern = pick(Slices(), motion="tick", period="16")
    feature = pattern.features[0]
    b = blender([pattern, Wash()])
    b.beat = FakeClock(120.0, 0.25)
    music(b, flash="off", palette="Off", spin_lock="off")
    held = []
    for t, _ in frames(b, 0, 12):
        if t > 8 and TICK + 0.1 < b.sound.beat % 1:
            held.append((b.sound.beat, feature.swept[0] * 16))
    # between its steps, a step a beat, the turn holds still, a whole step on
    assert held and all(abs(turn - round(turn)) < 0.01 for _, turn in held)
    assert len({round(turn) for _, turn in held}) >= 7

def seconds_of(pattern, other) -> list[list[float]]:
    """A minute of the hint on a quarter of the lights at 4 frames a second: each second's lights'
    levels."""
    random.seed(13)
    b = blender([pattern, other])
    b.pause_change = True
    b.pixels = b.pixels[::4]
    return [[sum(light) / 255 for light in b.render(k / 4)] for k in range(4 * 60)][::4]

def novelty(seconds) -> float:
    """As the design notes' metric: how far each second of the minute's last half is from the
    nearest at least 4 s before it, against how far apart two seconds are as a rule. 0 is a loop."""
    def apart(a, b):
        return sum(abs(x - y) for x, y in zip(a, b)) / len(a)

    typical = sum(apart(a, b) for a in seconds[::3] for b in seconds[1::3]) / (len(seconds[::3]) * len(seconds[1::3]))
    return sum(min(apart(seconds[k], seconds[j]) for j in range(k - 3)) for k in range(30, 60)) / 30 / typical

def swing(seconds) -> float:
    """As the design notes' metric: how far the share of lights lit and twice their mean level
    swing between 2 s windows over the minute."""
    lit = [sum(sum(v > 0.06 for v in s) / len(s) for s in seconds[k:k + 2]) / 2 for k in range(0, 60, 2)]
    mean = [sum(sum(s) / len(s) for s in seconds[k:k + 2]) / 2 for k in range(0, 60, 2)]
    return (max(lit) - min(lit)) + (2 * (max(mean) - min(mean)))

@pytest.mark.parametrize("axis", ["up", "round"])
def test_the_tide_keeps_changing_over_a_minute(axis):
    # the old Wash was an exact loop, its novelty 0
    assert novelty(seconds_of(pick(Wash(), axis=axis), Slices())) > 0.4

@pytest.mark.parametrize("axis", ["around", "up", "leaned"])
def test_slices_keep_changing_over_a_minute(axis):
    # as Sectors, Bands and Spiral did, the slices loop without their lean; with it, they don't
    flat = pick(Slices(), axis=axis, lean="3", **{"lean curved": "Off"})
    assert novelty(seconds_of(flat, Wash())) < 0.05
    leaning = pick(Slices(), axis=axis, lean="3", **{"lean curved": "On", "lean period": "48"})
    assert novelty(seconds_of(leaning, Wash())) > 0.2

def test_the_reveal_swings_from_sparkles_to_solid_stars_over_a_minute():
    # the old Hidden Field's swing was under 0.2, much as the field held revealed
    held = pick(HiddenField(), reveal="1", **{"reveal curved": "Off"})
    assert swing(seconds_of(held, Wash())) < 0.3
    revealed = pick(HiddenField(), reveal="1", **{"reveal curved": "On", "reveal period": "32"})
    assert swing(seconds_of(revealed, Wash())) > 0.6
