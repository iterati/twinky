# twinky

My Twinkly animator

## Setup

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
    pnpm install
    pnpm build

## Run

    .venv/bin/python twinky.py

It finds the two strands on the LAN and logs to `twinky.log`. Saved patterns (`s`) are JSON in
`saves/`, by feature, control and option name.

`.venv/bin/python device.py` saves the tree's real layout to `layouts/tree.json`.

## The simulator page

Whenever twinky runs it serves http://localhost:8016/ (the page `pnpm build` leaves in `web/dist/`):
the lights at their positions, lit by the exact bytes the tree is sent, in 3D (drag or pinch to
orbit) or Unrolled (angle round the trunk across, height up, a quarter turn repeated past each edge).
At `/ws` the same port sends the layout as JSON, then a binary message a frame: its number (4 bytes,
little-endian) and W, R, G, B a light, strand after strand. `pnpm dev` serves the page with reloads
and passes `/ws` through to a running twinky.

    .venv/bin/python twinky.py --sim                     # the generic cone, no tree
    .venv/bin/python twinky.py --sim layouts/tree.json   # the real tree's layout, offline

## Without the tree

`sim.SimLights` is a tree with no network, on the generic cone in `layouts/cone.json`
(`.venv/bin/python layout.py` writes it) or a dumped `tree.json`. Its interfaces keep every frame's
bytes, W R G B a light. Every layout is normalized before it's used: height rescaled to 0 to 1, the
lights recentred on the trunk, strays pulled in.

## Tests

    .venv/bin/pytest tests/test_patterns.py -k Galaxus
    .venv/bin/pytest tests/test_blend.py
    .venv/bin/pytest tests/test_server.py
    .venv/bin/ruff check <files>
    pnpm exec vitest run web/src/frame.test.ts web/src/unrolled.test.ts
    pnpm typecheck
