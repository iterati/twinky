import os

import layout

class FakeInterface:
    """Takes Blender's calls in place of a device.Interface, and keeps every frame's bytes."""
    def __init__(self, strand_layout: list[dict]):
        self.layout = strand_layout
        self.host = "sim"
        self.mode = None
        self.frames: list[bytes] = []

    def set_mode(self, mode: str):
        self.mode = mode

    def set_rt_frame_socket(self, frame, version, leds_number=None):
        self.frames.append(frame.read())

class SimLights:
    """A tree with no network, on the generic cone or a layout dumped from the real tree
    (python device.py writes layouts/tree.json)."""
    def __init__(self, path: str=os.path.join(layout.LAYOUTS, "cone.json")):
        self.interfaces = [FakeInterface(strand) for strand in layout.load(path)]
