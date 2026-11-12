"""The modulator port: its waves checked by hand against motion.ts, the phase spread round the trunk,
and the glide."""
import math

import pytest

from motion import MEMBERS, Modulator, Running, Target, follow, wave

def mod(name: str, **kwargs) -> Modulator:
    return Modulator("m", name, 4, **kwargs)

def test_cos_starts_at_1_and_falls_to_0_halfway():
    m = mod("cos")
    assert [wave(m, p) for p in [0, 0.25, 0.5, 0.75, 1, 2.5, -0.25]] == pytest.approx([1, 0.5, 0, 0.5, 1, 0, 0.5])

def test_tri_starts_at_1_and_runs_straight_to_0_and_back():
    m = mod("tri")
    assert [wave(m, p) for p in [0, 0.125, 0.25, 0.5, 0.75, 0.9, 1.25]] == pytest.approx(
        [1, 0.75, 0.5, 0, 0.5, 0.8, 0.5])

def test_ramp_runs_0_to_1_each_cycle():
    m = mod("ramp")
    assert [wave(m, p) for p in [0, 0.3, 0.999, 1, 3.6, -0.25]] == pytest.approx([0, 0.3, 0.999, 0, 0.6, 0.75])

def test_steps_hold_each_step_for_its_share_of_the_cycle():
    m = mod("steps", steps=[0, 1, 0.25, 0.75])
    assert [wave(m, p) for p in [0, 0.24, 0.25, 0.5, 0.74, 0.75, 0.99, 1.1]] == [0, 0, 1, 0.25, 0.25, 0.75, 0.75, 0]

def test_beat_is_its_two_harmonics_folded():
    # |cos(2π·f·a)·cos(2π·f·b)·0.5 - 0.5|: 0 where both cosines are 1 or both -1, 1 where one is
    # 1 and the other -1
    m = mod("beat", harmonics=(1, 2))
    assert wave(m, 0) == pytest.approx(0)
    assert wave(m, 0.5) == pytest.approx(1)  # cos(π)·cos(2π) = -1
    assert wave(m, 0.25) == pytest.approx(0.5)  # cos(π/2) = 0
    assert wave(m, 1 / 3) == pytest.approx(abs(math.cos(2 * math.pi / 3) * math.cos(4 * math.pi / 3) * 0.5 - 0.5))
    m = mod("beat", harmonics=(3, 5))
    assert wave(m, 0.1) == pytest.approx(abs(math.cos(0.6 * math.pi) * math.cos(math.pi) * 0.5 - 0.5))

def test_the_phase_runs_a_cycle_each_period_in_beats():
    running = Running(mod("ramp"), Target("x", 1))
    for _ in range(3):
        running.advance(1, 0.5)
    assert running.phase == pytest.approx(0.75)
    assert running.at(0) == pytest.approx(0.75)
    running.advance(2, 0.5)
    assert running.phase == pytest.approx(0.25)

def test_the_modulators_phase_and_depth():
    running = Running(mod("cos", phase=0.5), Target("x", 0.3))
    running.advance(0, 0)
    # the phase puts the cos at its trough, and the depth takes it 0.3 under the knob's base
    assert running.at(0) == pytest.approx(0)
    assert running.offset(0) == pytest.approx(-0.3)

def test_a_spread_by_angle_is_a_wave_travelling_round_the_trunk():
    # a phase spread of 1 round the trunk: one cos round the tree, its peak where the phase puts it,
    # moving a quarter turn back each beat of a 4 beat period, and no seam at angle 0
    running = Running(mod("cos"), Target("x", 1, phase_spread=1))
    angles = [i / 360 for i in range(360)]
    peaks = []
    for _ in range(4):
        running.advance(1, 0.25)
        values = [running.at(a) for a in angles]
        peaks.append(angles[values.index(max(values))])
        assert running.at(0) == pytest.approx(running.at(1), abs=1e-9)
        assert max(abs(values[i] - values[i - 1]) for i in range(1, 360)) < 0.02
    assert peaks == pytest.approx([0.75, 0.5, 0.25, 0.0], abs=1 / 360)

def test_a_light_between_two_members_reads_between_them():
    running = Running(mod("ramp"), Target("x", 1, phase_spread=0.5))
    running.advance(0, 0)
    assert running.at(0.5 / MEMBERS) == pytest.approx(0.25 / MEMBERS)
    assert running.at(1) == pytest.approx(0.5)

def test_glide_decays_as_exp_of_minus_dt_over_glide():
    assert follow(None, 0.4, 2, 0.1) == 0.4
    assert follow(1.0, 0.0, 0, 0.1) == 0.0
    assert follow(1.0, 0.0, 2, 0.5) == pytest.approx(math.exp(-0.25))
    assert follow(0.2, 1.0, 0.5, 1) == pytest.approx(1 - 0.8 * math.exp(-2))
    # a step in a glided steps wave: the light eases to the new step, a share each frame
    running = Running(mod("steps", steps=[0, 1], glide=1), Target("x", 1))
    running.advance(0, 1 / 16)
    assert running.at(0) == 0
    values = []
    for beats in [2.4, 0, 0, 0]:
        running.advance(beats, 1 / 16)  # past the step at half the 4 beat cycle, then held there
        values.append(running.at(0))
    assert values == pytest.approx([1 - math.exp(-k / 16) for k in range(1, 5)])
