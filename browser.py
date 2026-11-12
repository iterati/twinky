"""twinky's engine in the simulator page, run by Pyodide in a worker when no twinky.py answers: the
rotation on the simulated cone as twinky --sim starts it, a frame at a time on the clock --sim plays
on, each frame as the server sends it, and the remote's commands. It and what it imports reach for no
device, socket, thread or TUI: those stay in device.py, server.py and twinky.py."""
import json
import time

import commands
from core import FRAME
from sim import SimLights
from wire import frame_message, layout_message, remote_state

class Engine:
    """twinky --sim's Blender on the lights, the cone if not given, that the page's worker steps: init
    once, then step a frame at a time, command between frames, and changed_state after each."""
    frame = FRAME

    def __init__(self, lights: SimLights | None=None):
        self.blender = commands.start(lights if lights is not None else SimLights())
        self.layout = layout_message(self.blender)
        self.number = 0
        self.sent = b""
        self.state: str | None = None  # the last state given
        self.blender.on_frame = self._sent

    def _sent(self, frame: bytes):
        self.sent = frame
        # the fake interfaces keep every frame, which an endless page can't
        for interface in self.blender.lights.interfaces:
            interface.frames.clear()

    def init(self, t: float | None=None):
        self.blender.init(time.time() if t is None else t)

    def step(self, t: float | None=None) -> bytes:
        """Renders and writes the frame at t, now if not given, and gives its message."""
        self.blender.write(self.blender.render(time.time() if t is None else t))
        message = frame_message(self.number, self.sent)
        self.number += 1
        return message

    def command(self, message: str):
        """Runs one of the remote's commands, the JSON it sends, between frames as twinky's queue does."""
        commands.remote_command(json.loads(message))(self.blender)

    def changed_state(self) -> str | None:
        """The state message, as the remote gets it, when it changed since the last one given."""
        state = json.dumps({"state": remote_state(self.blender)})
        if state == self.state:
            return None
        self.state = state
        return state
