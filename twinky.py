import curses
import threading
import time
import queue

from pytweening import (
    linear,
    easeInSine,
    easeOutSine,
    easeInOutSine,
    easeOutBounce,
    easeInOutCubic,
)

from colors import (
    BaseColor,
    WindowColor,
    SplitColor,
    FallingColor,
    ColorFuncs,
    periodic_choices,
)
from core import (
    Blender,
    Color,
    Pattern,
    rand,
    choice,
)
from param import (
    Curve,
    const,
    combined_curve,
)
from streamer import (
    Direction,
    Spin,
    StreamerFuncs,
    setcolor_streamer,
    streamer_choices,
    combined_choices,
)
from topologies import (
    MirrorTopology,
    RepeatTopology,
    TurntTopology,
    DistortTopology,
)


def basic_bitch(flash=1.0, flicker=0.5, flitter=0.5, flux=2/3):
    return Pattern(
        "Basic Bitch",
        base_color=BaseColor(l=0),
        flash=flash,
        flicker=Curve(easeInOutSine, [(0, flicker), (3, 0), (6, flicker)]),
        flitter=Curve(easeInOutSine, [(0, 0), (6, flitter), (12, 0)]),
        flux=Curve(easeInOutSine, [(0, 0), (3, flux), (6, 0), (9, -flux), (12, 0)]),
    )
    

def circus_tent():
    return Pattern(
        "Circus Tent",
        base_color=SplitColor(
            count=4,
            funcs=periodic_choices(1.5, [
                [
                    BaseColor(h=0.25, l=-1),
                    BaseColor(h=0.0, l=0, suppress=["sparkles"]),
                    BaseColor(h=0.75,l=-1),
                    BaseColor(h=0.5, l=0, suppress=["sparkles"]),
                ],
                [
                    BaseColor(h=0.25, l=0, suppress=["sparkles"]),
                    BaseColor(h=0.0, l=0, suppress=["sparkles"]),
                    BaseColor(h=0.75, l=0, suppress=["sparkles"]),
                    BaseColor(h=0.5, l=0, suppress=["sparkles"]),
                ],
                [
                    BaseColor(h=0.25, l=0, suppress=["sparkles"]),
                    BaseColor(l=-1),
                    BaseColor(h=0.75, l=0, suppress=["sparkles"]),
                    BaseColor(l=-1),
                ],
                [
                    BaseColor(h=0.25, l=0, suppress=["sparkles"]),
                    BaseColor(h=0.0, l=0, suppress=["sparkles"]),
                    BaseColor(h=0.75, l=0, suppress=["sparkles"]),
                    BaseColor(h=0.5, l=0, suppress=["sparkles"]),
                ],
            ]),
        ),
        topologies=[RepeatTopology(4)],
        sparkles=0.5,
        spin=Curve(easeInOutSine, [(0, 0), (15, 1), (30, 0), (45, -1), (60, 0)]),
        streamers=streamer_choices(
            3,
            [
                [
                    {
                        "move_dir": move_dir,
                        "spin_dir": spin_dir,
                        "spin": Curve(const, [(0, 1), (3, 0.5), (6, 1)]),
                        "length": 1.0,
                        "width": Curve(const, [(0, 0.1), (3, 0.15), (6, 0.1)]),
                        "lifetime": 6.0,
                        "func": StreamerFuncs.WHITEN,
                    } for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                ] for move_dir in [Direction.FROM_BOT, Direction.FROM_TOP]
            ],
        ),
    )

def confetti():
    return Pattern(
        "Confetti",
        sparkles=0.2,
        streamers=streamer_choices(
            1,
            [[
                {
                    "move_dir": Direction.FROM_TOP,
                    "spin_dir": spin_dir,
                    "spin": spin,
                    "width": width,
                    "length": lambda _: choice([0.25, 0.5])(),
                    "lifetime": lambda _: rand(3, 6)(),
                    "func": setcolor_streamer(w=0, h=i/4, s=1, l=0.0),
                }
                for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                for spin, width in [(0.5, 0.1), (1, 0.15), (1.5, 0.2)]
                for i in range(4)
            ]],
            choose=(4, 8),
        )
    )
    
