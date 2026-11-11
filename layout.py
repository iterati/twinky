import json
import logging
import math
import os
import random
from statistics import median

log = logging.getLogger(__name__)

LAYOUTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "layouts")

# A layout is a list of strands, each a list of lights as the device gives them: {x, y, z}, y up

def load(path: str) -> list[list[dict]]:
    with open(path) as file:
        return json.load(file)

def save(path: str, strands: list[list[dict]]):
    with open(path, "w") as file:
        json.dump(strands, file)

def cone(strands: int=2,
         per_strand: int=400,
         turns: float=14,
         base: float=0.38,
         depth: tuple[float, float]=(0.55, 1.0),
         seed: int=1) -> list[list[dict]]:
    """A generic tree: each strand a helix from the bottom to the top, offset round the trunk from
    the others, each light depth[0] to depth[1] of the way out to the surface. base is the base
    radius over the height."""
    rnd = random.Random(seed)
    layout = []
    for strand in range(strands):
        lights = []
        for i in range(per_strand):
            y = (i + 0.5 + rnd.uniform(-0.3, 0.3)) / per_strand
            a = 2 * math.pi * ((turns * y) + (strand / strands)) + rnd.uniform(-0.08, 0.08)
            r = base * (1 - y) * rnd.uniform(*depth)
            lights.append({"x": r * math.cos(a), "y": y, "z": r * math.sin(a)})
        layout.append(lights)
    return layout

def _line(points: list[tuple[float, float]]):
    """The least-squares straight line through (y, v) points, as a function of y."""
    my = sum(y for y, _ in points) / len(points)
    mv = sum(v for _, v in points) / len(points)
    spread = sum((y - my) ** 2 for y, _ in points)
    slope = sum((y - my) * (v - mv) for y, v in points) / spread if spread else 0.0
    return lambda y: mv + (slope * (y - my))

def normalize(lights: list[dict], slices: int=10, stray: float=1.5) -> list[dict]:
    """Puts a layout the Twinkly app estimated where Pixel expects it, so angles round the trunk are
    true. A good layout comes through all but unchanged."""
    # the height rescaled so its 1st to 99th percentile runs from 0 to 1
    ys = sorted(light["y"] for light in lights)
    lo, hi = ys[int(len(ys) * 0.01)], ys[int(len(ys) * 0.99)]
    heights = [min(1.0, max(0.0, (light["y"] - lo) / (hi - lo))) for light in lights]

    # the trunk: a straight line through the median x and z of each height slice, which catches a lean
    groups: dict[int, list[int]] = {}
    for i, y in enumerate(heights):
        groups.setdefault(min(slices - 1, int(y * slices)), []).append(i)
    groups = {k: g for k, g in groups.items() if len(g) >= 3}

    def slice_medians(values):
        return [(median(heights[i] for i in g), median(values[i] for i in g)) for g in groups.values()]

    trunk_x = _line(slice_medians([light["x"] for light in lights]))
    trunk_z = _line(slice_medians([light["z"] for light in lights]))
    out = [
        {"x": light["x"] - trunk_x(y), "y": y, "z": light["z"] - trunk_z(y)}
        for light, y in zip(lights, heights)
    ]

    # a light past `stray` times the median radius at its height goes back in to the surface: the
    # median radius a line through the slices' (a tree tapers), kept above a tenth of the widest
    radii = [math.hypot(light["x"], light["z"]) for light in out]
    medians = slice_medians(radii)
    taper = _line(medians)
    floor = 0.1 * max(m for _, m in medians)
    expected = [max(floor, taper(y)) for y in heights]
    strays = [i for i, r in enumerate(radii) if r > stray * expected[i]]
    if strays:
        surface = max(r / e for r, e in zip(radii, expected) if r <= stray * e)
        for i in strays:
            pull = surface * expected[i] / radii[i]
            out[i]["x"] *= pull
            out[i]["z"] *= pull
        log.info("Pulled %d stray lights back to the surface: %s", len(strays), strays)
    return out

if __name__ == "__main__":
    # writes the generic cone the simulator plays when there's no tree.json
    save(os.path.join(LAYOUTS, "cone.json"), cone())
