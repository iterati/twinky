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
        h, w = screen.getmaxyx()
        colw = (w - 2) // 3

        pattern = self.animation.pattern
        feature = pattern.features[self.selected_row[1]]

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

        for i in range(3, h-2):
            screen.addstr(i, 0, '\u2551')
            screen.addstr(i, colw, '\u2502')
            screen.addstr(i, colw*2, '\u2502')
            screen.addstr(i, w-1, '\u2551')

        line = '\u255a'
        line += '\u2550' * (colw - len(line))
        line += '\u2567'
        line += '\u2550' * ((2*colw) - len(line))
        line += '\u2567'
        line += '\u2550' * ((w - 1) - len(line))
        line += '\u255d'
        screen.addstr(h-2, 0, line)

        # left shows patterns
        for i, p in enumerate(self.animation.patterns):
            pair = curses.color_pair(0)
            if self.selected_row[0] == i:
                pair = curses.color_pair(1)
                if self.selected_column == 0:
                    pair |= curses.A_BOLD
            screen.addstr(3 + i, 2, p.name, pair)

        # middle shows main settings
        for i, f in enumerate(pattern.features):
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
        return [
            len(self.animation.patterns),
            len(self.animation.pattern.features),
            len(self.animation.pattern.features[self.selected_row[1]].visible_controls()),
        ]

    def handle_input(self, screen) -> bool:
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
            if self.selected_column == 1 and self.animation.pattern.features[self.selected_row[1]].controls[0].name == "Enabled":
                self.queue.put(setoption(self.selected_row[1], 0, 1))
                self.selected_row[2] = 0
            elif self.selected_column == 2:
                self.queue.put(change(self.selected_row[1], self.selected_row[2], -1))
        elif key in [ord('='), ord('+')] :
            if self.selected_column == 1 and self.animation.pattern.features[self.selected_row[1]].controls[0].name == "Enabled":
                self.queue.put(setoption(self.selected_row[1], 0, 0))
                self.selected_row[2] = 0
            elif self.selected_column == 2:
                self.queue.put(change(self.selected_row[1], self.selected_row[2], 1))
        return False

    def __call__(self, screen):
        curses.curs_set(0)
        curses.cbreak()
        screen.nodelay(True)
        screen.keypad(True)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)

        start_time = time.time()
        next_frame = start_time + (1/16)
        while True:
            if self.animation.pattern != self.curr_pattern:
                self.selected_row[1] = 0
                self.selected_row[2] = 0
                self.curr_pattern = self.animation.pattern

            self.print_menu(screen)
            if self.handle_input(screen):
                break
            while time.time() < next_frame:
                pass
            next_frame += 1/16

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
        FallingSnow(),
        Galaxus(),
        Groovy(),
        RainbowStorm(),
        SlidingDoor(),
        SpiralTop(),
        Twirl(),
    ]
    queue = Queue()
    animation = Blender(patterns, 7, False)
    animation.pattern.randomize()
    animation_thread = Thread(
        target=animation_thread_task,
        args=(animation, queue)
    )
    menu = Menu(animation, queue)
    animation_thread.start()
    curses.wrapper(menu)
    animation_thread.join()
