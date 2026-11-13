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

## The walk

The autopilot is a walk (`walk.py`): every so often one control of one of the pattern's features
steps to an option near its own and the tree glides there, so the look changes a little at a time;
about one step in ten rerolls a whole feature, and about one in thirty changes the pattern, with the
usual change, the new one freshly randomized. Space pauses it, as it paused the changes; twinky
starts paused. Its live controls:

- Pace (`<` and `>`, or `,` and `.`): slow, easy, brisk or fast, a step every 8, 4, 2 or 1 seconds;
  with Music on and its beat sure, on every 8th, 4th, 2nd or every bar line instead.
- Reach (`[` and `]`): near (the next option either way), far (up to 3 away), any (any option) or
  jump, the old autopilot: a freshly randomized pattern every 60 seconds, from a bar line in drive.
- Stay (`t`): the walk stays on this pattern, moving only its knobs (at jump, rerolling them all).
- Pin (`p`, the selected feature): the walk holds a pinned feature still and moves the rest. Pins
  are the walk's alone: not saved, left as they are by Shuffle, and cleared when the pattern changes,
  Random's change too. Music is not walked, and has none.
- Back (`b`): undoes the walk's last step, gliding back, and again the one before, 10 kept; a change
  of pattern it undoes changes back to that pattern with its controls as they were, and a step's
  pattern gets its mark back, saved or not. It works paused.
- Nudge (`n`): one step now, as the walk would take it, so none while a change runs.

A saved pattern's controls are held, as before: the walk only moves on from it, unless Stay is on.
The TUI's footer shows the keys, Pace, Reach and Stay, and a pinned feature says so.

## The simulator page

Whenever twinky runs it serves http://localhost:8016/ (the page `pnpm build` leaves in `web/dist/`):
the lights at their positions, lit by the exact bytes the tree is sent, in 3D (drag or pinch to
orbit) or Unrolled (angle round the trunk across, height up, a quarter turn repeated past each edge).
At `/ws` the same port sends the layout as JSON, then a binary message a frame: its number (4 bytes,
little-endian) and W, R, G, B a light, strand after strand. `pnpm dev` serves the page with reloads
and passes `/ws` through to a running twinky.

    .venv/bin/python twinky.py --sim                     # the generic cone, no tree
    .venv/bin/python twinky.py --sim layouts/tree.json   # the real tree's layout, offline

### The simulated tree

When no twinky.py answers the page's `/ws` as it loads, or twinky drops and is not back within 3
seconds, the page runs twinky's own engine itself, under Pyodide in a Web Worker, on the generic cone,
and says "Simulated tree: no twinky.py answered. Run twinky.py to play your tree live." It is twinky
--sim in the page: the same rotation from Basic Bitch with the changes paused and the saves in
`saves/`, stepped on the clock and at the frame rate `--sim` plays on, each frame sent to the page as
the server sends it and drawn by the same code. A panel on the right picks the pattern, has the
remote's Walk card (its On switch starts the paused walk) and sets the one on show's knobs, a pin on
each feature, each change one of the remote's commands (`switch`, `set`, the walk's). Music is off: the
Listen panel says it needs twinky.py. While simulating, the page looks for twinky every 5 seconds
(not on an HTTPS page, which twinky never serves) and goes live once it answers. Served from a
folder (`base: './'`), `dist/` works from any path, such as the site's `/twinky/`.

`browser.py` is the engine's face to the page. The build packs, as the files are when it runs, every
`.py` in the repo but `device.py`, `server.py` and `twinky.py` (the device, the server's sockets and
threads, and the TUI), with `layouts/`, `looks/` and `saves/`, and from `.venv` pytweening and
xled_plus's `ledcolor.py`, which are pure Python (`vite.config.ts`); so the build needs the venv.
In the page run `browser.py`, `commands.py`, `core.py`, `control.py`, `colors.py`, `effects.py`,
`hints.py`, `layout.py`, `look.py`, `motion.py`, `music.py`, `palette.py`, `param.py`, `sim.py`,
`streamer.py`, `topologies.py`, `utils.py`, `walk.py` and `wire.py`.
What both twinky and the page run moved out of those three: the rotation and the commands to
`commands.py`, the layout, frame and state messages to `wire.py`. Pyodide's own files are copied from
`node_modules/pyodide` into `dist/pyodide/`, never fetched from a CDN. The first load is about 13 MB
(under 6 MB gzipped), most of it Pyodide's WebAssembly; the tree's first frame came about 5 seconds
after the page opened, in headless Chromium on a local server, and then 16 frames a second, as
`--sim` gives.

