"""Every pattern on the simulated tree: through a change, under every option, and round the seam."""
import random

import pytest

from core import Pixel
from support import PATTERNS, FRAME, blender, frames, in_range, quiet

def name(cls) -> str:
    return cls.__name__

def next_pattern(cls):
    return PATTERNS[(PATTERNS.index(cls) + 1) % len(PATTERNS)]

@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("cls", PATTERNS, ids=name)
def test_pattern_through_a_change(cls, seed):
    # 60 s of the pattern, its 6 s change into the next one, and 4 s after
    random.seed(seed)
    other = next_pattern(cls)
    b = blender([cls(), other()])
    changed = False
    for t, frame in frames(b, 0, 70):
        assert len(frame) == 800
        assert in_range(frame), f"{t}"
        assert [len(interface.frames[-1]) for interface in b.lights.interfaces] == [1600, 1600]
        changed |= b.transitioning
    assert changed
    assert b.pattern.name == other().name

@pytest.mark.parametrize("cls", PATTERNS, ids=name)
def test_every_option_of_every_control(cls):
    random.seed(4)
    pattern = cls()
    b = blender([pattern, next_pattern(cls)()])
    t = 0.0
    for fidx, feature in enumerate(pattern.features):
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

@pytest.mark.parametrize("cls", PATTERNS, ids=name)
def test_seam_at_angle_0(cls):
    # with the effects off, lights just either side of angle 0 at the same height agree, as the
    # patterns move: angle 0 is no edge
    random.seed(5)
    b = blender([quiet(cls(), streamers=True), next_pattern(cls)()])
    eps = 0.0002
    b.pixels = []
    for i in range(19):
        for t in [eps, 1 - eps]:
            pixel = Pixel(len(b.pixels), -1.0, (i + 1) / 20, 0.0)
            pixel.t = t
            b.pixels.append(pixel)
    worst = 0.0
    for _, frame in zip(range(160), frames_every(b, 0.25)):
        for a, c in zip(frame[0::2], frame[1::2]):
            worst = max(worst, *(abs(x - y) for x, y in zip(a, c)))
    assert worst <= 16

def frames_every(b, step):
    t = 0.0
    while True:
        yield b.render(t)
        t += step
