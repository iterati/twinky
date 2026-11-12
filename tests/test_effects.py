"""The ten effects on the simulated tree: T1a's pattern cases (through a change, every option, the
seam), no light popping from dark to full in a frame but Lightning's strike, the grain and the
rainbow's drift, a run starting the effect again, and the music's beat and bands reaching them."""
import math
import random

import pytest

from core import Pixel
from effects import EFFECTS, RAINBOW, Drips, EffectPattern, Fireworks, Lightning, Ripples
from support import FRAME, blender, frames, in_range
from test_music import FakeClock, music

def name(cls) -> str:
    return cls.__name__

def effect(cls, **knobs) -> EffectPattern:
    """The effect's pattern with its knobs set by name, Palette="ice" and so on, saved as
    configured so a change doesn't randomize it."""
    pattern = EffectPattern(cls())
    for control in pattern.features[0].controls:
        if control.name in knobs:
            control.set([o.name for o in control.options].index(knobs[control.name]))
    pattern.update(set_dirty=False)
    pattern.configured = True
    return pattern

def next_effect(cls):
    return EFFECTS[(EFFECTS.index(cls) + 1) % len(EFFECTS)]

def level(light) -> float:
    # how bright a light reads: its brightest channel, W counted
    return max(light) / 255

@pytest.mark.parametrize("cls", EFFECTS, ids=name)
def test_effect_through_a_change(cls):
    # 6 s of the effect, its knobs a random pick, its 6 s change into the next one, and 4 s after
    random.seed(1)
    other = next_effect(cls)
    b = blender([EffectPattern(cls()), EffectPattern(other())])
    b.pattern_length = 6.0
    changed = False
    lit = 0.0
    for t, frame in frames(b, 0, 16):
        assert len(frame) == 800
        assert in_range(frame), f"{t}"
        assert [len(interface.frames[-1]) for interface in b.lights.interfaces] == [1600, 1600]
        changed |= b.transitioning
        lit = max(lit, max(map(level, frame)))
    assert changed
    assert b.pattern.name == other.name
    assert lit > 0.3

@pytest.mark.parametrize("cls", EFFECTS, ids=name)
def test_every_option_of_every_control(cls):
    random.seed(4)
    pattern = EffectPattern(cls())
    b = blender([pattern, EffectPattern(next_effect(cls)())])
    t = 0.0
    for feature in pattern.features:
        for cidx, control in enumerate(feature.controls):
            for oidx, option in enumerate(control.options):
                feature.fset(cidx, oidx)
                pattern.update()
                for _ in range(8):
                    frame = b.render(t)
                    b.write(frame)
                    t += FRAME
                    assert in_range(frame), f"{feature.name} {control.name} {option.name}"
            control.randomize()

@pytest.mark.parametrize("cls", EFFECTS, ids=name)
def test_seam_at_angle_0(cls):
    # lights just either side of angle 0 (behind the trunk, at -x), at the same height and depth,
    # beside the tree's own: angle 0 is no edge in the tree's space
    random.seed(5)
    b = blender([effect(cls), EffectPattern(next_effect(cls)())])
    eps = 0.0002
    seam = []
    for i in range(19):
        y = (i + 1) / 20
        r = 0.38 * (1 - y) * 0.9
        for sign in (1, -1):
            a = math.pi - (sign * eps * 2 * math.pi)
            seam.append(Pixel(800 + len(seam), r * math.cos(a), y, r * math.sin(a)))
    assert [round(p.t) for p in seam[:2]] == [1, 0]
    b.pixels = b.pixels + seam
    worst = lit = 0.0
    for _, frame in frames(b, 0, 10):
        pairs = frame[800:]
        lit = max(lit, *map(max, pairs))
        for a, c in zip(pairs[0::2], pairs[1::2]):
            worst = max(worst, *(abs(x - y) for x, y in zip(a, c)))
    assert worst <= 16
    # and the effect reached the seam
    assert lit > 100

@pytest.mark.parametrize("cls", EFFECTS, ids=name)
def test_no_light_pops_from_dark_to_full(cls):
    # 20 s as set: no light goes from under 10% to over 90% in a frame, but where Lightning strikes
    random.seed(6)
    pattern = effect(cls)
    b = blender([pattern, EffectPattern(next_effect(cls)())])
    prev = None
    for t, frame in frames(b, 0, 20):
        levels = [level(light) for light in frame]
        struck = cls is Lightning and pattern.effect.struck == t
        if prev is not None and not struck:
            pops = [i for i, (a, c) in enumerate(zip(prev, levels)) if a < 0.1 and c > 0.9]
            assert not pops, f"{t}: {pops}"
        prev = levels
    if cls is Lightning:
        assert pattern.effect.struck is not None

