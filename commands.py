"""What twinky does to its Blender: the rotation it starts with, each with its save, and the commands the
TUI and the remote queue. Apart from the device, the server and the TUI, so the simulator page's own
engine (browser.py) runs them too."""
import json
import logging
import os

from control import (
    MusicFeature,
    WiredPattern,
    BasicBitch,
    CircusTent,
    CoiledSpring,
    Confetti,
    FallingSnow,
    Galaxus,
    Groovy,
    RainbowStorm,
    SlidingDoor,
    SpiralTop,
)
from core import Blender
from effects import EFFECTS, EffectPattern
from hints import HINTS
import look

log = logging.getLogger("twinky")

SAVES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves")

def switch_pattern(idx):
    def func(a):
        a.start_transition(idx)
    return func

# The menu lists the Music feature after the pattern's own, so a feature index past them is Music's

def change_option(fidx, cidx, step):
    def func(a):
        if fidx < len(a.pattern.features):
            a.pattern.change(fidx, cidx, step)
        else:
            a.music.change(cidx, step)
        a.glide()

    return func

def set_option(fidx, cidx, oidx):
    def func(a):
        if fidx < len(a.pattern.features):
            a.pattern.set(fidx, cidx, oidx)
        else:
            a.music.set(cidx, oidx)
        a.glide()

    return func

def random_pattern(a):
    a.next_pattern = a._pick_next()
    idx = a.patterns.index(a.next_pattern)
    a.start_transition(idx)

def randomize_pattern(a):
    a.pattern.randomize()
    a.glide()

def randomize_feature(fidx):
    def func(a):
        if fidx < len(a.pattern.features):
            a.pattern.features[fidx].randomize()
            a.pattern.update()
        else:
            a.music.randomize()
        a.glide()
    return func

def pauseplay(a):
    a.pause_change = not a.pause_change

# the walk's: Pace and Reach stepped, Stay and a feature's pin flipped, Back and Nudge

def walk_pace(step):
    def func(a):
        a.walk.pace.change(step)
    return func

def walk_reach(step):
    def func(a):
        a.walk.reach.change(step)
    return func

def toggle_stay(a):
    a.walk.stay.change()

def toggle_pin(fidx):
    def func(a):
        # Music is no pattern's, so the walk never moves it
        if fidx < len(a.pattern.features):
            a.walk.pins ^= {fidx}
    return func

def walk_back(a):
    a.walk.back(a)

def nudge(a):
    # as the walk would: never while a change runs
    if not a.transitioning:
        a.walk.step(a)

def spin_ring(angle):
    def func(a):
        a.ring_angle = angle
    return func

def save_path(pattern: WiredPattern) -> str:
    return os.path.join(SAVES, f"{pattern.name.replace(' ', '_').lower()}.json")

def toggle_configured(a):
    a.pattern.configured = not a.pattern.configured
    os.makedirs(SAVES, exist_ok=True)
    with open(save_path(a.pattern), 'w', encoding='utf-8') as file:
        json.dump(a.pattern._to_dict(), file, indent=2, ensure_ascii=False)
        file.write("\n")
    log.info("Saved %s", a.pattern.name)

def music_path() -> str:
    return os.path.join(SAVES, "music.json")

def save_music(a):
    # the same shape as a pattern's save, its one feature by name
    os.makedirs(SAVES, exist_ok=True)
    with open(music_path(), 'w', encoding='utf-8') as file:
        json.dump({a.music.name: a.music._to_dict()}, file, indent=2, ensure_ascii=False)
        file.write("\n")
    log.info("Saved Music")

def load_music(music: MusicFeature):
    if not os.path.exists(music_path()):
        log.info("No configuration found for Music")
    else:
        with open(music_path(), encoding='utf-8') as file:
            music._from_dict(json.load(file).get(music.name, {}), music.name)
            log.info("Loaded saved config for Music")

def load_pattern(pattern: WiredPattern):
    fname = save_path(pattern)
    if not os.path.exists(fname):
        log.info("No configuration found for %s", pattern.name)
    else:
        with open(fname, encoding='utf-8') as file:
            pattern._from_dict(json.load(file))
            pattern.configured = True
            log.info("Loaded saved config for %s", pattern.name)
    return pattern

def start_patterns() -> list[WiredPattern]:
    """The rotation: the ten patterns, the six hints, the ten effects and a pattern for each look in
    looks/, each with its save."""
    return [load_pattern(pattern) for pattern in [
        BasicBitch(),
        CircusTent(),
        CoiledSpring(),
        Confetti(),
        FallingSnow(),
        Galaxus(),
        Groovy(),
        RainbowStorm(),
        SlidingDoor(),
        SpiralTop(),
        *(cls() for cls in HINTS),
        *(EffectPattern(cls()) for cls in EFFECTS),
        *look.load_looks(),
    ]]

def remote_command(message: dict):
    """The TUI's own command for a message from the remote page. The page's view may be a moment
    behind, so a command for a feature runs only while the page's pattern is on show and the control
    is still there."""
    command = message["command"]
    if command == "switch":
        return switch_pattern(message["to"])
    if command == "random":
        return random_pattern
    if command == "pause":
        return pauseplay
    if command == "save":
        return toggle_configured
    if command == "save music":
        return save_music
    if command == "spin":
        return spin_ring(message["angle"])
    if command == "pace":
        return walk_pace(message["step"])
    if command == "reach":
        return walk_reach(message["step"])
    if command == "stay":
        return toggle_stay
    if command == "back":
        return walk_back
    if command == "nudge":
        return nudge
    if command == "randomize" and "feature" not in message:
        return randomize_pattern
    pattern = message["pattern"]
    fidx = message["feature"]
    control = None  # change's and set's: the control's place and name
    if command == "randomize":
        func = randomize_feature(fidx)
    elif command == "pin":
        func = toggle_pin(fidx)
    elif command == "change":
        control = (message["control"], message["name"])
        func = change_option(fidx, message["control"], message["step"])
    elif command == "set":
        control = (message["control"], message["name"])
        func = set_option(fidx, message["control"], message["option"])
    else:
        raise ValueError(f"No command {command!r}")

    def shown(a):
        # the control by name too, as a switch flipped on or off moves the ones after it
        features = a.pattern.features + [a.music]
        on_show = a.pattern.name == pattern and fidx < len(features)
        if on_show and control is not None:
            cidx, name = control
            controls = [c.name for c in features[fidx].visible_controls()]
            on_show = cidx < len(controls) and controls[cidx] == name
        if on_show:
            func(a)
        else:
            log.info("Dropped the remote's %s, for %s as it was", command, pattern)
    return shown

def start(lights) -> Blender:
    """twinky's Blender as it starts on the lights: the rotation from its first pattern with the
    changes paused, that pattern shuffled, and Music's save."""
    animation = Blender(start_patterns(), lights, 0, True)
    animation.pattern.randomize()
    load_music(animation.music)
    return animation
