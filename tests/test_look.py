"""The importer: a Bermuda look's JSON export, written here by hand in the export's shape, mapped to a
tree pattern, and the pattern it makes."""
import copy
import json
import random

import pytest

import look
import twinky
from hints import Wash
from support import FRAME, blender, frames, in_range

def knob(value: float, **more) -> dict:
    return {"value": value} | more

def shape(n: int) -> dict:
    return {"n": n, "m": knob(3), "r": knob(0.4), "round": knob(0.1), "twist": knob(0)}

# The parts of a scene the mapping reads, as Bank.tsx's export writes them (JSON.stringify(scene,
# null, 2)), with some it doesn't
LOOK = {
    "name": "Disco Ball",
    "levels": [
        {"id": "hexA", "weight": knob(1), "variants": [{"share": knob(1), "shape": shape(6)},
                                                        {"share": knob(0.5), "shape": shape(8)}]},
        {"id": "hexB", "weight": knob(0.5), "variants": [{"share": knob(1), "shape": shape(4)}]},
    ],
    "contour": {"rings": knob(3, spread=0.1), "drift": knob(0.2, glide=1), "radialWeight": knob(0.5)},
    "palette": {
        "stops": [
            {"at": 0, "lch": [knob(0.7), knob(0.15), knob(30)], "mix": "short"},
            {"at": 0.4, "lch": [knob(0.5), knob(0.2), knob(200)], "mix": "long"},
            {"at": 0.7, "lch": [knob(0.85), knob(0.1), knob(90)], "mix": "straight"},
        ],
        "hue": knob(20),
        "contrast": knob(1.2),
        "radius": knob(1),
        "time": knob(0.05),
    },
    "modulators": [
        {"id": "spin", "wave": "cos", "period": 8, "phase": 0.25, "glide": 0.5,
         "targets": [{"knob": "levels[hexA].affine.turn", "depth": 0.1, "phaseSpread": 1}]},
        {"id": "pulse", "wave": "beat", "period": 2, "phase": 0, "harmonics": [3, 5], "glide": 0,
         "targets": [{"knob": "levels[hexA].shape.r", "depth": 0.3},
                     {"knob": "contour.rings", "depth": 0.5, "phaseSpread": 2.2}]},
        {"id": "hue", "wave": "steps", "period": 16, "phase": 0, "steps": [0, 1, 0.5], "glide": 2,
         "targets": [{"knob": "palette.hue", "depth": 0.2, "phaseSpread": 0.3}]},
    ],
    "frame": {}, "line": {}, "composite": {}, "post": {}, "macros": [], "presets": [], "midi": {}, "loop": {},
}

def test_a_look_maps_to_its_palette_sectors_bands_drift_and_timing():
    values = look.mapped(LOOK)
    assert values["name"] == "Disco Ball"
    assert values["palette"] == {
        "stops": [
            {"at": 0, "lch": [0.7, 0.15, 30], "mix": "short"},
            {"at": 0.4, "lch": [0.5, 0.2, 200], "mix": "long"},
            {"at": 0.7, "lch": [0.85, 0.1, 90], "mix": "straight"},
        ],
        "hue": 20,
        "contrast": 1.2,
        "time": 0.05,
    }
    assert values["sectors"] == 6  # the first level's first variant's star
    assert values["bands"] == 3
    assert values["drift"] == 0.2
    assert values["timing"] == [
        {"part": "spin", "wave": "cos", "period": 8, "phase": 0.25, "harmonics": None, "steps": None,
         "glide": 0.5, "depth": 0.1, "spread": 1},
        {"part": "brightness", "wave": "beat", "period": 2, "phase": 0, "harmonics": [3, 5], "steps": None,
         "glide": 0, "depth": 0.3, "spread": 0},
        {"part": "bands", "wave": "beat", "period": 2, "phase": 0, "harmonics": [3, 5], "steps": None,
         "glide": 0, "depth": 0.5, "spread": 2},
        {"part": "palette", "wave": "steps", "period": 16, "phase": 0, "harmonics": None, "steps": [0, 1, 0.5],
         "glide": 2, "depth": 0.2, "spread": 0},
    ]

@pytest.mark.parametrize("path, field", [
    (["levels", 0, "variants", 0, "shape", "n"], "levels[0].variants[0].shape.n"),
    (["levels"], "levels[0].variants[0].shape.n"),
    (["contour", "rings"], "contour.rings.value"),
    (["contour", "drift", "value"], "contour.drift.value"),
    (["palette", "stops", 1, "lch"], "palette.stops[1].lch[0].value"),
    (["palette", "contrast"], "palette.contrast.value"),
    (["palette", "time"], "palette.time.value"),
    (["modulators", 1, "harmonics"], "modulators[1].harmonics"),
    (["modulators", 0, "targets", 0, "depth"], "modulators[0].targets[0].depth"),
    (["modulators", 2, "period"], "modulators[2].period"),
    (["name"], "name"),
])
def test_a_look_missing_a_field_raises_an_error_naming_it(path, field):
    scene = copy.deepcopy(LOOK)
    holder = scene
    for key in path[:-1]:
        holder = holder[key]
    del holder[path[-1]]
    with pytest.raises(ValueError, match=f"^The look has no {field.replace('[', r'\[').replace('.', r'\.')}$"):
        look.mapped(scene)

def test_import_look_writes_the_values_by_name_and_twinky_plays_them(tmp_path, monkeypatch):
    monkeypatch.setattr(look, "LOOKS", str(tmp_path / "looks"))
    monkeypatch.setattr(twinky, "SAVES", str(tmp_path / "saves"))
    exported = tmp_path / "Disco-Ball.json"
    exported.write_text(json.dumps(LOOK, indent=2))
    assert twinky.parse_args(["--import-look", str(exported)]).import_look == str(exported)
    out = look.import_look(str(exported))
    assert out == str(tmp_path / "looks" / "Disco-Ball.json")
    with open(out) as file:
        assert json.load(file) == look.mapped(LOOK)
    names = [p.name for p in twinky.start_patterns()]
    assert names[-1] == "Disco Ball" and len(names) == 17

def test_the_imported_pattern_renders_finite_and_moves_its_parts():
    random.seed(12)
    pattern = look.Look(look.mapped(LOOK))
    b = blender([pattern, Wash()])
    feature = pattern.features[0]
    assert feature.sectors == 6 and feature.bands == 3
    assert [len(feature.parts[name]) for name in ["spin", "bands", "palette", "brightness"]] == [1, 1, 1, 1]
    lit = 0.0
    for t, frame in frames(b, 0, 70):
        assert in_range(frame), f"{t}"
        lit = max(lit, max(map(sum, frame)))
        if t == 10 - FRAME:
            # the contour's drift, in radians a beat, and the palette's time, a beat a second with no music
            assert feature.drift == pytest.approx(0.2 * 10, abs=0.2 * FRAME * 2)
            assert feature.colour == pytest.approx(0.05 * 10, abs=0.05 * FRAME * 2)
    assert lit > 100
    assert b.pattern.name == "Wash"  # through a change
