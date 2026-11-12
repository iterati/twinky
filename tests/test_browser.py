"""The page's own engine, browser.py, as Pyodide runs it in the simulator page with no twinky.py: the
same frames, layout and state as twinky --sim gives, and the remote's commands."""
import json
import random
import struct

import pytest

import browser
import commands
import twinky
from core import FRAME
from server import Server
from wire import frame_message

T0 = 1000.0

@pytest.fixture(autouse=True)
def no_saves(tmp_path, monkeypatch):
    monkeypatch.setattr(commands, "SAVES", str(tmp_path / "saves"))

def sim_frames(seed: int, to: int | None, steps: int) -> list[bytes]:
    """twinky --sim's frames, as its animation thread gives them on the clock from T0."""
    random.seed(seed)
    animation = commands.start(twinky.open_lights(twinky.parse_args(["--sim"])))
    sent = []
    animation.on_frame = sent.append
    animation.init(T0)
    if to is not None:
        commands.remote_command({"command": "switch", "to": to})(animation)
    for k in range(steps):
        animation.write(animation.render(T0 + k * FRAME))
    return [frame_message(number, frame) for number, frame in enumerate(sent)]

def engine_frames(seed: int, to: int | None, steps: int) -> list[bytes]:
    random.seed(seed)
    engine = browser.Engine()
    engine.init(T0)
    if to is not None:
        engine.command(json.dumps({"command": "switch", "to": to}))
    return [engine.step(T0 + k * engine.frame) for k in range(steps)]

@pytest.mark.parametrize("to, name", [(None, "Basic Bitch"), (5, "Galaxus"), (18, "Fireworks")])
def test_the_engine_plays_the_frames_twinky_sim_does(to, name):
    expected = sim_frames(7, to, 112)
    assert engine_frames(7, to, 112) == expected
    assert [struct.unpack_from("<I", m)[0] for m in expected] == list(range(112))
    random.seed(7)
    engine = browser.Engine()
    engine.init(T0)
    if to is not None:
        engine.command(json.dumps({"command": "switch", "to": to}))
    for k in range(112):
        engine.step(T0 + k * FRAME)
    assert engine.blender.pattern.name == name

def test_the_engine_keeps_no_frames_and_gives_the_servers_layout():
    engine = browser.Engine()
    engine.init(T0)
    for k in range(5):
        message = engine.step(T0 + k * FRAME)
    assert len(message) == 4 + 4 * 800
    assert all(interface.frames == [] for interface in engine.blender.lights.interfaces)
    assert engine.layout == Server(engine.blender).layout

def test_the_state_comes_on_a_change_and_commands_run():
    engine = browser.Engine()
    engine.init(T0)
    engine.step(T0)
    state = json.loads(engine.changed_state())["state"]
    assert state["pattern"] == "Basic Bitch" and state["patterns"][18] == "Fireworks"
    engine.step(T0 + FRAME)
    assert engine.changed_state() is None
    engine.command(json.dumps({"command": "switch", "to": 18}))
    engine.step(T0 + 2 * FRAME)
    assert json.loads(engine.changed_state())["state"]["to"] == "Fireworks"
    # a knob, as the page's picker sends it: the pattern's first feature's first control
    feature = engine.blender.pattern.features[0]
    control = feature.visible_controls()[0]
    option = (control.selected_idx + 1) % len(control.options)
    engine.command(json.dumps({"command": "set", "pattern": engine.blender.pattern.name, "feature": 0,
                               "control": 0, "name": control.name, "option": option}))
    assert control.selected_idx == option
