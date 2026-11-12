import argparse
import curses
import logging
import os
from queue import Queue, Empty
import socket
import threading
from threading import Thread
import time
from commands import (
    change_option,
    pauseplay,
    random_pattern,
    randomize_feature,
    randomize_pattern,
    remote_command,
    save_music,
    set_option,
    start,
    switch_pattern,
    toggle_configured,
)
from core import FRAME, wait_for
from device import Lights
import layout
import look
from server import PORT, Server
from sim import SimLights

log = logging.getLogger("twinky")

_sentinel = object()

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
    parser.add_argument(
        "--import-look",
        metavar="FILE",
        help="write the pattern for a look Bermuda exported as JSON to looks/, played from the next start, and stop",
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
    args = parse_args()
    if args.import_look:
        print("Wrote", look.import_look(args.import_look))
        raise SystemExit
    lights = open_lights(args)
    queue = Queue()
    animation = start(lights)
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
