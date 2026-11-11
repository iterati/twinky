# twinky
My Twinkly animator

## Setup

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt -r requirements-dev.txt

## Run

    .venv/bin/python twinky.py

It finds the two strands on the LAN and logs to `twinky.log`. Saved patterns (`s`) are JSON in
`saves/`, by feature, control and option name.

`.venv/bin/python device.py` saves the tree's real layout to `layouts/tree.json`.

## Without the tree

`sim.SimLights` is a tree with no network, on the generic cone in `layouts/cone.json`
(`.venv/bin/python layout.py` writes it) or a dumped `tree.json`. Its interfaces keep every frame's
bytes, W R G B a light. Every layout is normalized before it's used: height rescaled to 0 to 1, the
lights recentred on the trunk, strays pulled in.

## Tests

    .venv/bin/pytest tests/test_patterns.py -k Galaxus
    .venv/bin/pytest tests/test_blend.py
    .venv/bin/ruff check <files>
