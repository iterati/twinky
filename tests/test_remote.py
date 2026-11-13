"""The remote: its state messages and the time, its commands on the TUI's queue, the spin ring,
--remote's address, and /remote with its manifest and icons."""
import http.client
import json
import os
import shutil
import socket
import struct
from queue import Queue

import pytest
from websockets.sync.client import connect

import commands
import twinky
from control import BasicBitch, CircusTent
from server import Server, remote_state
from support import FRAME, blender, frames, quiet

PUBLIC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "public", "remote")

def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

@pytest.fixture
def running(tmp_path, monkeypatch):
    monkeypatch.setattr(commands, "SAVES", str(tmp_path / "saves"))
    dist = tmp_path / "dist"
    (dist / "remote").mkdir(parents=True)
    (dist / "remote" / "index.html").write_text("<!doctype html><title>Twinky</title>")
    for name in os.listdir(PUBLIC):
        shutil.copy(os.path.join(PUBLIC, name), dist / "remote" / name)
    b = blender([BasicBitch(), CircusTent()])
    b.pattern.dirty = False
    queue = Queue()
    server = Server(b, free_port(), str(dist), on_command=lambda message: queue.put(commands.remote_command(message)))
    b.on_frame = server.send
    server.start()
    step(b)
    yield b, server, queue
    server.stop()

def step(b):
    # the animation thread's next frame, which sends the state if it changed
    t = b._t + FRAME
    b.write(b.render(t))

def remote(server):
    return connect(f"ws://127.0.0.1:{server.port}/ws?remote")

def next_state(ws) -> dict:
    # the time messages between are skipped
    while True:
        message = json.loads(ws.recv(timeout=5))
        if "state" in message:
            return message["state"]

def run(b, queue):
    """What the animation thread does with the next command on the queue, then its frame."""
    command = queue.get(timeout=5)
    command(b)
    step(b)
    return command

def inner(command):
    # the TUI's closure inside a feature command's check
    return dict(zip(command.__code__.co_freevars, (cell.cell_contents for cell in command.__closure__)))["func"]

def test_the_state_holds_the_pattern_its_features_and_music(running):
    b, server, _ = running
    with remote(server) as ws:
        state = next_state(ws)
    assert state["patterns"] == ["Basic Bitch", "Circus Tent"]
    assert state["pattern"] == "Basic Bitch" and state["to"] is None
    assert state["paused"] is False and state["ring"] == 0.0
    features = b.pattern.features + [b.music]
    assert [f["name"] for f in state["features"]] == [f.name for f in features]
    assert state["features"][-1]["name"] == "Music"
    for sent, feature in zip(state["features"], features):
        controls = feature.visible_controls()
        assert [c["name"] for c in sent["controls"]] == [c.name for c in controls]
        for c, control in zip(sent["controls"], controls):
            assert c["options"] == [o.name for o in control.options]
            assert c["pick"] == control.selected_idx
    # Pulse, Flicker and the rest open on their Enabled switch, Music on its On; Blend has none
    switches = {f["name"]: f["switch"] for f in state["features"]}
    assert switches["Pulse"] == 0 and switches["Music"] == 0 and switches["Blend"] is None
    # the walk's knobs, at jump in these tests
    assert state["walk"] == {
        "pace": {"name": "Pace", "options": ["slow", "easy", "brisk", "fast"], "pick": 1},
        "reach": {"name": "Reach", "options": ["near", "far", "any", "jump"], "pick": 3},
        "stay": False,
        "pins": [],
        "back": False,
    }

def test_the_mark_for_a_pattern_unsaved_saved_and_changed(running):
    b, server, queue = running
    with remote(server) as ws:
        assert next_state(ws)["mark"] == "?"
        ws.send(json.dumps({"command": "save"}))
        run(b, queue)
        assert next_state(ws)["mark"] == "!"
        ws.send(json.dumps({"command": "change", "pattern": "Basic Bitch", "feature": 5, "control": 0,
                            "name": "Transition", "step": 1}))
        run(b, queue)
        assert next_state(ws)["mark"] == "*"

def test_the_paused_flag_and_the_time_say_so(running):
    b, server, queue = running
    with remote(server) as ws:
        assert next_state(ws)["paused"] is False
        ws.send(json.dumps({"command": "pause"}))
        run(b, queue)
        assert next_state(ws)["paused"] is True
        for _ in frames(b, b._t + FRAME, b._t + 0.5):
            pass
        message = json.loads(ws.recv(timeout=5))
        while "time" not in message:
            message = json.loads(ws.recv(timeout=5))
        assert message["time"].startswith("(PAUSED)")

def check_switch(b, state):
    assert state["to"] == "Circus Tent" and b.transitioning

def check_random(b, state):
    assert state["to"] == "Circus Tent"

