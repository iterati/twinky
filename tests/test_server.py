"""The simulator page's server: the layout, then the frames' exact bytes, the page's music messages,
the built page, and --sim."""
import http.client
import json
import os
import socket
import struct
import time

import pytest
from websockets.sync.client import connect

import layout
import twinky
from control import BasicBitch, CircusTent
from music import Sound
from server import Server
from sim import SimLights
from support import blender, frames, quiet

def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

@pytest.fixture
def running(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>twinky</title>")
    (dist / "assets" / "app.js").write_text("console.log('twinky')")
    (tmp_path / "secret.txt").write_text("not the page")
    b = blender([quiet(BasicBitch()), quiet(CircusTent())])
    server = Server(b, free_port(), str(dist))
    b.on_frame = server.send
    server.start()
    yield b, server
    server.stop()

def recorded(b, number: int) -> bytes:
    return b"".join(interface.frames[number] for interface in b.lights.interfaces)

def test_the_layout_comes_first(running):
    b, server = running
    list(frames(b, 0, 1))
    with connect(f"ws://127.0.0.1:{server.port}/ws") as ws:
        message = ws.recv(timeout=5)
    assert isinstance(message, str)
    lights = json.loads(message)["layout"]
    assert len(lights) == 800
    assert [(light["strand"], light["index"]) for light in lights] == [(s, i) for s in range(2) for i in range(400)]
    for light, pixel in zip(lights, b.pixels):
        assert (light["x"], light["y"], light["z"], light["angle"]) == (pixel.x, pixel.y, pixel.z, pixel.t)
        assert 0 <= light["y"] <= 1 and 0 <= light["angle"] <= 1

def test_then_each_frame_as_the_tree_is_sent_it(running):
    b, server = running
    list(frames(b, 0, 0.5))  # 8 frames before the page connects
    with connect(f"ws://127.0.0.1:{server.port}/ws") as ws:
        ws.recv(timeout=5)
        list(frames(b, 0.5, 2))
        messages = []
        while not messages or struct.unpack("<I", messages[-1][:4])[0] < 31:
            messages.append(ws.recv(timeout=5))
    numbers = [struct.unpack("<I", message[:4])[0] for message in messages]
    assert numbers[0] >= 8
    assert numbers == list(range(numbers[0], 32))
    for number, message in zip(numbers, messages):
        assert isinstance(message, bytes)
        assert len(message) == 4 + 3200
        assert message[4:] == recorded(b, number)
    assert any(message[4:] != messages[0][4:] for message in messages)

def test_a_pages_music_messages_reach_the_beat_clock(running):
    b, server = running
    fields = {"time": 100.0, "bpm": 128.0, "beat": 41.5, "bar": 10, "confidence": 0.8,
              "low": 0.7, "mid": 0.4, "high": 0.2, "tone": 0.6, "drive": 0.3}
    with connect(f"ws://127.0.0.1:{server.port}/ws") as ws:
        ws.recv(timeout=5)
        ws.send(json.dumps({"music": fields}))
        deadline = time.monotonic() + 5
        while b.beat.heard is None and time.monotonic() < deadline:
            time.sleep(0.01)
    assert b.beat.heard == Sound(**fields)

def get(port: int, path: str) -> http.client.HTTPResponse:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    return conn.getresponse()

def test_the_page_is_served(running):
    _, server = running
    page = get(server.port, "/")
    assert page.status == 200
    assert page.getheader("Content-Type") == "text/html"
    assert page.read() == b"<!doctype html><title>twinky</title>"
    script = get(server.port, "/assets/app.js?v=1")
    assert script.status == 200
    assert script.getheader("Content-Type") == "text/javascript"
    assert script.read() == b"console.log('twinky')"
    assert get(server.port, "/missing.js").status == 404
    assert get(server.port, "/../secret.txt").status == 404

def test_sim_plays_the_cone_or_a_layout(tmp_path, monkeypatch):
    monkeypatch.setattr(twinky, "Lights", lambda: "the real tree")
    assert twinky.open_lights([]) == "the real tree"

    cone = twinky.open_lights(["--sim"])
    assert isinstance(cone, SimLights)
    assert [i.layout for i in cone.interfaces] == layout.load(os.path.join(layout.LAYOUTS, "cone.json"))

    path = str(tmp_path / "tree.json")
    layout.save(path, layout.cone(strands=3, per_strand=50, seed=7))
    tree = twinky.open_lights(["--sim", path])
    assert isinstance(tree, SimLights)
    assert [i.layout for i in tree.interfaces] == layout.cone(strands=3, per_strand=50, seed=7)

def test_a_port_in_use_stops_twinky_as_it_starts():
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        server = Server(blender([quiet(BasicBitch()), quiet(CircusTent())]), taken.getsockname()[1])
        with pytest.raises(OSError):
            server.start()