def coiled_spring():
    return Pattern(
        "Coiled Spring",
        base_color=WindowColor(
            0.75,
            [
                BaseColor(w=0.75, s=0.0, l=-0.75, suppress=["sparkles", "streamers"]),
                BaseColor(h=0.5, l=-1),
            ],
        ),
        topologies=[RepeatTopology(3)],
        spiral=Curve(easeOutBounce, [(0, 2), (15, -2), (30, 2)]),
        streamers=streamer_choices(
            2,
            [
                [
                    {
                        "move_dir": Direction.FROM_BOT,
                        "spin_dir": o % 2,
                        "angle": (i/4),
                        "spin": Curve(easeOutBounce, [(0, -2), (15, 2), (30, -2)]),
                        "length": 1,
                        "width": 0.2,
                        "lifetime": 1.0,
                        "func": setcolor_streamer(w=0, s=1, l=0.0),
                    } for i in range(4)
                ] for o in range(4)
            ],
        )
    )

def rainbro():
    return Pattern(
        "Rainbro",
        base_color=BaseColor(l=0),
        topologies=[RepeatTopology(Curve(const, [
                (0, 6),
                (7.5, 8),
                (22.5, 4),
                (37.5, 2),
                (52.5, 3),
                (60, 6),
        ]))],
        flitter=0.1,
        flux=1/16,
        spin=6,
        spiral=Curve(easeInOutSine, [(0, -2), (7.5, 2), (15, -2)]),
        spread=Curve(easeInOutSine, [(0, 1), (15, -1), (30, 1)]),
    )

def twisted_rainbows():
    return Pattern(
        "Twisted Rainbows",
        base_color=SplitColor(3),
        topologies=[RepeatTopology(Curve(const, [
            (0, 1),
            (12, 3),
            (24, 5),
            (36, 4),
            (48, 2),
            (60, 1)
        ]))],
        spin=2.0,
        spread=Curve(easeInOutCubic, [
            (0, 1/4),
            (3, 0),
            (6, -1/4),
            (9, 0),
            (12, 1/4),
        ]),
        spiral=Curve(const, [
            (0, -3), (3, 3),
            (9, -1.5), (15, 1.5),
            (21, -0.5), (27, 0.5),
            (33, -1), (39, 1),
            (45, -2), (51, 2),
            (57, -3), (60, -3)
        ]),
        streamers=streamer_choices(
            1,
            [[
                {
                    "move_dir": move_dir,
                    "spin_dir": spin_dir,
                    "spin": 2.0,
                    "length": 2.0,
                    "width": 0.15,
                    "lifetime": 3,
                    "func": StreamerFuncs.WHITEN,
                }
                for move_dir in [Direction.FROM_BOT, Direction.FROM_TOP]
                for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
            ]],
            choose=(0, 2),
        )
    )

def spiral_top():
    return Pattern(
        "Spiral Top",
        base_color=WindowColor(Curve(linear, [(0, 0), (3, 1)])),
        topologies=[MirrorTopology(3)],
        flux=1/16,
        spin=Curve(easeInSine, [(0, 0), (15, 2), (30, 0), (45, -2), (60, 0)]),
        spiral=Curve(linear, [(0, 0), (7.5, 2), (15, 0), (22.5, -2), (30, 0)]),
        spread=1/3,
        sparkles=0.15,
    )

def sliding_door():
    streamers = [
        [
            [
                {
                    "move_dir": move_dir,
                    "spin_dir": spin_dir,
                    "spin": Curve(const, [(0, 1), (6, 0.5), (12, 1)]),
                    "length": 1.0,
                    "width": Curve(const, [(0, 0.1), (6, 0.15), (12, 0.1)]),
                    "lifetime": 6.0,
                    "func": func,
                } for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
            ] for move_dir in [Direction.FROM_BOT, Direction.FROM_TOP]
        ] for func in [
            setcolor_streamer(h=0.25, l=0, make_white=True),
            setcolor_streamer(h=-0.25, l=0.75, make_white=True),
        ]
    ]

    return Pattern(
        "Sliding Door",
        base_color=WindowColor(
            Curve(easeInOutSine, [(0, 0), (3, 1), (6, 0)]),
            [
                BaseColor(l=-1, spread=False),
                BaseColor(
                    h=Curve(const, [(0, 0), (6, 0.5), (12, 0)]),
                    suppress=["sparkles", "streamers"],
                    spread=False,
                ),
            ],
        ),
        topologies=[MirrorTopology(Curve(const, [
            (0, 4),
            (6, 3),
            (12, 6),
            (18, 2),
            (24, 5),
            (30, 4),
        ]))],
        flux=1/16,
        spread=Curve(easeInOutSine, [(0, 0.5), (15, -0.5), (30, 0.5)]),
        sparkles=0.5,
        streamers=combined_choices([
            streamer_choices(3, streamers[0]),
            streamer_choices(3, streamers[1]),
        ]),
    )

