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

## Music

The page's Listen panel hears the Mac's mic or a line-in (pick it by device; the browser's echo
cancellation, noise suppression and auto gain are off, as they wreck music) and shows the three
bands, the bpm with a Tap button to tap the tempo in, and a beat light. `web/src/music.ts` does the
analysis, about 60 times a second: onsets, the tempo (70 to 180 bpm), the beat and its bar, the low
(40-150 Hz), mid (150 Hz-2 kHz) and high (2-12 kHz) bands, the tone (dark to light) and the drive
(groove to drive). About 30 times a second the page sends twinky a text message on `/ws`:

    {"music": {"time": 1794443000.123, "bpm": 128.0, "beat": 351.27, "bar": 87, "confidence": 0.82,
               "low": 0.71, "mid": 0.4, "high": 0.22, "tone": 0.61, "drive": 0.45}}

`time` is the Mac's clock, which the page and twinky share, and `beat` the beats counted at that
time, its fraction the phase. twinky's beat clock (`music.py`) runs on from each message at its bpm.

In the TUI, Music is listed after the current pattern's features, for every pattern alike: On;
Streamers (the pattern's own streamers launched on the beat, every 2 beats or every bar, each launch
a quarter turn round the trunk on from the last); Flash (on each beat, the whole tree or a quarter
of it chasing round the trunk); Sparkle rate (the highs quicken the sparkles and add more, the bass
ones low on the tree and the treble ones at the top); Palette (the base hue glides toward orange for
light music and blue for dark); Feel (with drive, snappy sparkles and glides and changes from bar
line to bar line; with groove, long glides); Spin lock (the tree turns once every 4 or 8 bars); and
Latency (the lights later, +, or earlier, -, by up to 150 ms, to line them up with the sound). A
second after the last message the links let go, the hue and the spin gliding home. `s` on Music
saves its picks to `saves/music.json`.

## The remote

A page for the phone, at `/remote` on the same port: the patterns as a row of chips along the top, the
pattern's features as cards, Music last, the open card's controls as minus and plus steppers (tap a
value for its whole option list) and its On switch on the header, then the spin ring; along the
bottom, Random (the TUI's `R`), Shuffle (`r`: the open card's feature, or with every card closed the
whole pattern), Pause (space) and Save (`s`: the pattern, or Music with its card open). It keeps the
screen on, ticks on each minus and plus, and drags the tree round live with the spin ring, the tree
staying where it's let go (its bottom is the side nearest you). Every tap is one of the TUI's own
commands on the same queue, so the phone and the TUI can drive at once and stay in step.

On `/ws?remote` twinky sends the state as JSON as the remote connects and whenever anything changes,
from the phone, the TUI or an automatic change, and the TUI's time text 4 times a second:

    {"state": {"patterns": ["Basic Bitch", ...], "pattern": "Galaxus", "mark": "!", "to": null,
               "features": [{"name": "Spin", "on": true,
                             "controls": [{"name": "Enabled", "options": ["On", "Off"], "pick": 0}, ...]},
                            ..., {"name": "Music", ...}],
               "paused": false, "ring": 0.0}}
    {"time": "-42.13"}

`mark` is the TUI's `?` (not saved), `!` (saved) or `*` (changed since), `to` the pattern a change is
running to, `ring` the spin ring's turn. The remote sends
`{"command": "switch", "to": 3}`, `"random"`, `"pause"`, `"save"`, `"save music"`,
`{"command": "spin", "angle": 0.25}`, `"randomize"` (the pattern), and for a feature, by its place
in `features` and a control's in its visible `controls`, `"randomize"`, `"change"` (with `step`) and
`"set"` (with `option`), each naming the pattern it was meant for, as one it no longer shows is
dropped.

### On the Android phone

Twinky listens beyond this Mac only with `--remote`, and then the TUI's footer shows the remote's
address:

    .venv/bin/python twinky.py --remote

Chrome installs a page as an app, and keeps the screen on, only from a secure origin (HTTPS or
localhost), and `http://192.168.x.x` is not one, so tell Chrome on the phone to treat twinky's
address as secure:

1. Open `chrome://flags`, find "Insecure origins treated as secure"
   (`#unsafely-treat-insecure-origin-as-secure`), enter `http://<the Mac's address>:8016`, enable it
   and relaunch Chrome.
2. Open `http://<the Mac's address>:8016/remote` and install it from Chrome's menu (Add to home
   screen, then Install).

The flag names the address, so keep the Mac's the same: reserve it for the Mac on the router. The
first time twinky runs with `--remote`, the Mac's firewall asks once to let Python take incoming
connections: allow it.

## Without the tree

`sim.SimLights` is a tree with no network, on the generic cone in `layouts/cone.json`
(`.venv/bin/python layout.py` writes it) or a dumped `tree.json`. Its interfaces keep every frame's
bytes, W R G B a light. Every layout is normalized before it's used: height rescaled to 0 to 1, the
lights recentred on the trunk, strays pulled in.

## Tests

    .venv/bin/pytest tests/test_patterns.py -k Galaxus
    .venv/bin/pytest tests/test_blend.py
    .venv/bin/pytest tests/test_server.py
    .venv/bin/pytest tests/test_music.py
    .venv/bin/pytest tests/test_remote.py
    .venv/bin/ruff check <files>
    pnpm exec vitest run web/src/frame.test.ts web/src/unrolled.test.ts web/src/music.test.ts web/src/remote/remote.test.ts
    pnpm typecheck
