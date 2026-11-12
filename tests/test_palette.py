"""The palette port against Bermuda: reference values made once from its colour.ts with Node
(tests/palette_reference.json)."""
import json
import os

import pytest

from palette import COSINES, Palette, Stop, oklch_to_linear, oklch_to_srgb, palette_at, srgb_to_oklch, \
    stops_from_cosine, to_gamma

with open(os.path.join(os.path.dirname(__file__), "palette_reference.json")) as file:
    REFERENCE = json.load(file)

def stop(s: dict) -> Stop:
    return Stop(s["at"], tuple(knob["value"] for knob in s["lch"]), s["mix"])

def close(a, b):
    assert len(a) == len(b)
    for x, y in zip(a, b):
        assert x == pytest.approx(y, abs=1e-6)

@pytest.mark.parametrize("name", list(COSINES))
def test_stops_from_cosine_match_bermuda(name):
    ours = stops_from_cosine(name, REFERENCE["count"])
    theirs = [stop(s) for s in REFERENCE["stopsFromCosine"][name]]
    assert [s.mix for s in ours] == ["short"] * len(theirs)
    for a, b in zip(ours, theirs):
        close((a.at, *a.lch), (b.at, *b.lch))

def test_srgb_to_oklch_matches_bermuda():
    for case in REFERENCE["srgbToOklch"]:
        close(srgb_to_oklch(tuple(case["rgb"])), case["lch"])

def test_oklch_to_srgb_matches_bermuda_and_the_tree_takes_it_before_the_gamma():
    for case in REFERENCE["oklchToSrgb"]:
        close(oklch_to_srgb(tuple(case["lch"])), case["rgb"])
        close([to_gamma(c) for c in oklch_to_linear(tuple(case["lch"]))], case["rgb"])

@pytest.mark.parametrize("mix", ["straight", "short", "long"])
def test_palette_at_matches_bermuda(mix):
    case = REFERENCE["paletteAt"][mix]
    palette = Palette([stop(s) for s in case["palette"]["stops"]],
                      case["palette"]["hue"]["value"], case["palette"]["contrast"]["value"])
    assert len(case["points"]) == 16
    for t, value in zip(case["points"], case["values"]):
        close(palette_at(palette, t), value)