def check_pause(b, state):
    assert state["paused"] is True

def check_save(b, state):
    assert state["mark"] == "!" and os.path.exists(commands.save_path(b.pattern))

def check_save_music(b, state):
    assert os.path.exists(commands.music_path())

def check_spin(b, state):
    assert state["ring"] == 0.25 and b.ring_angle == 0.25

def check_randomize_pattern(b, state):
    assert state["mark"] == "*"

def check_randomize_feature(b, state):
    assert state["mark"] == "*"

def check_change(b, state):
    # Blend's Transition, from crossfade one on to sweep round
    assert state["features"][5]["controls"][0]["pick"] == 1 and b.pattern.transition == "sweep"

def check_set(b, state):
    # Music's Flash: chasing sectors
    assert state["features"][6]["controls"][2]["pick"] == 2 and b.music.value["flash"] == "chase"

def check_pace(b, state):
    # easy, one on to brisk
    assert state["walk"]["pace"]["pick"] == 2 and b.walk.pace.value == (2.0, 2)

def check_reach(b, state):
    # jump, one back to any
    assert state["walk"]["reach"]["pick"] == 2 and not b.walk.jumping

def check_stay(b, state):
    assert state["walk"]["stay"] is True and b.walk.stay.value

def check_pin(b, state):
    assert state["walk"]["pins"] == [1] and b.walk.pins == {1}

def check_back(b, state):
    # with no step to undo, nothing: the nudge test undoes one
    assert not b.walk.back_steps and not b.transitioning

def check_nudge(b, state):
    # at jump, the pattern's change
    assert state["to"] == "Circus Tent" and state["walk"]["back"] is True

@pytest.mark.parametrize("message, closure, check", [
    ({"command": "switch", "to": 1}, "switch_pattern.<locals>.func", check_switch),
    ({"command": "random"}, commands.random_pattern, check_random),
    ({"command": "pause"}, commands.pauseplay, check_pause),
    ({"command": "save"}, commands.toggle_configured, check_save),
    ({"command": "save music"}, commands.save_music, check_save_music),
    ({"command": "spin", "angle": 0.25}, "spin_ring.<locals>.func", check_spin),
    ({"command": "randomize"}, commands.randomize_pattern, check_randomize_pattern),
    ({"command": "randomize", "pattern": "Basic Bitch", "feature": 1},
     "randomize_feature.<locals>.func", check_randomize_feature),
    ({"command": "change", "pattern": "Basic Bitch", "feature": 5, "control": 0, "name": "Transition", "step": 1},
     "change_option.<locals>.func", check_change),
    ({"command": "set", "pattern": "Basic Bitch", "feature": 6, "control": 2, "name": "Flash", "option": 2},
     "set_option.<locals>.func", check_set),
    ({"command": "pace", "step": 1}, "walk_pace.<locals>.func", check_pace),
    ({"command": "reach", "step": -1}, "walk_reach.<locals>.func", check_reach),
    ({"command": "stay"}, commands.toggle_stay, check_stay),
    ({"command": "pin", "pattern": "Basic Bitch", "feature": 1}, "toggle_pin.<locals>.func", check_pin),
    ({"command": "back"}, commands.walk_back, check_back),
    ({"command": "nudge"}, commands.nudge, check_nudge),
], ids=["switch", "random", "pause", "save", "save music", "spin", "randomize", "randomize feature",
        "change", "set", "pace", "reach", "stay", "pin", "back", "nudge"])
def test_each_command_puts_the_tuis_own_closure_on_the_queue(running, message, closure, check):
    b, server, queue = running
    b.pattern.features[5].controls[0].set(0)
    b.pattern.update(set_dirty=False)
    step(b)
    with remote(server) as ws:
        next_state(ws)
        ws.send(json.dumps(message))
        command = run(b, queue)
        if "feature" in message:
            command = inner(command)
        if isinstance(closure, str):
            assert command.__qualname__ == closure
        else:
            assert command is closure
        # Music's save is no change to the state, nor Back with no step
        check(b, None if message["command"] in ["save music", "back"] else next_state(ws))

def test_a_command_for_a_pattern_or_control_no_longer_shown_is_dropped(running):
    b, server, queue = running
    picks = b.pattern._to_dict()

    def music(control: int, name: str, option: int):
        ws.send(json.dumps({"command": "set", "pattern": "Basic Bitch", "feature": 6, "control": control,
                            "name": name, "option": option}))
        run(b, queue)

    with remote(server) as ws:
        next_state(ws)
        # meant for Circus Tent
        ws.send(json.dumps({"command": "change", "pattern": "Circus Tent", "feature": 5, "control": 0,
                            "name": "Transition", "step": 1}))
        run(b, queue)
        ws.send(json.dumps({"command": "pin", "pattern": "Circus Tent", "feature": 1}))
        run(b, queue)
        # Music's Streamers, gone once Music is off, then the control after On once it is back
        music(0, "On", 1)
        assert next_state(ws)["features"][6]["controls"][0]["pick"] == 1
        music(1, "Streamers", 0)
        music(0, "On", 0)
        music(1, "Flash", 0)
    assert b.pattern._to_dict() == picks and not b.pattern.dirty and b.walk.pins == set()
    assert b.music.value["streamers"] == 1 and b.music.value["flash"] == "tree"

