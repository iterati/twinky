import argparse
import curses
import json
import logging
import os
from queue import Queue, Empty
import socket
import threading
from threading import Thread
import time
from core import Blender, FRAME, wait_for
from device import Lights
import layout
from server import PORT, Server
from sim import SimLights
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

log = logging.getLogger("twinky")

_sentinel = object()

SAVES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves")

def animation_thread_task(animation, command_queue):
    start_time = time.time()
    animation.init(start_time)
    next_frame = start_time + FRAME
    while True:
        try:
            command = command_queue.get(False)
            if command is not None:
                if command is _sentinel:
                    log.info("Stopping animation")
                    command_queue.put(_sentinel)
                    break
                else:
                    command(animation)
                command_queue.task_done()
        except Empty:
            pass

        colors = animation.render(time.time())
        animation.write(colors)
        next_frame = wait_for(next_frame)

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
    if command == "randomize" and "feature" not in message:
        return randomize_pattern
    fidx = message["feature"]
    cidx = message.get("control", 0)
    if command == "randomize":
        func = randomize_feature(fidx)
    elif command == "change":
        func = change_option(fidx, cidx, message["step"])
    elif command == "set":
        func = set_option(fidx, cidx, message["option"])
    else:
        raise ValueError(f"No command {command!r}")

    def shown(a):
        features = a.pattern.features + [a.music]
        if a.pattern.name == message["pattern"] and fidx < len(features) and cidx < len(features[fidx].visible_controls()):
            func(a)
        else:
            log.info("Dropped the remote's %s, for %s as it was", command, message["pattern"])
    return shown