def galaxus(streamers=6, spins=3):
    def sparkle_func(color: Color) -> Color:
        if color.l == -1.0:
            return ColorFuncs.WHITEN(color)
        else:
            return color
            
    streamers = [
        [
            [
                {
                    "move_dir": move_dir,
                    "spin_dir": spin_dir,
                    "angle": (i / streamers) + (o / (streamers * spins)),
                    "spin": 0.5,
                    "length": 1,
                    "width": 0.1,
                    "lifetime": 2,
                    "func": func,
                } for i in range(streamers)
            ] for o in range(spins)
        ] for move_dir, spin_dir, func in zip(
            [Direction.FROM_BOT, Direction.FROM_TOP],
            [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE],
            [
                setcolor_streamer(
                    l=0,
                    h=Curve(easeInOutSine, [(0, 0), (7.5, -0.25), (15, 0), (22.5, 0.25), (30, 0)]),
                ),
                setcolor_streamer(
                    l=0,
                    h=Curve(easeInOutSine, [(0, 0.5), (5, 0.25), (10, 0.5), (15, 0.75), (20, 0.5)]),
                ),
            ],
        )
    ]

    return Pattern(
        "Galaxus",
        sparkles=0.25,
        sparkle_func=sparkle_func,
        streamers=combined_choices([
            streamer_choices(2, streamers[0]),
            streamer_choices(2, streamers[1], delay_offset=1),
        ])
    )

def falling_snow():
    return Pattern(
        "Falling Snow",
        base_color=FallingColor(),
        flitter=0.25,
        flux=1/8,
        sparkles=Curve(easeInOutSine, [(0, 0.25), (6, 0.5), (12, 0.25)]),
        streamers=streamer_choices(
            1,
            [[
                {
                    "move_dir": move_dir,
                    "spin_dir": spin_dir,
                    "spin": spin,
                    "width": width,
                    "length": 0.5,
                    "lifetime": lifetime,
                    "func": setcolor_streamer(w=0.2, h=0, l=-1),
                }
                for move_dir in [Direction.FROM_BOT, Direction.FROM_TOP]
                for spin_dir in [Spin.CLOCKWISE, Spin.COUNTERCLOCKWISE]
                for lifetime in [3, 4.5, 6, 7.5]
                for spin, width in [(2, 0.2), (3, 0.15)]
            ]],
            choose=(0, 1),
        )
    )

def turning_windows(splits=8, repeats=4):
    base_windows = [None] * splits
    windows = []
    for i in range(splits):
        windows.append(base_windows[:i] + [BaseColor()] + base_windows[(i+1):])

    return Pattern(
        "Turning Windows",
        base_color=SplitColor(
            splits,
            periodic_choices(0.25, windows),
            suppress=["sparkles"],
        ),
        topologies=[
            RepeatTopology(repeats),
            TurntTopology(
                repeats,
                combined_curve([
                    Curve(easeOutSine, [(0, 0), (15, 1)]),
                    Curve(easeOutSine, [(0, 0), (15, -1)]),
                ])
            ),
        ],
        spin=Curve(easeInOutSine, [(0, 0), (15, -1), (30, 0), (45, 1), (60, 0)]),
        spread=Curve(linear, [(0, 0), (15, 3.0/splits), (30, 0), (45, -3.0/splits), (60, 0)]),
        sparkles=0.75,
    )

