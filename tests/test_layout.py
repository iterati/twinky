"""The simulated tree's cone, normalizing a layout, and the strands it's sent on."""
import math
import os
import random
from statistics import median

import pytest

import layout
from core import Blender
from sim import FakeInterface, SimLights
from support import PATTERNS, frames

def angle(light) -> float:
    return ((math.atan2(light["z"], light["x"]) / math.pi) + 1) / 2

def turn_apart(a: float, b: float) -> float:
    d = abs(a - b) % 1
    return min(d, 1 - d)

def test_the_cone():
    strands = layout.load(os.path.join(layout.LAYOUTS, "cone.json"))
    assert strands == layout.cone()
    assert [len(strand) for strand in strands] == [400, 400]
    for strand in strands:
        for light in strand:
            surface = 0.38 * (1 - light["y"])
            assert 0 < light["y"] < 1
            assert 0.55 * surface - 1e-12 <= math.hypot(light["x"], light["z"]) <= surface + 1e-12

def test_normalizing_the_cone_changes_nothing():
    lights = [light for strand in layout.cone() for light in strand]
    out = layout.normalize(lights)
    assert max(abs(a["y"] - b["y"]) for a, b in zip(lights, out)) < 0.015
    errors = [turn_apart(angle(a), angle(b)) for a, b in zip(lights, out) if a["y"] < 0.9]
    assert median(errors) < 0.002
    assert max(errors) < 0.02

def test_normalizing_keeps_the_cone_s_top_and_bottom_apart():
    # the lights past the 1st and 99th percentiles keep their order and spacing, never stacking
    # onto one height at the tip or the foot
    lights = [light for strand in layout.load(os.path.join(layout.LAYOUTS, "cone.json"))
              for light in strand]
    out = layout.normalize(lights)
    order = sorted(range(len(lights)), key=lambda i: lights[i]["y"])
    ends = int(len(lights) * 0.01) + 1
    for end in [order[:ends], order[-ends:]]:
        for a, b in zip(end, end[1:]):
            assert out[b]["y"] - out[a]["y"] >= 0.5 * (lights[b]["y"] - lights[a]["y"]) > 0

def test_normalizing_puts_strays_far_off_the_tree_at_its_ends():
    # the Twinkly app's estimate can put a light or two far above or below the tree: they land at
    # the ends and the tree still runs over nearly all of 0 to 1
    true = [light for strand in layout.cone() for light in strand]
    lights = true + [{"x": 0.0, "y": 3.0, "z": 0.0}, {"x": 0.1, "y": 2.5, "z": 0.0},
                     {"x": 0.0, "y": -2.0, "z": 0.1}]
    out = layout.normalize(lights)
    assert [light["y"] for light in out[len(true):]] == [1.0, 1.0, 0.0]
    tree = [light["y"] for light in out[:len(true)]]
    assert min(tree) < 0.002 and max(tree) > 0.998
    assert max(abs(a["y"] - b["y"]) for a, b in zip(true, out)) < 0.002

def test_normalizing_puts_a_shifted_trunk_back(caplog):
    # as the app might estimate the cone: the trunk off by (0.10, -0.07), a lean of 0.08, the height
    # squashed to 0.08-0.88 and 1.5% of the lights flung out
    rnd = random.Random(5)
    true = [light for strand in layout.cone() for light in strand]
    estimate, flung = [], set()
    for i, light in enumerate(true):
        x = light["x"] + 0.10 + (0.08 * light["y"])
        z = light["z"] - 0.07
        if rnd.random() < 0.015:
            x += rnd.choice([-1, 1]) * rnd.uniform(0.3, 0.5)
            z += rnd.uniform(-0.3, 0.3)
            flung.add(i)
        estimate.append({"x": x, "y": 0.08 + (light["y"] * 0.8), "z": z})
    before = [turn_apart(angle(a), angle(b)) for a, b in zip(true, estimate) if a["y"] < 0.9]
    with caplog.at_level("INFO", logger="layout"):
        out = layout.normalize(estimate)
    count, pulled = caplog.records[0].args
    assert "stray lights" in caplog.text and count == len(pulled)
    # the ones flung only a little stay inside 1.5 times the median radius, and stay put
    assert set(pulled) <= flung and len(pulled) >= 0.8 * len(flung)
    errors = [turn_apart(angle(a), angle(b)) for i, (a, b) in enumerate(zip(true, out))
              if a["y"] < 0.9 and i not in flung]
    assert median(before) > 0.05
    assert median(errors) < 0.005
    assert max(abs(a["y"] - b["y"]) for a, b in zip(true, out)) < 0.02
    for i in flung:
        surface = 0.38 * (1 - true[i]["y"])
        assert math.hypot(out[i]["x"], out[i]["z"]) < 1.2 * surface + 0.01

def test_frames_go_to_every_strand_by_its_own_length():
    lights = SimLights()
    lights.interfaces = [FakeInterface(strand) for strand in layout.cone(strands=3, per_strand=150)]
    b = Blender([PATTERNS[0](), PATTERNS[1]()], lights, 0)
    b.init(0)
    for _ in frames(b, 0, 1):
        pass
    assert len(b.pixels) == 450
    assert [len(interface.frames[-1]) for interface in lights.interfaces] == [600, 600, 600]
    assert all(interface.mode == "rt" for interface in lights.interfaces)

@pytest.mark.parametrize("strand", [0, 1])
def test_pixels_take_the_normalized_layout(strand):
    b = Blender([PATTERNS[0](), PATTERNS[1]()], SimLights(), 0)
    start = 400 * strand
    for pixel, light in zip(b.pixels[start:start + 400], layout.cone()[strand]):
        assert turn_apart(pixel.t, angle(light)) < 0.02 or light["y"] >= 0.9
