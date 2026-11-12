"""The six hints on the simulated tree: T1a's pattern cases (through a change, every option, the
seam), their soft edges, their colour as linear light, their clock in beats, and the music's links."""
import json
import os
import random

import pytest

import look
import twinky
from core import Pixel
from hints import HINTS, PaletteColor, Sectors, Wash
from palette import oklch_to_linear
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

FASTEST = {
    "Sectors": {"count": "6", "period": "16", "softness": "1/2"},
    "Bands": {"bands": "6", "drift": "1.0", "softness": "1/2"},
    "Spiral": {"arms": "3", "twist": "2", "period": "16", "softness": "1/2"},
    "Hidden Field": {"lattice": "1/4", "period": "128", "twinkle": "4"},
}

@pytest.mark.parametrize("bpm", [None, 180.0])
@pytest.mark.parametrize("hint", list(FASTEST))
def test_soft_edges_no_light_jumps_from_off_to_full_in_a_frame(hint, bpm):
    # at the fastest and sharpest options, and the music's fastest tempo: every light rises and falls
    # over frames, never from off to its full brightness in one
    random.seed(9)
    cls = next(cls for cls in HINTS if cls().name == hint)
    pattern = pick(cls(), **FASTEST[hint])
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
    pattern = pick(Sectors(), period="16", motion="spin")
    b = blender([pattern, Wash()])
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
    b = blender([pick(Wash(), wave="cos"), Sectors()])
    b.beat = FakeClock(120.0, 0.0, drive=0.0)
    music(b, flash="whole tree", palette="Off", spin_lock="off")
    level = {t: sum(map(sum, frame)) / len(frame) for t, frame in frames(b, 0, 4)}
    for beat in [1.0, 1.5, 2.0, 3.5]:
        assert level[beat] > 1.3 * level[beat - 0.25]
        assert level[beat + FRAME] < level[beat]

def test_the_spin_lock_turns_a_hint():
    b = blender([pick(Sectors(), period="64", motion="sway"), Wash()])
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
    monkeypatch.setattr(twinky, "SAVES", str(tmp_path))
    pattern = cls()
    assert len({c.name for f in pattern.features for c in f.controls}) == sum(len(f.controls) for f in pattern.features)
    pattern.randomize()
    twinky.toggle_configured(type("Animation", (), {"pattern": pattern})())
    with open(tmp_path / os.path.basename(twinky.save_path(pattern))) as file:
        assert json.load(file) == pattern._to_dict()
    loaded = twinky.load_pattern(cls())
    assert loaded.configured and loaded._to_dict() == pattern._to_dict()

def test_the_hints_join_the_rotation(tmp_path, monkeypatch):
    monkeypatch.setattr(twinky, "SAVES", str(tmp_path))
    monkeypatch.setattr(look, "LOOKS", str(tmp_path / "looks"))
    names = [p.name for p in twinky.start_patterns()]
    assert names[10:16] == ["Wash", "Sectors", "Bands", "Spiral", "Hidden Field", "Palette Drift"]
    assert len(set(names)) == 26
