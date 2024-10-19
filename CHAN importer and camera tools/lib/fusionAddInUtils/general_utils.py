#  Copyright 2022 by Autodesk, Inc.
#  Permission to use, copy, modify, and distribute this software in object code form
#  for any purpose and without fee is hereby granted, provided that the above copyright
#  notice appears in all copies and that both that copyright notice and the limited
#  warranty and restricted rights notice below appear in all supporting documentation.
#
#  AUTODESK PROVIDES THIS PROGRAM "AS IS" AND WITH ALL FAULTS. AUTODESK SPECIFICALLY
#  DISCLAIMS ANY IMPLIED WARRANTY OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR USE.
#  AUTODESK, INC. DOES NOT WARRANT THAT THE OPERATION OF THE PROGRAM WILL BE
#  UNINTERRUPTED OR ERROR FREE.

import os
import traceback
import adsk.core

app = adsk.core.Application.get()
ui = app.userInterface

# Attempt to read DEBUG flag from parent config.
try:
    from ... import config
    DEBUG = config.DEBUG
except:
    DEBUG = False


def log(message: str, level: adsk.core.LogLevels = adsk.core.LogLevels.InfoLogLevel, force_console: bool = False):
    """Utility function to easily handle logging in your app.

    Arguments:
    message -- The message to log.
    level -- The logging severity level.
    force_console -- Forces the message to be written to the Text Command window. 
    """    
    # Always print to console, only seen through IDE.
    print(message)  

    # Log all errors to Fusion log file.
    if level == adsk.core.LogLevels.ErrorLogLevel:
        log_type = adsk.core.LogTypes.FileLogType
        app.log(message, level, log_type)

    # If config.DEBUG is True write all log messages to the console.
    if DEBUG or force_console:
        log_type = adsk.core.LogTypes.ConsoleLogType
        app.log(message, level, log_type)


def handle_error(name: str, show_message_box: bool = False):
    """Utility function to simplify error handling.

    Arguments:
    name -- A name used to label the error.
    show_message_box -- Indicates if the error should be shown in the message box.
                        If False, it will only be shown in the Text Command window
                        and logged to the log file.                        
    """    

    log('===== Error =====', adsk.core.LogLevels.ErrorLogLevel)
    log(f'{name}\n{traceback.format_exc()}', adsk.core.LogLevels.ErrorLogLevel)

    # If desired you could show an error as a message box.
    if show_message_box:
        ui.messageBox(f'{name}\n{traceback.format_exc()}')

import time
import threading
import functools
from functools import wraps
geom_to_str = lambda x: functools.reduce(lambda a,b: f'{a}, {b}', [f'{r}: {s}' for r,s in zip("xyz", [f'{v*10:.4f} mm' for v in x.asArray()])])

def throttle(interval, guarantee_last=True):
    def decorator(func):
        last_call_time = 0
        pending_call = None
        lock = threading.Lock()
        timer = None  # To keep track of the active delayed call

        def wrapper(*args, **kwargs):
            nonlocal last_call_time, pending_call, timer
            current_time = time.time()

            def execute_call():
                nonlocal last_call_time, pending_call, timer
                last_call_time = current_time
                func(*args, **kwargs)
                pending_call = None
                timer = None

            with lock:
                # Cancel any previous scheduled call if a new one comes in before executing
                if timer is not None:
                    timer.cancel()

                # If too soon since last call
                if current_time - last_call_time < interval:
                    pending_call = (args, kwargs)
                    if guarantee_last:
                        # Schedule the latest call
                        timer = threading.Timer(interval - (current_time - last_call_time), execute_call)
                        timer.start()
                    return
                else:
                    execute_call()

        return wrapper

    return decorator