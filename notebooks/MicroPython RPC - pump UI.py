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
import asyncio
import functools as ft
import json
import platform
import sys
import threading
import time

from asyncserial import BackgroundSerialAsync
from rpc_host import AsyncRemote
import asyncserial
import ipywidgets as ipw

try:
    adevice.close()
    time.sleep(.5)
except:
    pass

adevice = BackgroundSerialAsync(port='COM3', baudrate=115200)
aremote = AsyncRemote(adevice)

await aremote.call('gc.mem_free')

# Turn off all pump outputs.
for i in range(4):
    await aremote.call('motor_ctrl.set_direction', 15, i, False)
# Set all pump outputs to 100% duty cycle. This lets the pulsing code
# determine on/off durations for pump outputs.
await aremote.call('motor_ctrl.set_speed', 15, 1, 1)

# +
loop = asyncio.get_event_loop()

pumps = ('H20 -> CFA', 'CFA -> CFB', 'CFB -> CFA')
pumps_help = ('Water to Cell-free A', 'Cell-free A -> Cell-free B', 'Cell-free B -> Cell-free A')

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
for i, (label, help_i) in enumerate(zip(pumps, pumps_help)):
    button_i = ipw.Button(description='Pump %s' % label, tooltip=help_i)
    pulses_i = ipw.IntSlider(min=0, max=125, value=25, description='Pulses')
    button_i.on_click(ft.partial(do_pump, 15, i, pulses_i))
    buttons.append(ipw.HBox([button_i, pulses_i]))
    
single_pump_ui = ipw.VBox(buttons)

# Multiple pump UI (i.e., one button to start multiple pumps simultaneously)
pulses = ipw.IntSlider(min=0, max=125, value=25, description='Pulses')
button_pump = ipw.Button(description='Pump', tooltip='''
1) Use checkboxes to select one or more pumps.
2) Select number of pulses.
3) Click here to execute pulses.'''.strip())
checkboxes = ipw.VBox([ipw.Checkbox(description=p, index=True) for p in pumps])

def on_multi_pump(index, pulses, *args, **kwargs):
    for i, c in enumerate(checkboxes.children):
        if c.value:
            do_pump(index, i, pulses)
            
button_pump.on_click(ft.partial(on_multi_pump, 15, pulses))

multi_pump_ui = ipw.HBox([checkboxes, pulses, button_pump])

accordion = ipw.Accordion(children=[single_pump_ui, multi_pump_ui])
accordion.set_title(0, 'Single pump')
accordion.set_title(1, 'Multiple pumps')

label = ipw.Label()

ipw.VBox([accordion, label])
# -