@pytest.mark.parametrize("cls", EFFECTS, ids=name)
def test_grain_raw_hardens_the_edges(cls):
    random.seed(7)
    pattern = effect(cls)
    b = blender([pattern, EffectPattern(next_effect(cls)())])
    for _ in frames(b, 0, 2):
        pass

    def covers():
        # each light's shape layers, the off one left out
        layers = [pattern.base_color(0, 0, 0, p.t, p.y, p) for p in b.pixels]
        return [[w for w, color, _ in light[:-1]] for light in layers]

    assert any(0.02 < w < 0.98 for light in covers() for w in light)
    pattern.features[1].fset(1, 1)
    pattern.update()
    assert pattern.grain == "raw"
    b.render(2.0)
    for light in covers():
        # a light is in or out: each layer covering it a whole share
        assert all(w == pytest.approx(1 / len(light)) for w in light)

def turned_frames(cls, palette: str, hue: float):
    """4 s of the effect at the palette, the base hue turned by hue from its clock."""
    random.seed(8)
    b = blender([effect(cls, Palette=palette), EffectPattern(next_effect(cls)())])
    b.hue_shift = hue
    return [frame for _, frame in frames(b, 0, 4)]

@pytest.mark.parametrize("cls", [cls for cls in EFFECTS if "Palette" in [k[0] for k in cls.knobs]], ids=name)
def test_only_the_rainbow_palette_drifts(cls):
    for palette in [o for o, _ in next(k for k in cls.knobs if k[0] == "Palette")[1]]:
        turned = turned_frames(cls, palette, 0.25) != turned_frames(cls, palette, 0.0)
        assert turned == (palette == RAINBOW), palette

def test_an_effect_starts_again_with_its_run():
    random.seed(8)
    fireworks = effect(Fireworks)
    b = blender([fireworks, effect(Ripples)])
    for _ in frames(b, 0, 10):
        pass
    assert fireworks.effect.next_launch > 5
    b.start_transition(1)
    for _ in frames(b, 10, 20):
        pass
    assert b.pattern is not fireworks
    b.start_transition(0)
    b.render(20.0)
    # its new run's clock starts at 0, so the effect starts again: its first launch, nothing in the air
    assert fireworks.effect.last == pytest.approx(20.0 - b.change.run.start)
    assert fireworks.effect.next_launch == 0.3 and not fireworks.effect.sparks

def test_the_effects_join_the_rotation(tmp_path, monkeypatch):
    import look
    import twinky
    monkeypatch.setattr(twinky, "SAVES", str(tmp_path))
    monkeypatch.setattr(look, "LOOKS", str(tmp_path / "looks"))
    names = [p.name for p in twinky.start_patterns()]
    assert names[16:26] == [cls.name for cls in EFFECTS]

def beat_frames(cls, first: float, seconds: float=4.0):
    """The effect under Music, its own links alone, at 120 bpm, its beats counted from first."""
    random.seed(9)
    pattern = effect(cls)
    b = blender([pattern, EffectPattern(next_effect(cls)())])
    b.beat = FakeClock(120.0, first)
    music(b, streamers="off", flash="off", sparkle_rate="Off", palette="Off", feel="Off", spin_lock="off")
    return pattern, [frame for _, frame in frames(b, 0, seconds)]

@pytest.mark.parametrize("cls", EFFECTS, ids=name)
def test_a_beat_reaches_an_effect(cls):
    pattern, on_beat = beat_frames(cls, 0.0)
    assert pattern.effect.beat_at == 3.5
    # the same tempo and bands, the beats a quarter of one later: the lights move with them
    _, later = beat_frames(cls, 0.125)
    assert on_beat != later

@pytest.mark.parametrize("cls", [Fireworks, Ripples, Drips], ids=name)
def test_a_launch_waits_for_the_beat(cls):
    # every rocket, drop and drip starts on a beat, every half second at 120 bpm
    random.seed(10)
    pattern = effect(cls)
    b = blender([pattern, EffectPattern(next_effect(cls)())])
    b.beat = FakeClock(120.0, 0.0)
    starts = []
    for t, _ in frames(b, 0, 12):
        e = pattern.effect
        launched = (e.rockets[-1]["start"] if cls is Fireworks and e.rockets else
                    e.drops[-1][0] if cls is Ripples and e.drops else
                    e.drips[-1]["start"] if cls is Drips and e.drips else None)
        if launched == t:
            starts.append(t)
    assert len(starts) >= 3
    assert all((2 * t) == round(2 * t) for t in starts)

def test_lightning_strikes_on_a_bar_line():
    random.seed(11)
    pattern = effect(Lightning, Interval="often")
    b = blender([pattern, EffectPattern(next_effect(Lightning)())])
    b.beat = FakeClock(120.0, 0.0)
    strikes = set()
    for t, _ in frames(b, 0, 24):
        if pattern.effect.struck == t:
            strikes.add(t)
    # a bar every 2 s at 120 bpm
    assert len(strikes) >= 3
    assert all(t % 2 == 0 for t in strikes)
