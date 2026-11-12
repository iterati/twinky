"""A Bermuda look on the tree: the importer that maps a look's JSON export (Bermuda's Bank, the whole
scene) to a tree pattern's values, and the pattern they make, a hint of the look and not its picture.
The look's palette stops (with its hue, contrast and time) become the pattern's palette; its star's
points the number of sectors round the trunk; its contour's rings and drift the bands and their
speed; and each modulator target moves the part its knob names, its phase spread laid round the
trunk."""
import json
import math
import os
import re

from control import BlendFeature, Control, WiredPattern
from hints import SOFTNESS, HintFeature, slot
from motion import Modulator, Running, Target
from palette import Palette, Stop, js_round, palette_at

LOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "looks")

def read(scene: dict, path: str):
    """The value at path in the scene, as "levels[0].variants[0].shape.n.value", or an error naming
    the field the look is missing."""
    value = scene
    for key in re.findall(r"[^.[\]]+", path):
        try:
            value = value[int(key)] if isinstance(value, list) else value[key]
        except (KeyError, IndexError, TypeError, ValueError):
            raise ValueError(f"The look has no {path}") from None
    return value

def part(knob: str) -> str:
    """The moving part a modulator's target drives: a turn the sectors' spin, a contour knob the bands,
    the palette's hue its hue (its depth in degrees), any other palette knob the palette's index, and
    any other knob the brightness."""
    if knob.split(".")[-1] == "turn":
        return "spin"
    if knob.startswith("contour"):
        return "bands"
    if knob == "palette.hue":
        return "hue"
    if knob.startswith("palette"):
        return "palette"
    return "brightness"

def mapped(scene: dict) -> dict:
    """A look's tree pattern, by name, from Bermuda's scene."""
    stops = read(scene, "palette.stops")
    timing = []
    for i in range(len(read(scene, "modulators"))):
        m = f"modulators[{i}]"
        wave = read(scene, f"{m}.wave")
        for j in range(len(read(scene, f"{m}.targets"))):
            target = read(scene, f"{m}.targets[{j}]")
            timing.append({
                "part": part(read(scene, f"{m}.targets[{j}].knob")),
                "wave": wave,
                "period": read(scene, f"{m}.period"),
                "phase": read(scene, f"{m}.phase"),
                "harmonics": read(scene, f"{m}.harmonics") if wave == "beat" else None,
                "steps": read(scene, f"{m}.steps") if wave == "steps" else None,
                "glide": read(scene, f"{m}.glide"),
                "depth": read(scene, f"{m}.targets[{j}].depth"),
                # whole turns round the trunk, as part of one would tear at angle 0
                "spread": js_round(target.get("phaseSpread", 0)),
            })
    return {
        "name": read(scene, "name"),
        "palette": {
            "stops": [{
                "at": read(scene, f"palette.stops[{i}].at"),
                "lch": [read(scene, f"palette.stops[{i}].lch[{c}].value") for c in range(3)],
                "mix": read(scene, f"palette.stops[{i}].mix"),
            } for i in range(len(stops))],
            "hue": read(scene, "palette.hue.value"),
            "contrast": read(scene, "palette.contrast.value"),
            "time": read(scene, "palette.time.value"),
        },
        "sectors": read(scene, "levels[0].variants[0].shape.n"),
        "bands": read(scene, "contour.rings.value"),
        "drift": read(scene, "contour.drift.value"),
        "timing": timing,
    }

def import_look(path: str) -> str:
    """Writes the tree pattern for the look exported to path into looks/, and gives its file."""
    with open(path, encoding="utf-8") as file:
        values = mapped(json.load(file))
    os.makedirs(LOOKS, exist_ok=True)
    # named as Bermuda's export names its file
    out = os.path.join(LOOKS, re.sub(r"[^\w-]+", "-", values["name"], flags=re.ASCII) + ".json")
    with open(out, "w", encoding="utf-8") as file:
        json.dump(values, file, indent=2, ensure_ascii=False)
        file.write("\n")
    return out

class LookFeature(HintFeature):
    """The look's sectors, their spin, the bands, the palette's index and hue and the brightness, each
    moved by the modulators that drive it."""
    def __init__(self, values: dict):
        palette = values["palette"]
        self.palette_time = palette["time"]
        self.sectors = values["sectors"]
        self.bands = values["bands"]
        self.drift_speed = values["drift"]  # radians a beat
        self.drift = 0.0
        self.colour = 0.0
        self.parts: dict[str, list[Running]] = {name: [] for name in ["spin", "bands", "palette", "hue", "brightness"]}
        for i, t in enumerate(values["timing"]):
            m = Modulator(str(i), t["wave"], t["period"], t["phase"], t["harmonics"], t["steps"], t["glide"])
            self.parts[t["part"]].append(Running(m, Target(t["part"], t["depth"], t["spread"])))
        self._softness = Control("Softness", SOFTNESS)
        super(LookFeature, self).__init__("Look", [self._softness], sum(self.parts.values(), []))
        self.palette = Palette([Stop(s["at"], tuple(s["lch"]), s["mix"]) for s in palette["stops"]],
                               palette["hue"], palette["contrast"])

    def frame(self, beats, dt):
        super(LookFeature, self).frame(beats, dt)
        # the contour's ring phase and the palette's running index, as motion.ts runs them
        self.drift = (self.drift + (self.drift_speed * beats)) % (2 * math.pi)
        self.colour = (self.colour + (self.palette_time * beats)) % 1

    def light(self, x, y):
        def moved(name: str) -> float:
            return sum(running.offset(x) for running in self.parts[name])

        softness = self._softness.value
        cover, k = slot(((x - moved("spin")) % 1) * self.sectors, softness)
        if self.bands:
            band, _ = slot((y * self.bands) - (self.drift / (2 * math.pi)) - moved("bands"), softness)
            cover *= band
        brightness = min(1.0, max(0.0, 1 + moved("brightness")))
        L, C, h = palette_at(self.palette, (k / self.sectors) + self.colour + moved("palette"))
        # palette_at adds the palette's hue to every hue it mixes, so a hue moved after is the same
        return cover * brightness, (L, C, h + moved("hue"))

class Look(WiredPattern):
    def __init__(self, values: dict):
        super(Look, self).__init__(values["name"])
        self.features = [LookFeature(values), BlendFeature()]

def load_looks() -> list[Look]:
    """A pattern for each look in looks/."""
    if not os.path.isdir(LOOKS):
        return []
    looks = []
    for name in sorted(n for n in os.listdir(LOOKS) if n.endswith(".json")):
        with open(os.path.join(LOOKS, name), encoding="utf-8") as file:
            looks.append(Look(json.load(file)))
    return looks
