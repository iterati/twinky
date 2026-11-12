"""Saved patterns: JSON by feature, control and option name, and old saves by position."""
import json
import logging
import os
import random

import pytest

import commands
from support import PATTERNS

# Basic Bitch as the old pickle held it, option numbers by position
OLD_BASIC_BITCH = [[0, 8, 5, 6], [0, 1, 4, 0, 2, 4], [0, 5, 9, 0, 1, 5], [0, 5, 0, 3, 1], [0, 0, 6, 0, 2, 2, 2]]

@pytest.mark.parametrize("cls", PATTERNS, ids=lambda cls: cls.__name__)
def test_names_are_unique_so_a_save_can_use_them(cls):
    pattern = cls()
    assert len({f.name for f in pattern.features}) == len(pattern.features)
    for f in pattern.features:
        assert len({c.name for c in f.controls}) == len(f.controls), f.name
        for c in f.controls:
            assert len({o.name for o in c.options}) == len(c.options), f"{f.name} {c.name}"

@pytest.mark.parametrize("cls", PATTERNS, ids=lambda cls: cls.__name__)
def test_a_save_round_trips_by_name(cls, tmp_path, monkeypatch):
    random.seed(1)
    monkeypatch.setattr(commands, "SAVES", str(tmp_path))
    pattern = cls()
    pattern.randomize()
    commands.toggle_configured(type("Animation", (), {"pattern": pattern})())
    with open(tmp_path / os.path.basename(commands.save_path(pattern))) as file:
        saved = json.load(file)
    assert saved == pattern._to_dict()
    loaded = commands.load_pattern(cls())
    assert loaded.configured
    assert loaded._to_dict() == saved

def test_an_old_save_loads_by_position():
    pattern = PATTERNS[0]()
    pattern._from_dict(OLD_BASIC_BITCH)
    assert [[c.selected_idx for c in f.controls] for f in pattern.features[:5]] == OLD_BASIC_BITCH
    assert pattern._to_dict()["Blend"] == {"Transition": "crossfade", "Grain": "smooth"}

def test_the_saves_in_the_repo_load_by_name(caplog):
    files = sorted(os.listdir(commands.SAVES))
    assert files == ["basic_bitch.json", "circus_tent.json"]
    with caplog.at_level(logging.WARNING):
        patterns = [commands.load_pattern(cls()) for cls in PATTERNS]
    assert caplog.text == ""
    basic = next(p for p in patterns if p.name == "Basic Bitch")
    assert [[c.selected_idx for c in f.controls] for f in basic.features[:5]] == OLD_BASIC_BITCH
    assert sum(p.configured for p in patterns) == 2

def test_a_name_the_pattern_no_longer_has_keeps_its_option(caplog):
    pattern = PATTERNS[0]()
    saved = pattern._to_dict()
    saved["Flicker"]["Start"] = "7/9"
    saved["Gone"] = {"Away": "1"}
    with caplog.at_level(logging.WARNING):
        pattern._from_dict(saved)
    assert "no option '7/9' for Flicker Start" in caplog.text
    assert pattern._to_dict()["Flicker"]["Start"] == "0"
