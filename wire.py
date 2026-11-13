"""What twinky sends a page, from the server or the page's own engine (browser.py) alike: the layout
as it connects, a message a frame, and the remote's state."""
import json
import struct

from control import Control, Feature, ToggleControl

# a feature's toggle by one of these names is its On switch, on the remote's card header
SWITCHES = ["Enabled", "On"]

def layout_message(blender) -> str:
    """Every light where Pixel has it, after normalizing: x, y (its height, 0 to 1) and z, its strand
    and index on the strand, and its angle round the trunk (0 to 1)."""
    places = [(strand, index)
              for strand, interface in enumerate(blender.lights.interfaces)
              for index in range(len(interface.layout))]
    return json.dumps({"layout": [
        {"x": pixel.x, "y": pixel.y, "z": pixel.z, "strand": strand, "index": index, "angle": pixel.t}
        for pixel, (strand, index) in zip(blender.pixels, places)
    ]})

def frame_message(number: int, frame: bytes) -> bytes:
    """A frame's bytes as a page gets them: its number (4 bytes, little-endian), then W, R, G, B a light."""
    return struct.pack("<I", number) + frame

def control_state(control: Control) -> dict:
    return {"name": control.name, "options": [o.name for o in control.options], "pick": control.selected_idx}

def feature_state(feature: Feature) -> dict:
    controls = feature.visible_controls()
    switches = [i for i, c in enumerate(controls) if isinstance(c, ToggleControl) and c.name in SWITCHES]
    return {
        "name": feature.name,
        "switch": switches[0] if switches else None,  # its index in controls
        "controls": [control_state(c) for c in controls],
    }

def remote_state(blender) -> dict:
    """What the remote shows: the patterns, the current one with its mark and the change running, its
    features with their visible controls and the Music feature after them, as the TUI lists them, the
    walk's knobs, the pause and the spin ring's angle."""
    return {
        "patterns": [p.name for p in blender.patterns],
        "pattern": blender.pattern.name,
        "mark": blender.mark,
        "to": blender.change.run.pattern.name if blender.change is not None else None,
        "features": [feature_state(f) for f in blender.pattern.features + [blender.music]],
        "walk": {
            "pace": control_state(blender.walk.pace),
            "reach": control_state(blender.walk.reach),
            "stay": blender.walk.stay.value,
            "pins": sorted(blender.walk.pins),  # the pinned features' indices in features
            "back": bool(blender.walk.back_steps),  # a step for Back to undo
        },
        "paused": blender.pause_change,
        "ring": blender.ring_angle,
    }