## Music

The page's Listen panel hears the Mac's mic or a line-in (pick it by device; the browser's echo
cancellation, noise suppression and auto gain are off, as they wreck music), or what a browser tab
plays, such as a music video: "Listen to a tab", beside Listen and in the Input picker, asks the
browser to share a screen; pick the tab and tick Share tab audio. Chrome only offers a tab's audio
with its video, which the page stops at once, keeping the audio, and never plays it back out, as the
tab already does. A share with no audio says so, and when the tab closes or its sharing stops the
panel says so and stops listening. The panel shows the three bands, the bpm with a Tap button to
tap the tempo in, and a beat light. `web/src/music.ts` does the analysis, about 60 times a second:
onsets, the tempo (70 to 180 bpm), the beat and its bar, the low (40-150 Hz), mid (150 Hz-2 kHz)
and high (2-12 kHz) bands, the tone (dark to light) and the drive (groove to drive). About 30 times a second the page sends twinky a text message on `/ws`:

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
value for its whole option list) and its pin and On switch on the header, then the Walk card (its On
switch, the other way round from Pause; Pace and Reach as steppers, Stay, Back and Nudge), then the
spin ring; along the bottom, Random (the TUI's `R`), Shuffle (`r`: the open card's feature, or with
every card closed the whole pattern), Pause (space) and Save (`s`: the pattern, or Music with its
card open). It keeps the screen on, ticks on each minus and plus, and drags the tree round live with
the spin ring, the tree staying where it's let go (its bottom is the side nearest you). Every tap is
one of the TUI's own commands on the same queue, so the phone and the TUI can drive at once and stay
in step.

On `/ws?remote` twinky sends the state as JSON as the remote connects and whenever anything changes,
from the phone, the TUI or an automatic change, and the TUI's time text 4 times a second:

    {"state": {"patterns": ["Basic Bitch", ...], "pattern": "Galaxus", "mark": "!", "to": null,
               "features": [{"name": "Spin", "switch": 0,
                             "controls": [{"name": "Enabled", "options": ["On", "Off"], "pick": 0}, ...]},
                            ..., {"name": "Music", ...}],
               "walk": {"pace": {"name": "Pace", "options": ["slow", "easy", "brisk", "fast"], "pick": 1},
                        "reach": {"name": "Reach", "options": ["near", "far", "any", "jump"], "pick": 0},
                        "stay": false, "pins": [2], "back": true},
               "paused": false, "ring": 0.0}}
    {"time": "-42.13"}

`mark` is the TUI's `?` (not saved), `!` (saved) or `*` (changed since), `to` the pattern a change is
running to, a feature's `switch` its On toggle's place in `controls` (null with none), `walk` the
walk's Pace and Reach, Stay, the pinned features by their place in `features` and whether Back has a
step, `ring` the spin ring's turn. The remote sends
`{"command": "switch", "to": 3}`, `"random"`, `"pause"`, `"save"`, `"save music"`,
`{"command": "spin", "angle": 0.25}`, `"randomize"` (the pattern), the walk's
`{"command": "pace", "step": 1}`, `{"command": "reach", "step": -1}`, `"stay"`, `"back"` and
`"nudge"`, and for a feature, by its place in `features` and a control's in its visible `controls`,
`"randomize"`, `"pin"`, `"change"` (with `step`) and `"set"` (with `option`), each naming the
pattern it was meant for, and change and set the control's `name`, as a command for a pattern or
control no longer on show is dropped.

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

