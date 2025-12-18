import curses
import queue
import threading
import time

from core import ControllablePattern

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
        except queue.Empty:
            pass
        
        colors = animation.render(time.time())
        animation.write(colors)
        while time.time() < next_frame:
            pass
        next_frame += 1/16

def pause(a):
    a.pause_change = True

def unpause(a):
    a.pause_change = False

def switch_idx(idx):
    def func(a):
        a.start_transition(int(idx))
    return func

def set_control_option(idx, option_idx):
    def func(a):
        a.pattern.set_control_option(idx, option_idx)
    return func

def randomize(a):
    a.pattern.randomize()


def make_draw_menu(animation, q):
    def draw_menu(stdscr):
        curses.curs_set(0)
        curses.cbreak()    # React to keys instantly, no Enter needed
        stdscr.nodelay(True)
        stdscr.keypad(True)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)

        def print_menu(screen, selected_row_idx, menu_items):
            screen.clear()
            h, w = screen.getmaxyx()

            for idx, item in enumerate(menu_items):
                y = h // 2 - len(menu_items) // 2 + idx

                if item is None:
                    continue
                elif item == "PATTERN_NAME":
                    x = w // 2 - len(animation.pattern_name) // 2
                    screen.addstr(y, x, animation.pattern_name)
                elif item == "TIME_STR":
                    x = w // 2 - len(animation.time_str) // 2
                    screen.addstr(y, x, animation.time_str)
                elif item in controls:
                    control_idx = controls.index(item)
                    options = animation.pattern.get_control_options(control_idx)
                    option_idx = animation.pattern.get_control_option(control_idx)
                    option = options[option_idx]
                    string = f"{item}: {option}"
                    x = w // 2 - len(string) // 2
                    if selected_row_idx == idx:
                        screen.attron(curses.A_REVERSE)
                        screen.addstr(y, x, item)
                        screen.attroff(curses.A_REVERSE)
                        screen.addstr(y, x + len(item), f": {option}")
                    else:
                        screen.addstr(y, x, string)
                else:
                    x = w // 2 - len(item) // 2
                    if idx == selected_row_idx:
                        screen.attron(curses.A_REVERSE)
                        screen.addstr(y, x, item)
                        screen.attroff(curses.A_REVERSE)
                    else:
                        screen.addstr(y, x, item)

            screen.refresh()

        def get_menu_items(a):
            controls = animation.pattern.get_controls() if isinstance(animation.pattern, ControllablePattern) else []
            patterns = [p.name for p in animation.patterns]
            return [
                '[PAUSED]' if animation.pause_change else '',
                "PATTERN_NAME",
                "TIME_STR",
                None,
            ] + controls + [
                None,
            ] + patterns + [
                None,
                "EXIT",
            ]
            

        lowest_row = 4
        current_row = (
            lowest_row
            if isinstance(animation.pattern, ControllablePattern) else
            get_menu_items(animation).index(animation.pattern.name)
        )
        curr_pattern = animation.pattern
        while True:
            controls = animation.pattern.get_controls() if isinstance(animation.pattern, ControllablePattern) else []
            patterns = [p.name for p in animation.patterns]
            menu_items = get_menu_items(animation)
            highest_row = len(menu_items) - 1
            if current_row > highest_row:
                current_row = highest_row

            if curr_pattern != animation.pattern:
                current_row = (
                    5
                    if isinstance(animation.pattern, ControllablePattern) else
                    menu_items.index(animation.pattern.name)
                )
                curr_pattern = animation.pattern

            print_menu(stdscr, current_row, menu_items)
            key = stdscr.getch()

            if key == curses.KEY_UP:
                current_row -= 1
                if current_row < lowest_row:
                    current_row = highest_row

                while menu_items[current_row] is None:
                    current_row -= 1
                    if current_row < lowest_row:
                        current_row = highest_row

            elif key == curses.KEY_DOWN:
                current_row += 1
                if current_row > highest_row:
                    current_row = lowest_row

                while menu_items[current_row] is None:
                    current_row += 1
                    if current_row > highest_row:
                        current_row = lowest_row

            elif key == curses.KEY_LEFT:
                if menu_items[current_row] in controls:
                    idx = controls.index(menu_items[current_row])
                    num_options = len(animation.pattern.get_control_options(idx))
                    option_idx = animation.pattern.get_control_option(idx)
                    option_idx = (option_idx - 1) % num_options
                    q.put(set_control_option(idx, option_idx))

            elif key == curses.KEY_RIGHT:
                if menu_items[current_row] in controls:
                    idx = controls.index(menu_items[current_row])
                    num_options = len(animation.pattern.get_control_options(idx))
                    option_idx = animation.pattern.get_control_option(idx)
                    option_idx = (option_idx + 1) % num_options
                    q.put(set_control_option(idx, option_idx))

            elif key == ord(' '):
                q.put(unpause if animation.pause_change else pause)

            elif key == ord('q'):
                q.put(_sentinel)
                break

            elif key == ord('r'):
                q.put(randomize)

            elif key == curses.KEY_ENTER or key in [10, 13]:
                item = menu_items[current_row]
                if item == "EXIT":
                    q.put(_sentinel)
                    break
                elif item in patterns:
                    pattern_idx = patterns.index(item)
                    q.put(switch_idx(pattern_idx))

        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.curs_set(1)
    return draw_menu


def get_thread_and_menu(animation):
    q = queue.Queue()
    animation_thread = threading.Thread(
        target=animation_thread_task,
        args=(animation,q,),
    )
    draw_menu = make_draw_menu(animation, q)

    return [animation_thread, draw_menu]
