import curses
from queue import Queue, Empty
from threading import Thread
import time
from core import Blender
from control import *

_sentinel = object()

def animation_thread_task(animation, command_queue):
    start_time = time.time()
    animation.init(start_time)
    next_frame = start_time + (1/16)
    while True:
        try:
            command = command_queue.get(False)
            if command is not None:
                if command is _sentinel:
                    print("Stopping animation")
                    command_queue.put(_sentinel)
                    break
                else:
                    command(animation)
                command_queue.task_done()
        except Empty:
            pass
        
        colors = animation.render(time.time())
        animation.write(colors)
        while time.time() < next_frame:
            pass
        next_frame += 1/16

def switch_pattern(idx):
    def func(a):
        a.start_transition(idx)
    return func

def change(fidx, cidx, step):
    def func(a):
        a.pattern.change(fidx, cidx, step)

    return func

def setoption(fidx, cidx, oidx):
    def func(a):
        a.pattern.set(fidx, cidx, oidx)

    return func

def randomize(a):
    a.pattern.randomize()

def pauseplay(a):
    a.pause_change = not a.pause_change

class Menu:
    def __init__(self, animation, queue):
        self.animation = animation
        self.queue = queue
        self.selected_column = 0
        self.selected_row = [0, 0, 0]
        self.curr_pattern = animation.pattern

    def print_menu(self, screen):
        screen.clear()
        _, w = screen.getmaxyx()
        midw = w // 2
        colw = (w - 2) // 3

        pattern = self.animation.pattern
        feature = pattern.features[self.selected_row[1]]

        # top shows animation name and time if not paused
        title = f"{self.animation.pattern.name}: "
        title += 'PAUSED' if self.animation.pause_change else self.animation.time_str
        screen.addstr(1, midw - (len(title) // 2), title)

        # left shows patterns
        for i, p in enumerate(self.animation.patterns):
            mid = colw // 2
            pair = 0
            if self.selected_row[0] == i:
                pair = 2 if self.selected_column == 0 else 3
            screen.addstr(
                3 + i,
                mid - (len(p.name) // 2),
                p.name,
                curses.color_pair(pair),
            )

        # middle shows main settings
        for i, f in enumerate(pattern.features):
            mid = (colw // 2) + colw
            pair = 0
            if self.selected_row[1] == i:
                pair = 2 if self.selected_column == 1 else 3
            screen.addstr(
                3 + i,
                mid - (len(f.name) // 2),
                f.name,
                curses.color_pair(pair),
            )

        # right shows control settings
        for i, c in enumerate(feature.visible_controls()):
            s = f"{c.name}: {c.selected.name}"
            mid = (colw // 2) + (2 * colw)
            pair = 0
            if self.selected_row[2] == i:
                pair = 2 if self.selected_column == 2 else 3
            screen.addstr(
                3 + i,
                mid - (len(s) // 2),
                s,
                curses.color_pair(pair),
            )

        screen.refresh()

    def handle_input(self, screen) -> bool:
        maxrow = [
            len(self.animation.patterns),
            len(self.animation.pattern.features),
            len(self.animation.pattern.features[self.selected_row[1]].visible_controls()),
        ]

        key = screen.getch()
        if key == ord('q'):
            self.queue.put(_sentinel)
            return True
        elif key == ord('r'):
            self.queue.put(randomize)
        elif key == curses.KEY_ENTER or key in [10, 13]:
            if self.selected_column == 0:
                self.queue.put(switch_pattern(self.selected_row[0]))
        elif key == ord(' '):
            self.queue.put(pauseplay)
        elif key == curses.KEY_LEFT:
            self.selected_column = (self.selected_column - 1) % 3
            self.selected_row[self.selected_column] %= maxrow[self.selected_column]
        elif key == curses.KEY_RIGHT:
            self.selected_column = (self.selected_column + 1) % 3
            self.selected_row[self.selected_column] %= maxrow[self.selected_column]
        elif key == curses.KEY_UP:
            self.selected_row[self.selected_column] -= 1
            self.selected_row[self.selected_column] %= maxrow[self.selected_column]
        elif key == curses.KEY_DOWN:
            self.selected_row[self.selected_column] += 1
            self.selected_row[self.selected_column] %= maxrow[self.selected_column]
        elif key in [ord('-'), ord('_')] :
            if self.selected_column == 1 and self.animation.pattern.features[self.selected_row[1]].controls[0].name == "Enabled":
                self.queue.put(setoption(self.selected_row[1], self.selected_row[2], 1))
            elif self.selected_column == 2:
                self.queue.put(change(self.selected_row[1], self.selected_row[2], -1))
        elif key in [ord('='), ord('+')] :
            if self.selected_column == 1 and self.animation.pattern.features[self.selected_row[1]].controls[0].name == "Enabled":
                self.queue.put(setoption(self.selected_row[1], self.selected_row[2], 0))
            elif self.selected_column == 2:
                self.queue.put(change(self.selected_row[1], self.selected_row[2], 1))
        return False

    def __call__(self, screen):
        curses.curs_set(0)
        curses.cbreak()
        screen.nodelay(True)
        screen.keypad(True)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_BLUE)

        while True:
            if self.animation.pattern != self.curr_pattern:
                self.selected_row[1] = 0
                self.selected_row[2] = 0
                self.curr_pattern = self.animation.pattern

            self.print_menu(screen)
            if self.handle_input(screen):
                break

        curses.nocbreak()
        screen.keypad(False)
        curses.echo()
        curses.curs_set(1)


if __name__ == "__main__":
    patterns = [
        BasicBitch(),
        CircusTent(),
        CoiledSpring(),
        Confetti(),
        DroppingPlates(),
        FallingSnow(),
        Galaxus(),
        Groovy(),
        SlidingDoor(),
        SpiralTop(),
        TurningWindows(),
    ]
    queue = Queue()
    animation = Blender(patterns, -1, False)
    animation.pattern.randomize()
    animation_thread = Thread(
        target=animation_thread_task,
        args=(animation, queue)
    )
    menu = Menu(animation, queue)
    animation_thread.start()
    curses.wrapper(menu)
    animation_thread.join()
