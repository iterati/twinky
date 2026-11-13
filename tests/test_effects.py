"""The ten effects on the simulated tree: T1a's pattern cases (through a change, every option, the
seam), no light popping from dark to full in a frame but Lightning's strike, the grain and the
rainbow's drift, a run starting the effect again, and the music's beat and bands reaching them; each
developing over a minute, its Curved knob's sweep, the finale and Ripples' first ring's paint."""
import math
import random

import pytest

from core import Pixel
from effects import (EFFECTS, PAUSE, RAINBOW, VOLLEY, Aurora, Comets, Drips, EffectPattern, Fireflies, Fireworks,
                     Hearth, Heartbeat, LavaLamp, Lightning, Ripples)
from param import getv
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
    import commands
    monkeypatch.setattr(commands, "SAVES", str(tmp_path))
    monkeypatch.setattr(look, "LOOKS", str(tmp_path / "looks"))
    names = [p.name for p in commands.start_patterns()]
    assert names[13:23] == [cls.name for cls in EFFECTS]

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

def windows(cls) -> list[tuple[float, ...]]:
    """A minute of the effect as set on a quarter of the lights at 4 frames a second, in 10 s windows:
    each window's share of lights lit and its mean W, R, G and B."""
    random.seed(13)
    b = blender([effect(cls), EffectPattern(next_effect(cls)())])
    b.pause_change = True
    b.pixels = [Pixel(i, p.x, p.y, p.z) for i, p in enumerate(b.pixels[::4])]
    lights = [b.render(k / 4) for k in range(4 * 60)]
    out = []
    for w in range(6):
        window = [light for frame in lights[40 * w:40 * (w + 1)] for light in frame]
        lit = sum(max(light) > 0.06 * 255 for light in window) / len(window)
        out.append((lit, *(sum(light[c] for light in window) / len(window) / 255 for c in range(4))))
    return out

# How far apart the minute's windows get at least, against the effect each replaced, which measured
# Aurora 0.44, Fireflies 0.006, Fireworks 0.03, Ripples 0.21, Lava lamp 0.08, Comets 0.006, Hearth
# 0.22, Lightning 0.05, Drips 0.08 and Heartbeat 0, an exact loop
DEVELOPS = {Aurora: 0.6, Fireflies: 0.2, Fireworks: 0.15, Ripples: 0.3, LavaLamp: 0.2, Comets: 0.05,
            Hearth: 0.5, Lightning: 0.3, Drips: 0.35, Heartbeat: 0.4}

@pytest.mark.parametrize("cls", EFFECTS, ids=name)
def test_each_effect_develops_over_a_minute(cls):
    # the two windows furthest apart, by their lit share and colour summed
    ws = windows(cls)
    assert max(sum(abs(a - c) for a, c in zip(u, v)) for u in ws for v in ws) > DEVELOPS[cls]

SWEPT = {cls: next(k for k in cls.knobs if len(k) > 3) for cls in EFFECTS if any(len(k) > 3 for k in cls.knobs)}

def test_eight_effects_have_a_swept_knob():
    assert {cls: k[0] for cls, k in SWEPT.items()} == {
        Aurora: "Surge", Fireflies: "Count", Fireworks: "Build", LavaLamp: "Heat", Hearth: "Height",
        Lightning: "Storm", Drips: "Rate", Heartbeat: "Rate"}

@pytest.mark.parametrize("cls", list(SWEPT), ids=name)
def test_a_curved_knob_sweeps_from_its_rest_to_its_value_over_its_period(cls):
    # as an effect starts: Curved, a sine in and out over 32 s of the run's clock, from the knob's rest
    knob, options, start, rest = SWEPT[cls][:4]
    value = dict(options)[start]
    pattern = effect(cls)
    feature = pattern.features[0]
    swept = pattern.effect.knob[knob]
    assert getv(swept, 0.0) == rest
    if cls is Fireworks:
        # a ramp: up to the value over the period, then straight back to rest
        assert getv(swept, 16.0) == pytest.approx((rest + value) / 2)
        assert getv(swept, 31.9) == pytest.approx(value, abs=0.01 * abs(value - rest))
    else:
        assert getv(swept, 8.0) == pytest.approx((rest + value) / 2)
        assert getv(swept, 16.0) == pytest.approx(value)
        assert getv(swept, 24.0) == pytest.approx((rest + value) / 2)
    assert getv(swept, 32.0) == pytest.approx(rest)
    assert f"{knob} Period" in [c.name for c in feature.visible_controls()]
    # Curved off, the value, its Curve and Period hidden
    sweep = feature.sweeps[0]
    sweep.curved.set(1)
    pattern.update(set_dirty=False)
    assert pattern.effect.knob[knob] == value
    assert f"{knob} Period" not in [c.name for c in feature.visible_controls()]

def test_the_fireworks_build_to_a_finale_then_pause():
    random.seed(12)
    pattern = effect(Fireworks)
    b = blender([pattern, EffectPattern(next_effect(Fireworks)())])
    launches = {}
    for t, _ in frames(b, 0, 40):
        fresh = [r for r in pattern.effect.rockets if r["start"] == t]
        if fresh:
            launches[t] = len(fresh)
    finales = [t for t, n in launches.items() if n == VOLLEY]
    # once a build, as it reaches 0.9 of its 32 s ramp (eased, 25.4 s), then the pause, and the rockets
    # coming quicker as it builds
    assert len(finales) == 1 and 25.4 <= finales[0] < 27
    assert not [t for t in launches if finales[0] < t < finales[0] + PAUSE]
    early = [t for t in launches if t < 10]
    late = [t for t in launches if 18 < t < finales[0]]
    assert len(late) / (finales[0] - 18) > 1.5 * len(early) / 10

def test_ripples_first_ring_paints_the_tree():
    # the first drop falls at once, and its ring repaints the tree as it spreads: within 2 s, a share
    # of the tree holds its colour
    random.seed(14)
    pattern = effect(Ripples)
    b = blender([pattern, EffectPattern(next_effect(Ripples)())])
    for t, frame in frames(b, 0, 2):
        pass
    assert len(pattern.effect.drops) >= 1
    painted = sum(c > 0.2 for c in pattern.effect.painted) / len(frame)
    assert painted > 0.1
    assert sum(max(light) > 0.06 * 255 for light in frame) / len(frame) > 0.1
