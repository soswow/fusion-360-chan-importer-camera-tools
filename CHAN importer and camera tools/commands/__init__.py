from .chan_to_canvas import entry as chan_to_canvas_entry
from .sticky_canvas import entry as sticky_canvas_entry

commands = [
    chan_to_canvas_entry,
    sticky_canvas_entry
]


# Assumes you defined a "start" function in each of your modules.
# The start function will be run when the add-in is started.
def start():
    for command in commands:
        command.start()


# Assumes you defined a "stop" function in each of your modules.
# The stop function will be run when the add-in is stopped.
def stop():
    for command in commands:
        command.stop()