def parse_args(argv: list[str] | None=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Animates the Twinkly tree, and plays it at http://localhost:8016/")
    parser.add_argument(
        "--sim",
        nargs="?",
        const=os.path.join(layout.LAYOUTS, "cone.json"),
        metavar="LAYOUT",
        help="play a simulated tree instead of finding the real one: the cone, or a layout file such as layouts/tree.json",
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="listen on the home network too, for the remote page at http://<this Mac>:8016/remote",
    )
    return parser.parse_args(argv)

def open_lights(args: argparse.Namespace):
    return SimLights(args.sim) if args.sim else Lights()

def listen_host(args: argparse.Namespace) -> str:
    # every interface with --remote, else only this Mac
    return "0.0.0.0" if args.remote else "localhost"

def lan_address() -> str:
    """This Mac's address on the home network, the one its route out leaves from (a UDP socket's
    connect sends nothing)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("192.0.2.1", 9))
        return s.getsockname()[0]

class Menu:
    def __init__(self, animation, queue, remote: str | None=None):
        self.animation = animation
        self.queue = queue
        self.remote = remote  # the remote page's address, with --remote
        self.selected_column = 0
        self.selected_row = [0, 0, 0]
        self.curr_pattern = animation.pattern

    @property
    def features(self):
        return self.animation.pattern.features + [self.animation.music]

    def print_menu(self, screen):
        screen.clear()
        h, w = screen.getmaxyx()
        colw = (w - 2) // 3

        feature = self.features[self.selected_row[1]]

        line = '\u2554'
        line += '\u2550' * (w - 2)
        line += '\u2557'
        screen.addstr(0, 0, line)
        
        # top shows animation name and time if not paused
        screen.addstr(1, 0, '\u2551')
        screen.addstr(
            1,
            (w // 2) - (len(self.animation.pattern_name) // 2),
            self.animation.pattern_name,
        )
        screen.addstr(
            1,
            w - (len(self.animation.time_str) + 2),
            self.animation.time_str,
        )
        screen.addstr(1, w-1, '\u2551')

        line = '\u2560'
        line += '\u2550' * (colw - len(line))
        line += '\u2564'
        line += '\u2550' * ((2*colw) - len(line))
        line += '\u2564'
        line += '\u2550' * ((w - 1) - len(line))
        line += '\u2563'
        screen.addstr(2, 0, line)

        for i in range(3, h-4):
            screen.addstr(i, 0, '\u2551')
            screen.addstr(i, colw, '\u2502')
            screen.addstr(i, colw*2, '\u2502')
            screen.addstr(i, w-1, '\u2551')

        line = '\u2560'
        line += '\u2550' * (colw - len(line))
        line += '\u2567'
        line += '\u2550' * ((2*colw) - len(line))
        line += '\u2567'
        line += '\u2550' * ((w - 1) - len(line))
        line += '\u2563'
        screen.addstr(h-4, 0, line)

        screen.addstr(h-3, 0, '\u2551')
        screen.addstr(h-3, 2, "q - quit, R - random mode, r - randomize mode/feature, spc - pause mode change")
        screen.addstr(h-3, w-1, '\u2551')

        line = '\u255a'
        line += '\u2550' * (colw - len(line))
        line += '\u2550'
        line += '\u2550' * ((2*colw) - len(line))
        line += '\u2550'
        line += '\u2550' * ((w - 1) - len(line))
        line += '\u255d'
        screen.addstr(h-2, 0, line)
        if self.remote is not None:
            screen.addstr(h-2, 2, f" remote: {self.remote} ")

        # left shows patterns
        for i, p in enumerate(self.animation.patterns):
            pair = curses.color_pair(0)
            if self.selected_row[0] == i:
                pair = curses.color_pair(1)
                if self.selected_column == 0:
                    pair |= curses.A_BOLD
            screen.addstr(3 + i, 2, p.name, pair)

        # middle shows main settings
        for i, f in enumerate(self.features):
            pair = curses.color_pair(0)
            if self.selected_row[1] == i:
                pair = curses.color_pair(1)
                if self.selected_column == 1:
                    pair |= curses.A_BOLD
            screen.addstr(3 + i, colw + 2, f.name, pair)

        # right shows control settings
        for i, c in enumerate(feature.visible_controls()):
            pair = curses.color_pair(0)
            if self.selected_row[2] == i:
                pair = curses.color_pair(1)
                if self.selected_column == 2:
                    pair |= curses.A_BOLD
            screen.addstr(3 + i, (2*colw) + 2, f"{c.name}: {c.selected.name}", pair)

        screen.refresh()

    @property
    def maxrow(self):
        self.selected_row[1] %= len(self.features)
        return [
            len(self.animation.patterns),
            len(self.features),
            len(self.features[self.selected_row[1]].visible_controls()),
        ]

    def handle_input(self, screen) -> bool:
        key = screen.getch()
        if key == ord('q'):
            self.queue.put(_sentinel)
            return True
        elif key == ord('s'):
            if self.selected_column > 0 and self.features[self.selected_row[1]] is self.animation.music:
                self.queue.put(save_music)
            else:
                self.queue.put(toggle_configured)
        elif key == ord('R'):
            self.queue.put(random_pattern)
        elif key == ord('r'):
            if self.selected_column == 0:
                self.queue.put(randomize_pattern)
            else:
                self.queue.put(randomize_feature(self.selected_row[1]))
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if self.selected_column == 0:
                self.queue.put(switch_pattern(self.selected_row[0]))
        elif key == ord(' '):
            self.queue.put(pauseplay)
        elif key == curses.KEY_LEFT:
            self.selected_column = (self.selected_column - 1) % 3
            self.selected_row[self.selected_column] %= self.maxrow[self.selected_column]
        elif key == curses.KEY_RIGHT:
            self.selected_column = (self.selected_column + 1) % 3
            self.selected_row[self.selected_column] %= self.maxrow[self.selected_column]
        elif key == curses.KEY_UP:
            self.selected_row[self.selected_column] -= 1
            self.selected_row[self.selected_column] %= self.maxrow[self.selected_column]
        elif key == curses.KEY_DOWN:
            self.selected_row[self.selected_column] += 1
            self.selected_row[self.selected_column] %= self.maxrow[self.selected_column]
        elif key in [ord('-'), ord('_')] :
            if self.selected_column == 1:
                controls = self.features[self.selected_row[1]].controls
                idxs = [i for i, c in enumerate(controls)]
                if len(idxs) > 0:
                    self.queue.put(set_option(self.selected_row[1], idxs[0], 1))
                    self.selected_row[2] = 0
            elif self.selected_column == 2:
                self.queue.put(change_option(self.selected_row[1], self.selected_row[2], -1))
        elif key in [ord('='), ord('+')] :
            if self.selected_column == 1:
                controls = self.features[self.selected_row[1]].controls
                idxs = [i for i, c in enumerate(controls)]
                if len(idxs) > 0:
                    self.queue.put(set_option(self.selected_row[1], idxs[0], 0))
                    self.selected_row[2] = 0
                self.queue.put(set_option(self.selected_row[1], 0, 0))
                self.selected_row[2] = 0
            elif self.selected_column == 2:
                self.queue.put(change_option(self.selected_row[1], self.selected_row[2], 1))
        return False

    def __call__(self, screen):
        curses.curs_set(0)
        curses.cbreak()
        screen.nodelay(True)
        screen.keypad(True)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)

        start_time = time.time()
        next_frame = start_time + FRAME
        while True:
            if self.animation.pattern != self.curr_pattern:
                self.selected_row[1] = 0
                self.selected_row[2] = 0
                self.curr_pattern = self.animation.pattern

            self.print_menu(screen)
            if self.handle_input(screen):
                break
            next_frame = wait_for(next_frame)

        curses.nocbreak()
        screen.keypad(False)
        curses.echo()
        curses.curs_set(1)


if __name__ == "__main__":
    logging.basicConfig(
        filename="twinky.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    threading.excepthook = lambda args: log.error(
        "Crash in %s", args.thread.name if args.thread else "a thread",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )
    patterns = [
        load_pattern(BasicBitch()),
        load_pattern(CircusTent()),
        load_pattern(CoiledSpring()),
        load_pattern(Confetti()),
        load_pattern(FallingSnow()),
        load_pattern(Galaxus()),
        load_pattern(Groovy()),
        load_pattern(RainbowStorm()),
        load_pattern(SlidingDoor()),
        load_pattern(SpiralTop()),
    ]
    args = parse_args()
    lights = open_lights(args)
    queue = Queue()
    animation = Blender(patterns, lights, 0, True)
    animation.pattern.randomize()
    load_music(animation.music)
    remote = f"http://{lan_address()}:{PORT}/remote" if args.remote else None
    server = Server(animation, host=listen_host(args), on_command=lambda message: queue.put(remote_command(message)))
    animation.on_frame = server.send
    server.start()
    animation_thread = Thread(
        target=animation_thread_task,
        args=(animation, queue)
    )
    menu = Menu(animation, queue, remote)
    animation_thread.start()
    curses.wrapper(menu)
    animation_thread.join()
    server.stop()