## Hints, and looks from Bermuda

Six patterns in the rotation are hints of Bermuda's looks rather than its pictures, which 800
lights can't show: slow, soft-edged shapes in Bermuda's palettes, moved by its modulators, most of
them round the trunk. Wash (the palette running up the tree, a wave of brightness round it),
Sectors (soft sectors spinning or swaying round the trunk), Bands (rings climbing, falling, or rising
and falling at the contour's drift), Spiral (soft arms winding up and turning), Hidden Field (sparse
sparkles tracing a lattice of stars seen from above the treetop) and Palette Drift (the palette
drifting round the trunk). Each picks one of Bermuda's six cosine palettes, and their periods count
beats of the beat clock while music plays, seconds otherwise. `palette.py` and `motion.py` are
Python ports of Bermuda's `src/colour.ts` and `src/motion.ts`, its names in snake_case, to read side
by side with them; the hints are in `hints.py`.

Bermuda's Bank exports a look as JSON (export). To play it on the tree:

    .venv/bin/python twinky.py --import-look Disco-Ball.json

writes `looks/Disco-Ball.json`, the look's palette, its star's points as sectors round the trunk,
its contour's rings and drift as bands, and its modulators' timing (`look.py`), and twinky plays a
pattern of that name from its next start, one for each file in `looks/`. A look missing a field
this reads is refused, naming the field.

## Effects

Ten patterns in the rotation are effects in the tree's 3D space, each light lit from its x, y and z
rather than its angle and height: Aurora (curtains of green and violet folding up the tree), Fireflies
(soft warm lights wandering in clusters), Fireworks (a spark climbs and bursts on the surface, its
sparks falling in fading trails), Ripples (rings spreading from drops), Lava lamp (blobs rising,
merging and splitting), Comets (two or three orbiting with tails), Hearth (fire at the bottom cooling
up the tree, with embers), Lightning (one branching bolt, then an afterglow), Drips (paint running
down into a pool) and Heartbeat (a double pulse from the core). Each has one feature of its own knobs
and Blend: Grain raw hardens an effect's soft edges, a light in or out. Only the rainbow palettes
turn with the base hue every 66 s; the named ones stay as named.

With Music on and the page listening, the beat and the bands drive them: a rocket, drop or drip
waits for a beat, Fireworks' Rate and Lightning's Interval the least time between, Lightning on a
bar line; a firefly lights on each beat; the beat swells Aurora and the blobs, pushes the comets and
flares the fire; Heartbeat pulses on the beat. A band moves a knob from half as set (quiet) to half
as much again (loud): the low band Aurora's and the Lava lamp's Speed, Fireworks' Size, Hearth's
Height, Heartbeat's Reach and Lightning's clouds; the high band Aurora's violet, the fireflies' Count
and Hearth's Embers; the bands together Ripples' Width, the comets' Tail and Drips' Speed.

They are in `effects.py`. Once a frame, before the lights, the Blender calls a pattern's `step` with
the run's clock, every light, the sound, the beat and the base hue, and an effect works out each
light's layers there; every base color is then called with the light's `Pixel` too, which only an
effect reads. An effect starts again whenever its run does.

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
    .venv/bin/pytest tests/test_walk.py
    .venv/bin/pytest tests/test_palette.py tests/test_motion.py tests/test_hints.py tests/test_look.py
    .venv/bin/pytest tests/test_effects.py -k Aurora
    .venv/bin/pytest tests/test_browser.py
    .venv/bin/ruff check <files>
    pnpm exec vitest run web/src/frame.test.ts web/src/unrolled.test.ts web/src/music.test.ts web/src/remote/remote.test.ts
    pnpm exec vitest run web/src/engine.test.ts   # the page's engine against twinky --sim, in Node
    pnpm exec vitest run web/src/App.test.ts      # the built page with no twinky, in headless Chromium
    pnpm exec vitest run web/src/Listen.test.ts   # the Listen panel's tab, shared by a stub, in headless Chromium
    pnpm typecheck
