# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.4'
#       jupytext_version: 1.2.4
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# +
from __future__ import print_function, division
from collections import OrderedDict
import asyncio
import functools as ft
import json
import logging
import os
import platform
import sys
import threading
import time
logging.basicConfig(level=logging.INFO)

from asyncserial import BackgroundSerialAsync
from rpc_host import AsyncRemote
import asyncserial
import ipywidgets as ipw
import serial
import serial.tools.list_ports
try:
    from PySide2 import QtGui, QtCore, QtWidgets
    # Enable Qt support for Jupyter.
    %gui qt5
except:
    pass

# Get list of serial ports that are available for use (i.e., can be opened successfully).
available_ports = []


def get_port(vid, pid):
    try:
        port = next(p for p in serial.tools.list_ports.comports()
                    if p.vid == vid and p.pid == pid)
    except StopIteration:
        raise IOError('No matching port found.')
    device = serial.Serial(port.device)
    device.close()
    return port


# +
try:
    global adevice
    adevice.close()
    time.sleep(0.5)
except Exception as exception:
    print(exception)

# Get serial port connected to UART2 on Huzzah32 ESP32 board.
uart2_port = get_port(vid=0x0403, pid=0x6015)
print('found uart2 port: %s' % uart2_port.device)

adevice = BackgroundSerialAsync(port=uart2_port.device, baudrate=115200)
aremote = AsyncRemote(adevice)

async def init_i2c_grove_board(aremote):
    try:
        # Turn off all pump outputs.
        for i in range(4):
            await aremote.call('motor_ctrl.set_direction', 15, i, False)
            await aremote.call('gc.collect')
        # Set all pump outputs to 100% duty cycle. This lets the pulsing code
        # determine on/off durations for pump outputs.
        await aremote.call('motor_ctrl.set_speed', 15, 1, 1)
    except RuntimeError as exception:
        if 'ETIMEDOUT' in str(exception):
            raise RuntimeError('Error communicating with I2C motor grove.')

async def init():
    # Show free memory (in bytes) on ESP32.
    await init_i2c_grove_board(aremote)
    return (await aremote.call('gc.mem_free'))
            
    
await init()

# +
# # Configuration

# For each pump and valve:
#  - `addr`: I2C address of corresponding Grove motor control board
#  - `index`: output index (0-3) within the Grove motor control board
pumps = OrderedDict([('1', {'addr': 15, 'index': 0}),
                     ('2', {'addr': 15, 'index': 1})])
valves = OrderedDict([('i', {'addr': 15, 'index': 2}),
                      ('ii', {'addr': 15, 'index': 3})])

# -----------------------------------------------------------------------------

# # Debug tools
def launch_file_manager():
    global file_manager_
    root_path = os.path.realpath('..')
    file_manager_ = aremote.file_manager(root_path)
    file_manager_.setMinimumSize(1280, 720)
    file_manager_.show()
    return file_manager_
    
def reset_esp32():
    future = asyncio.run_coroutine_threadsafe(aremote.reset(), adevice.loop)

    def on_done(f):
        print('Reset successful (%d bytes free)' % f.result())
        asyncio.run_coroutine_threadsafe(asyncio.wait_for(init_i2c_grove_board(aremote),
                                                          timeout=4),
                                         aremote.device.loop)
    future.add_done_callback(on_done)

debug_buttons = []

button_reset = ipw.Button(description='Reset ESP32')
button_reset.on_click(lambda *args: reset_esp32())
debug_buttons.append(button_reset)
try:
    QtCore
    button_file_manager = ipw.Button(description='File manager')
    button_file_manager.on_click(lambda *args: launch_file_manager())
    debug_buttons.append(button_file_manager)
except:
    pass

hbox_debug = ipw.HBox(debug_buttons)

# -----------------------------------------------------------------------------

# # Pump control
loop = asyncio.get_event_loop()

# Single pump UI (i.e., one button per pump); can still run more than one at a time
def do_pump(addr, index, pulses, *args, **kwargs):
    loop = asyncio.get_event_loop()
    loop.create_task(asyncio.wait_for(aremote.create_task('motor_ctrl.pump',
                                                          addr, index,
                                                          pulses.value,
                                                          on_ms=400,
                                                          off_ms=200),
                                      timeout=2))
    
def set_direction(addr, index, on, *args, **kwargs):
    return asyncio.wait_for(aremote.call('motor_ctrl.set_direction', addr, index, on), timeout=2)
    
    
buttons = []
for name_i, pump_i in pumps.items():
    button_i = ipw.Button(description='Pump %s' % name_i)
    pulses_i = ipw.IntSlider(min=0, max=125, value=25, description='Pulses')
    button_i.on_click(ft.partial(do_pump, pump_i['addr'], pump_i['index'], pulses_i))
    buttons.append(ipw.HBox([button_i, pulses_i]))
    
single_pump_ui = ipw.VBox(buttons)

# Multiple pump UI (i.e., one button to start multiple pumps simultaneously)
pulses = ipw.IntSlider(min=0, max=125, value=25, description='Pulses')
button_pump = ipw.Button(description='Pump', tooltip='''
1) Use checkboxes to select one or more pumps.
2) Select number of pulses.
3) Click here to execute pulses.'''.strip())
checkboxes = ipw.VBox([ipw.Checkbox(description=name_i, index=True)
                       for name_i in pumps])

def on_multi_pump(pulses, *args, **kwargs):
    for c in checkboxes.children:
        if c.value:
            pump = pumps[c.description]
            do_pump(pump['addr'], pump['index'], pulses)
            
button_pump.on_click(ft.partial(on_multi_pump, pulses))

multi_pump_ui = ipw.HBox([checkboxes, pulses, button_pump])

accordion = ipw.Accordion(children=[single_pump_ui, multi_pump_ui, hbox_debug])
accordion.set_title(0, 'Single pump')
accordion.set_title(1, 'Multiple pumps')
accordion.set_title(2, 'Debug')

label = ipw.Label()

pump_ui = ipw.VBox([accordion, label])

def valve_widget(addr, index, name, options=None):
    if options is None:
        options=['A', 'B']
    valve = ipw.RadioButtons(options=options,
                             description='Valve %s' % name)
    
    def on_toggle(addr, index, message, *args, **kwargs):
        value = (message['new'] == 1)
        
        async def switch_valve():
            await aremote.call('motor_ctrl.set_direction', addr, index, value)
            await aremote.call('gc.collect')
            
        loop = asyncio.get_event_loop()
        loop.create_task(asyncio.wait_for(switch_valve(), timeout=2))
        
    valve.observe(ft.partial(on_toggle, addr, index), names='index')
    return valve

valves_ui = ipw.VBox([valve_widget(valve['addr'], valve['index'], name)
                      for name, valve in valves.items()])

ipw.HBox([pump_ui, valves_ui])