def groovy():
    return Pattern(
        "Groovy",
        base_color=SplitColor(
            8,
            [
                BaseColor(
                    l=0.0, spread=False, suppress=["sparkles"],
                    h=Curve(easeInOutSine, [(0, 1/8), (15, 0), (30, 1/8)]),
                ),
                BaseColor(),
                BaseColor(),
                BaseColor(
                    l=0.0, spread=False, suppress=["sparkles"],
                ),
                BaseColor(
                    l=0.0, spread=False, suppress=["sparkles"],
                ),
                BaseColor(),
                BaseColor(),
                BaseColor(
                    l=0.0, spread=False, suppress=["sparkles"],
                    h=Curve(easeInOutSine, [(0, -1/8), (10, 0), (20, -1/8)]),
                ),
            ],
        ),
        topologies=[
            DistortTopology(
                easeInOutSine,
                Curve(easeInOutSine, [(0, 0.5), (30, -0.5), (60, 0.5)]),
                Curve(easeInOutSine, [(0, -0.5), (30, 0.5), (60, -0.5)]),
                Curve(easeInOutSine, [(0, 0.5), (5, 0.3), (10, 0.5), (15, 0.7), (20, 0.5)])
            ),
            MirrorTopology(2),
        ],
        sparkles=0.25,
    )

patterns = [
    basic_bitch(),
    circus_tent(),
    coiled_spring(),
    confetti(),
    falling_snow(),
    rainbro(),
    sliding_door(),
    spiral_top(),
    twisted_rainbows(),
    turning_windows(),
    groovy(),
    galaxus(),
]

# animation.animate()

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

def switch_name(name):
    def func(a):
        idx = [i for i, p in enumerate(a.patterns) if p.name == name][0]
        a.start_transition(idx)
    return func

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
        current_row = 0
        menu_items = ["Pause", "Unpause", "Quit"]

        def print_menu(screen, selected_row_idx):
            screen.clear()
            h, w = screen.getmaxyx()

            item = f"{'[PAUSED] ' if animation.pause_change else ''}({round(animation._t - animation._init_t, 2)}): {animation.pattern_name}"
            x = w // 2 - len(item) // 2
            y = h // 2 - len(menu_items) // 2 - 2
            screen.addstr(y, x, item)

            for idx, item in enumerate(menu_items):
                x = w // 2 - len(item) // 2
                y = h // 2 - len(menu_items) // 2 + idx
                if idx == selected_row_idx:
                    screen.attron(curses.A_REVERSE)
                    screen.addstr(y, x, item)
                    screen.attroff(curses.A_REVERSE)
                else:
                    screen.addstr(y, x, item)
            screen.refresh()

        while True:
            print_menu(stdscr, current_row)
            key = stdscr.getch()

            if key == curses.KEY_UP:
                if current_row > 0:
                    current_row -= 1
            elif key == curses.KEY_DOWN:
                if current_row < len(menu_items) - 1:
                    current_row += 1
            elif key == curses.KEY_ENTER or key in [10, 13]:
                if current_row == 0:
                    q.put(pause)
                elif current_row == 1:
                    q.put(unpause)
                if current_row == len(menu_items) - 1:
                    q.put(_sentinel)
                    break

                stdscr.addstr(curses.LINES - 1, 0, animation.pattern_name)

        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.curs_set(1)
    return draw_menu


def console_run(animation, q):
    valid_commands = ["Pause", "Unpause", "Quit"]
    pattern_names = [p.name for p in animation.patterns]
    pattern_idx = [f"{i}" for i in range(len(animation.patterns))]

    while True:
        command = input(f"{animation.pattern_name} >> ")
        if command in valid_commands:
            if command == "Pause":
                q.put(pause)
            elif command == "Unpause":
                q.put(unpause)
            elif command == "Quit":
                q.put(_sentinel)
                break
        elif command in pattern_names:
            q.put(switch_name(command))
        elif command in pattern_idx:
            q.put(switch_idx(command))


if __name__ == "__main__":
    animation = Blender(
        patterns,
        start_idx=-1,
        pause_change=False,
    )
    q = queue.Queue()
    animation_thread = threading.Thread(
        target=animation_thread_task,
        args=(animation,q,),
    )
    animation_thread.start()
    # console_run(animation, q)
    draw_menu = make_draw_menu(animation, q)
    curses.wrapper(draw_menu)
    animation_thread.join()
