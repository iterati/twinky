"""twinky's server, on one port: the built pages (web/dist) over HTTP, the simulator at / and the
remote at /remote. At /ws the simulator gets the layout, then every frame's bytes as the tree is sent
them, and sends its music messages; at /ws?remote the remote gets twinky's state whenever it changes
and the time 4 times a second, and sends the TUI's commands."""
import asyncio
import email.utils
import json
import mimetypes
import os
import struct
import threading
from typing import Callable

from websockets.asyncio.server import ServerConnection, broadcast, serve
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosedError
from websockets.http11 import Request, Response

from control import Feature, ToggleControl

PORT = 8016
DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "dist")
REMOTE = "/ws?remote"
TIME_EVERY = 0.25
# a feature's first control by one of these names is its On switch, on the remote's card header
SWITCHES = ["Enabled", "On"]

def feature_state(feature: Feature) -> dict:
    controls = feature.visible_controls()
    first = controls[0]
    switch = isinstance(first, ToggleControl) and first.name in SWITCHES
    return {
        "name": feature.name,
        "on": first.value if switch else None,
        "controls": [
            {"name": c.name, "options": [o.name for o in c.options], "pick": c.selected_idx}
            for c in controls
        ],
    }

def remote_state(blender) -> dict:
    """What the remote shows: the patterns, the current one with its mark and the change running, its
    features with their visible controls and the Music feature after them, as the TUI lists them, the
    pause and the spin ring's angle."""
    return {
        "patterns": [p.name for p in blender.patterns],
        "pattern": blender.pattern.name,
        "mark": blender.mark,
        "to": blender.change.run.pattern.name if blender.change is not None else None,
        "features": [feature_state(f) for f in blender.pattern.features + [blender.music]],
        "paused": blender.pause_change,
        "ring": blender.ring_angle,
    }

class Server:
    """Runs on its own event loop in its own thread. A page gets the layout as it connects, then one
    binary message a frame: the frame number (4 bytes, little-endian) and W, R, G, B a light. A page
    listening to music sends {"music": {...}} as text, the fields of music.Sound, for the beat clock.
    A remote gets {"state": {...}} as it connects and on every change, and {"time": "..."}, the TUI's
    time text; on_command takes its commands, {"command": "switch", ...} and so on, on this thread."""
    def __init__(self,
                 blender,
                 port: int=PORT,
                 dist: str=DIST,
                 host: str="localhost",
                 on_command: Callable[[dict], None] | None=None):
        # every light where Pixel has it, after normalizing: x, y (its height, 0 to 1) and z, its
        # strand and index on the strand, and its angle round the trunk (0 to 1)
        places = [(strand, index)
                  for strand, interface in enumerate(blender.lights.interfaces)
                  for index in range(len(interface.layout))]
        self.layout = json.dumps({"layout": [
            {"x": pixel.x, "y": pixel.y, "z": pixel.z, "strand": strand, "index": index, "angle": pixel.t}
            for pixel, (strand, index) in zip(blender.pixels, places)
        ]})
        self.blender = blender
        self.beat = blender.beat
        self.port = port
        self.dist = dist
        self.host = host
        self.on_command = on_command
        self.clients: set[ServerConnection] = set()
        self.remotes: set[ServerConnection] = set()
        self.number = 0
        self.state: str | None = None  # the last state sent
        self.next_time = 0.0
        self.loop = asyncio.new_event_loop()

    def start(self):
        # opened on the caller's thread, so a port in use stops twinky as it starts
        self.server = self.loop.run_until_complete(self._open())
        self.thread = threading.Thread(target=self.loop.run_forever, name="server")
        self.thread.start()

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()
        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())
        self.loop.close()

    def send(self, frame: bytes):
        """Takes a frame from the animation thread, and with it, reads the state there."""
        message = struct.pack("<I", self.number) + frame
        self.number += 1
        self.loop.call_soon_threadsafe(broadcast, self.clients, message)
        state = json.dumps({"state": remote_state(self.blender)})
        if state != self.state:
            self.state = state
            self.loop.call_soon_threadsafe(broadcast, self.remotes, state)
        t = self.blender._t
        if t >= self.next_time:
            self.next_time += TIME_EVERY
            if self.next_time <= t:
                self.next_time = t + TIME_EVERY
            self.loop.call_soon_threadsafe(broadcast, self.remotes, json.dumps({"time": self.blender.time_str}))

    async def _open(self):
        # serve wants the loop running as it's made
        return await serve(self._connect, self.host, self.port, process_request=self._page)

    async def _connect(self, connection: ServerConnection):
        if connection.request.path == REMOTE:
            clients = self.remotes
            clients.add(connection)
            if self.state is not None:
                await connection.send(self.state)
        else:
            clients = self.clients
            await connection.send(self.layout)
            clients.add(connection)
        try:
            async for message in connection:
                message = json.loads(message)
                if "music" in message:
                    self.beat.hear(message["music"])
                else:
                    self.on_command(message)
        except ConnectionClosedError:
            pass  # a page gone without closing, as a tab closing can
        finally:
            clients.discard(connection)

    def _page(self, connection: ServerConnection, request: Request) -> Response | None:
        path = request.path.split("?")[0]
        if path == "/ws":
            return None
        file = os.path.normpath(os.path.join(self.dist, path.lstrip("/") or "index.html"))
        if os.path.isdir(file):
            file = os.path.join(file, "index.html")  # /remote
        if not file.startswith(self.dist + os.sep) or not os.path.isfile(file):
            return connection.respond(404, "Not found (pnpm build makes the page)\n")
        with open(file, "rb") as f:
            body = f.read()
        headers = Headers([
            ("Date", email.utils.formatdate(usegmt=True)),
            ("Connection", "close"),
            ("Content-Length", str(len(body))),
            ("Content-Type", mimetypes.guess_type(file)[0]),
        ])
        return Response(200, "OK", headers, body)
