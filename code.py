# Minimal code.py for Pico / Pico 2 W - Clean Launcher
import supervisor
import os
import time
import digitalio
import pwmio
import board
import asyncio
from duckyinpython import *

# Sleep at the start to allow the device to be recognized by the host
time.sleep(.5)

# Turn off automatically reloading when files are written
supervisor.runtime.autoreload = False

# Setup the onboard LED
if(board.board_id == 'raspberry_pi_pico' or board.board_id == 'raspberry_pi_pico2'):
    led = pwmio.PWMOut(board.LED, frequency=5000, duty_cycle=0)
elif(board.board_id == 'raspberry_pi_pico_w' or board.board_id == 'raspberry_pi_pico2_w'):
    led = digitalio.DigitalInOut(board.LED)
    led.switch_to_output()


async def run_payload_on_startup():
    """Delegates entirely to duckyinpython's native DS 3.0 engine."""
    progStatus = getProgrammingStatus()
    if not progStatus:
        if "loot.bin" in os.listdir("/"):
            print("loot.bin exists, skipping.")
        else:
            payload_path = selectPayload() # returns path like 'payload.dd'
            print(f"Executing Ducky 3.0 Script natively via {payload_path}")
            
            # duckyinpython's runScript handles file reading, IFs, WHILEs, and variables automatically
            await runScript(payload_path) 
    else:
        print("Programming Mode Active")


async def main_loop():
    global led, button1
    
    # Core tasks required for duckyinpython.py to function
    tasks = [
        asyncio.create_task(monitor_buttons(button1)),
        asyncio.create_task(run_payload_on_startup()),
        asyncio.create_task(monitor_led_changes())
    ]
    
    # Board-specific LED task
    if(board.board_id == 'raspberry_pi_pico_w' or board.board_id == 'raspberry_pi_pico2_w'):
        tasks.append(asyncio.create_task(blink_pico_w_led(led)))
    else:
        tasks.append(asyncio.create_task(blink_pico_led(led)))
        
    await asyncio.gather(*tasks)

asyncio.run(main_loop())