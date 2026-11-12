"""The music: the beat clock, the Music feature and its six links, on the simulated tree."""
import json
import math
import random

import pytest

import twinky
from colors import BaseColor
from core import wrap
from control import BasicBitch, Confetti, SlidingDoor, WiredPattern
from music import LET_GO, BeatClock, Sound
from support import FRAME, PATTERNS, blender, frames, in_range, quiet

def message(time: float, bpm: float=120.0, first: float=0.0, **fields) -> dict:
    """A music message as the page sends it: beats counted from first, on a clock shared with twinky."""
    beat = (time - first) * bpm / 60
    return {"time": time, "bpm": bpm, "beat": beat, "bar": int(beat // 4), "confidence": 0.9,
            "low": 0.5, "mid": 0.5, "high": 0.5, "tone": 0.5, "drive": 0.5} | fields

class FakeClock:
    """A beat clock that hears the music perfectly: at any time, the beat exactly, and bands, tone and
    drive from fields (each a number or a function of the time). Until `until`, then silence."""
    def __init__(self, bpm: float=120.0, first: float=0.0, until: float=math.inf, **fields):
        self.bpm = bpm
        self.first = first
        self.until = until
        self.fields = fields

    def at(self, t: float, latency: float=0.0) -> Sound | None:
        if t > self.until:
            return None
        fields = {name: value(t) if callable(value) else value for name, value in self.fields.items()}
        return Sound(**message(t - latency, self.bpm, self.first, **fields) | {"time": t})

def music(b, **picks):
    """Sets the Blender's Music controls by name: Streamers="every beat" and so on."""
    for control in b.music.controls:
        name = control.name.replace(" ", "_").lower()
        if name in picks:
            control.set([o.name for o in control.options].index(picks[name]))

def lit(name: str) -> WiredPattern:
    # one lit color over the whole tree, off the base hue's clock, so a flash shows as plain numbers
    pattern = WiredPattern(name, base_color=BaseColor(l=-0.2, blend=False))
    pattern.configured = True
    return pattern

def test_the_beat_clock_extrapolates_between_messages():
    clock = BeatClock()
    assert clock.at(100.0) is None
    clock.hear(message(100.0, bpm=120, first=95.0))
    assert clock.at(100.0).beat == pytest.approx(10.0)
    sound = clock.at(100.25)
    assert sound.beat == pytest.approx(10.5)
    assert sound.time == 100.25 and sound.bar == 2 and sound.bpm == 120
    # the next message picks up where the last one's extrapolation had got to
    clock.hear(message(100.5, bpm=120, first=95.0))
    assert clock.at(100.75).beat == pytest.approx(11.5)

@pytest.mark.parametrize("latency, beat", [(0.1, 10.3), (-0.1, 10.7), (0.15, 10.2), (-0.15, 10.8)])
def test_the_latency_control_shifts_the_beat(latency, beat):
    clock = BeatClock()
    clock.hear(message(100.0, bpm=120, first=95.0))
    assert clock.at(100.25, latency).beat == pytest.approx(beat)
    b = blender([lit("Lit"), lit("Other")])
    latencies = [o.value for o in b.music._latency.options]
    assert latencies[0] == 0 and min(latencies) == -0.15 and max(latencies) == 0.15
    assert sorted(latencies) == [ms / 1000 for ms in range(-150, 151, 25)]
    music(b, latency=f"{round(latency * 1000):+d} ms")
    b.beat = clock
    b.render(100.25)
    assert b.sound.beat == pytest.approx(beat)

def test_a_message_missing_a_field_is_refused():
    with pytest.raises(TypeError):
        BeatClock().hear({"time": 1.0, "bpm": 120})

@pytest.mark.parametrize("every", [1, 2, 4])
def test_streamers_launch_within_a_frame_of_each_beat(every):
    random.seed(2)
    confetti = quiet(Confetti(), streamers=True)
    confetti.features[0]._min.set(1)
    confetti.features[0]._delay.set(4)  # 1.5 s on its own timer
    confetti.update(set_dirty=False)
    b = blender([confetti, quiet(BasicBitch())])
    b.pixels = b.pixels[::20]  # the streamers launch the same, for a quicker render
    music(b, streamers={1: "every beat", 2: "every 2 beats", 4: "every bar"}[every])
    bpm, first = 128.0, 0.3
    b.beat = FakeClock(bpm, first)
    period = 60 / bpm
    seen = set()
    launches = []
    for t, _ in frames(b, 0, 20):
        new = set(b.run.streamers) - seen
        seen |= new
        launches += [(t, s) for s in new]
    beats = [first + (n * period) for n in range(0, 50, every) if first + (n * period) < 20 - (FRAME / 2)]
    launch_frames = sorted({t for t, _ in launches})
    assert len(launch_frames) == len(beats)
    for at, t in zip(beats, launch_frames):
        assert abs(t - at) <= FRAME / 2 + 1e-9
    for t, streamer in launches:
        assert any(abs(streamer.initial_t + b.run.start - at) < 1e-9 for at in beats)
    # each launch a quarter turn on from the last: a rotating cascade
    angles = {round(s.initial_t, 6): s.angle % 1 for _, s in launches}
    steps = [round((later - earlier) % 1, 6) for earlier, later in zip(list(angles.values()), list(angles.values())[1:])]
    assert set(steps) == {0.25}

def test_streamers_with_no_angle_of_their_own_step_round_the_trunk():
    random.seed(3)
    door = quiet(SlidingDoor(), streamers=True)
    door.features[0]._streamers.set(0)  # On
    door.update(set_dirty=False)
    b = blender([door, quiet(BasicBitch())])
    b.pixels = b.pixels[::20]
    b.beat = FakeClock(120.0, 0.0)
    angles = set()
    for _ in frames(b, 0, 6):
        angles |= {s.angle for s in b.run.streamers}
    assert angles == {0.0, 0.25, 0.5, 0.75}

def test_the_flash_lifts_the_tree_on_the_beat_and_decays_with_the_drive():
    b = blender([lit("Lit"), lit("Other")])
    b.beat = FakeClock(120.0, 0.0, drive=0.0)
    music(b, flash="whole tree", palette="Off")
    level = {t: sum(map(sum, frame)) / len(frame) for t, frame in frames(b, 0, 4)}
    base = level[0.25]  # mid-beat, the flash long gone
    for beat in [1.0, 1.5, 2.0, 3.5]:
        assert level[beat] > 1.5 * base
        assert level[beat + FRAME] < level[beat]
    # 400 ms of decay in groove, so it's over by 0.4 s after the beat
    assert level[1.0 + 0.4375] == pytest.approx(base)
    b.beat = FakeClock(120.0, 0.0, drive=1.0)
    snappy = {t: sum(map(sum, frame)) / len(frame) for t, frame in frames(b, 4, 6)}
    assert snappy[5.0 + 0.125] == pytest.approx(base)
    assert level[1.0 + 0.125] > 1.2 * base

def test_chasing_sectors_light_a_quarter_of_the_trunk_each_beat():
    b = blender([lit("Lit"), lit("Other")])
    b.beat = FakeClock(120.0, 0.0)
    music(b, flash="chasing sectors", palette="Off")
    dark = b.render(0.25)
    for n in [2, 3, 4, 5, 6]:  # a beat each half second
        b.render((n / 2) - FRAME)
        frame = b.render(n / 2)
        lifted = [p.t for p, light, before in zip(b.pixels, frame, dark) if sum(light) > sum(before) + 1]
        # a quarter turn on each beat, give or take the soft edge's half either side
        start = (n % 4) / 4
        assert all(((angle - start + 0.025) % 1) < 0.3 for angle in lifted)
        quarter = [p for p in b.pixels if ((p.t - start) % 1) < 0.25]
        assert len(lifted) > 0.95 * len(quarter)

def test_the_highs_quicken_the_sparkles_and_the_bands_set_their_height():
    random.seed(5)
    pattern = quiet(BasicBitch())
    sparkles = pattern.features[4]
    sparkles.controls[0].set(0)  # Enabled
    sparkles.controls[1].set(4)  # Start 1/4
    pattern.update(set_dirty=False)
    b = blender([pattern, quiet(SlidingDoor())])

    def rolls(clock) -> tuple[int, float]:
        b.beat = clock
        starts = set()
        heights = []
        for t, _ in frames(b, b._t + FRAME, b._t + 4):
            starts |= set(b.run.sparkles.values())
            heights += [b.pixels[i].y for i, lit in b.run.sparkles.items() if lit == t - b.run.start]
        return len(starts), sum(heights) / len(heights)

    off_rolls, _ = rolls(FakeClock(until=-1))
    assert off_rolls == pytest.approx(4 / 0.25, abs=1)
    bass_rolls, bass_height = rolls(FakeClock(high=0.0, low=1.0, mid=0.0))
    treble_rolls, treble_height = rolls(FakeClock(high=1.0, low=0.0, mid=0.0))
    assert bass_rolls == pytest.approx(off_rolls, abs=1)
    assert treble_rolls >= (4 / FRAME) - 2  # every frame, but the first, waiting out the last roll
    assert bass_height < 0.3 < 0.6 < treble_height

def test_the_palette_glides_toward_the_tones_anchor():
    b = blender([lit("Lit"), lit("Other")])
    clock_hue = b._blend_func
    for tone, anchor in [(1.0, 0.5), (0.0, 1.0)]:
        b.beat = FakeClock(tone=tone)
        hues = {t: (clock_hue(t) + b.hue_shift) % 1 for t, _ in frames(b, b._t + FRAME, b._t + 12)}
        times = sorted(hues)
        off = [abs(((hues[t] - anchor + 0.5) % 1) - 0.5) for t in times]
        assert off[-1] < 0.03  # there within about 8 s
        assert off[round(2 / FRAME)] > 0.05  # and not in a jump
        assert max(abs(((hues[a] - hues[b] + 0.5) % 1) - 0.5) for a, b in zip(times, times[1:])) < 0.02

def test_the_spin_locks_to_the_bar():
    b = blender([lit("Lit"), lit("Other")])
    b.beat = FakeClock(120.0, 0.3)
    for bars in [4, 8]:
        music(b, spin_lock=f"{bars} bars")
        for _ in frames(b, b._t + FRAME, b._t + 10):  # drawn round to its place in the bars
            pass
        start = b._t + FRAME
        turned = 0.0
        last = b.spin_angle
        for t, _ in frames(b, start, start + (bars * 2)):  # bars at 120 bpm take 2 s each
            turned += b.spin_angle - last
            last = b.spin_angle
            # a turn from every so many bar lines on
            assert abs(wrap(b.spin_angle - (b.sound.beat / (4 * bars)))) < 0.005
        assert turned == pytest.approx(1.0, abs=0.01)

def test_with_drive_a_change_lands_on_bar_lines_and_in_groove_it_is_long():
    b = blender([quiet(BasicBitch()), quiet(SlidingDoor())])
    b.beat = FakeClock(120.0, 0.3, drive=1.0)
    for _ in frames(b, 0, 62):
        pass
    change = b.change
    assert change is not None
    # bar lines every 2 s from 0.3 s: the first after 60 s is 60.3 s
    assert abs(change.start - 60.3) <= FRAME / 2
    assert change.length == pytest.approx(4.0)
    b.beat = FakeClock(120.0, 0.3, drive=0.0)
    for _ in frames(b, 70, 71):
        pass
    b.start_transition()
    assert b.change.length == pytest.approx(12.0)
    # a switch by hand in drive: the usual length, as it starts off the bar line
    b.beat = FakeClock(120.0, 0.3, drive=1.0)
    for _ in frames(b, 90, 91):
        pass
    b.start_transition(0)
    assert b.change.length == b.transition_length

def test_feel_snaps_the_sparkles_in_drive():
    b = blender([lit("Lit"), lit("Other")])
    b.run.sparkles = {0: 1.0}
    b.render(1.0)
    b.beat = FakeClock(drive=1.0)
    b.render(1.0 + FRAME)
    assert b._sparkle(b.run, 0, 1.0) == pytest.approx(1.0)
    b.beat = FakeClock(until=-1)
    b.render(1.0 + 2 * FRAME)
    assert b._sparkle(b.run, 0, 1.0) == pytest.approx(0.0)

def test_the_links_let_go_when_messages_stop():
    random.seed(6)
    confetti = quiet(Confetti(), streamers=True)
    confetti.features[0]._min.set(1)
    confetti.update(set_dirty=False)
    b = blender([confetti, quiet(BasicBitch())])
    b.pixels = b.pixels[::20]
    b.beat = BeatClock()
    music(b, palette="On", flash="whole tree")
    bpm = 120.0
    for k in range(round(10 / FRAME)):
        t = k * FRAME
        if t < 6 and k % 2 == 0:  # about 30 messages a second, for 6 s
            b.beat.hear(message(t, bpm, tone=1.0, high=1.0, drive=1.0))
        b.render(t)
        if t < 6:
            assert b.sound is not None and b.beating
        if t > 6 - (2 * FRAME) + LET_GO:
            assert b.sound is None
            assert not b.beating and b.on_beat is None
            assert b.sparkle_roll == b.sparkle_delay
            assert b._flash_at(t) == 0
            assert b._change_length() == b.transition_length
    # the streamers back on their own timer, the hue and the spin gliding home
    assert b.run.next_streamer > 9.5
    assert abs(wrap(b.hue_shift)) < 0.2
    assert abs(wrap(b.spin_angle)) < 0.15

def test_music_off_plays_the_patterns_as_they_were():
    random.seed(7)
    a = blender([quiet(SlidingDoor()), quiet(BasicBitch())])
    random.seed(7)
    b = blender([quiet(SlidingDoor()), quiet(BasicBitch())])
    b.beat = FakeClock(tone=1.0, high=1.0)
    b.music._on.set(1)  # Off
    assert b.music.visible_controls() == [b.music._on]
    for (_, fa), (_, fb) in zip(frames(a, 0, 3), frames(b, 0, 3)):
        assert fa == fb

def sound_fields(t: float) -> dict:
    # every field sweeping its range, so each link sees highs and lows, light and dark, drive and groove
    return {name: (math.sin(t * rate) + 1) / 2 for name, rate in [
        ("low", 1.3), ("mid", 0.7), ("high", 2.1), ("tone", 0.3), ("drive", 0.9), ("confidence", 0.5)]}

@pytest.mark.parametrize("cls", PATTERNS, ids=lambda cls: cls.__name__)
def test_every_frame_stays_finite_and_in_range_with_each_link_on(cls):
    random.seed(8)
    b = blender([cls(), PATTERNS[(PATTERNS.index(cls) + 1) % len(PATTERNS)]()])
    b.pattern_length = 8.0  # so a change comes through too
    b.pixels = b.pixels[::4]
    music(b, flash="chasing sectors", spin_lock="8 bars")
    b.beat = FakeClock(150.0, 0.1, **{name: (lambda t, n=name: sound_fields(t)[n]) for name in sound_fields(0)})
    changed = False
    for t, frame in frames(b, 0, 20):
        assert in_range(frame), f"{t}"
        changed |= b.transitioning
    assert changed

def test_every_option_of_the_music_feature_renders_finite():
    random.seed(9)
    b = blender([quiet(Confetti(), streamers=True), quiet(BasicBitch())])
    b.pixels = b.pixels[::4]
    b.beat = FakeClock(100.0, 0.2, **{name: (lambda t, n=name: sound_fields(t)[n]) for name in sound_fields(0)})
    t = 0.0
    for control in b.music.controls:
        for oidx in range(len(control.options)):
            control.set(oidx)
            for _, frame in frames(b, t, t + 1):
                assert in_range(frame), f"{control.name} {control.selected.name}"
            t += 1
        control.set(1 if control is not b.music._latency and control is not b.music._on else 0)

def test_the_menus_commands_reach_music_after_the_patterns_features():
    random.seed(10)
    b = blender([BasicBitch(), SlidingDoor()])
    b.pattern.dirty = False
    fidx = len(b.pattern.features)
    before = b.pattern._to_dict()
    twinky.set_option(fidx, 1, 2)(b)  # Streamers: every 2 beats
    twinky.change_option(fidx, 2, 1)(b)  # Flash: on to chasing sectors
    assert b.music._to_dict()["Streamers"] == "every 2 beats"
    assert b.music._to_dict()["Flash"] == "chasing sectors"
    twinky.set_option(fidx, 0, 1)(b)  # the - key: Off
    assert b.music.visible_controls() == [b.music._on]
    twinky.set_option(fidx, 0, 0)(b)  # the + key: On
    picks = b.music._to_dict()
    twinky.randomize_feature(fidx)(b)
    assert b.music._to_dict()["On"] == "On" and b.music._to_dict()["Latency"] == picks["Latency"]
    assert b.pattern._to_dict() == before and not b.pattern.dirty
    # an automatic change randomizes the next pattern, and leaves the music alone
    picks = b.music._to_dict()
    for _ in frames(b, 0, 62):
        pass
    assert b.transitioning and b.music._to_dict() == picks

def test_the_music_save_round_trips_by_name(tmp_path, monkeypatch):
    monkeypatch.setattr(twinky, "SAVES", str(tmp_path))
    b = blender([BasicBitch(), SlidingDoor()])
    twinky.load_music(b.music)  # none yet: the picks stay
    music(b, streamers="every bar", flash="off", feel="Off", latency="-75 ms")
    twinky.save_music(b)
    with open(tmp_path / "music.json") as file:
        saved = json.load(file)
    assert saved == {"Music": b.music._to_dict()}
    assert saved["Music"]["Latency"] == "-75 ms"
    other = blender([BasicBitch(), SlidingDoor()])
    twinky.load_music(other.music)
    assert other.music._to_dict() == b.music._to_dict()
    assert other.music.value["latency"] == -0.075