def test_nudge_then_back_from_the_remote(running):
    b, server, queue = running
    with remote(server) as ws:
        next_state(ws)
        ws.send(json.dumps({"command": "nudge"}))
        run(b, queue)
        state = next_state(ws)
        assert state["to"] == "Circus Tent" and state["walk"]["back"] is True
        ws.send(json.dumps({"command": "back"}))
        run(b, queue)
        state = next_state(ws)
        assert state["to"] == "Basic Bitch" and state["walk"]["back"] is False

def test_a_command_queued_by_the_tui_sends_the_same_state(running):
    b, server, queue = running
    with remote(server) as phone, remote(server) as other:
        next_state(phone)
        next_state(other)
        phone.send(json.dumps({"command": "pause"}))
        run(b, queue)
        paused = next_state(phone)
        assert next_state(other) == paused
        # the TUI's space, twice
        queue.put(commands.pauseplay)
        run(b, queue)
        assert next_state(phone)["paused"] is False
        next_state(other)
        queue.put(commands.pauseplay)
        run(b, queue)
        assert next_state(phone) == paused == remote_state(b)
        assert next_state(other) == paused

def test_the_time_comes_4_times_a_second(running):
    b, server, _ = running
    with remote(server) as ws:
        next_state(ws)
        # from the second frame, at 1/8 s, to 2 1/8 s
        for _ in frames(b, b._t + FRAME, b._t + 2 + FRAME):
            pass
        times = []
        try:
            while True:
                message = json.loads(ws.recv(timeout=0.5))
                if "time" in message:
                    times.append(message["time"])
        except TimeoutError:
            pass
    # each quarter second, the pattern's time left
    assert times == [f"-{60 - (k / 4):.2f}" for k in range(1, 9)]

def test_a_simulator_page_gets_no_state(running):
    b, server, _ = running
    with connect(f"ws://127.0.0.1:{server.port}/ws") as ws:
        assert "layout" in json.loads(ws.recv(timeout=5))
        step(b)
        assert isinstance(ws.recv(timeout=5), bytes)

def test_the_spin_ring_turns_every_light_and_stays():
    b = blender([quiet(CircusTent()), quiet(BasicBitch())])
    b.pattern.spin = 0
    t = 1.0
    plain = b.render(t)
    commands.spin_ring(0.3)(b)
    ringed = b.render(t)
    # as far round as the pattern's own spin would turn it
    commands.spin_ring(0.0)(b)
    b.pattern.spin = 0.3
    spun = b.render(t)
    flat = lambda frame: [c for light in frame for c in light]
    assert flat(ringed) == pytest.approx(flat(spun))
    assert flat(ringed) != pytest.approx(flat(plain))
    b.pattern.spin = 0
    commands.spin_ring(0.3)(b)
    for _ in frames(b, t + FRAME, t + 5):
        pass
    assert b.ring_angle == 0.3

def test_the_address_is_localhost_without_remote_and_every_interface_with_it():
    assert twinky.listen_host(twinky.parse_args([])) == "localhost"
    assert twinky.listen_host(twinky.parse_args(["--sim", "--remote"])) == "0.0.0.0"

def get(port: int, path: str) -> http.client.HTTPResponse:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    return conn.getresponse()

def png_size(data: bytes) -> tuple[int, int]:
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])

def test_the_remote_its_manifest_and_icons_are_served(running):
    _, server, _ = running
    for path in ["/remote", "/remote/"]:
        page = get(server.port, path)
        assert page.status == 200
        assert page.getheader("Content-Type") == "text/html"
        assert page.read() == b"<!doctype html><title>Twinky</title>"
    response = get(server.port, "/remote/manifest.webmanifest")
    assert response.status == 200
    assert response.getheader("Content-Type") == "application/manifest+json"
    manifest = json.loads(response.read())
    assert manifest["name"] == "Twinky"
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "/remote" and manifest["scope"] == "/remote"
    sizes = set()
    for icon in manifest["icons"]:
        response = get(server.port, icon["src"])
        assert response.status == 200 and response.getheader("Content-Type") == "image/png"
        width, height = png_size(response.read())
        assert icon["sizes"] == f"{width}x{height}"
        sizes.add(width)
    assert sizes == {192, 512}
