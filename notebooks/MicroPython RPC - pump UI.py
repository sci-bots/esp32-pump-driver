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

from PySide2 import QtGui, QtCore, QtWidgets
from asyncserial import BackgroundSerialAsync
from rpc_host import AsyncRemote
import asyncserial
import ipywidgets as ipw
import serial
import serial.tools.list_ports

# Enable Qt support for Jupyter.
# %gui qt5

# Local imports
from file_manager import host_tree, RemoteFileTree, load_project_structure_, list_to_tree, copy

# Get list of serial ports that are available for use (i.e., can be opened successfully).
available_ports = []

for p in serial.tools.list_ports.comports():
    try:
        device = serial.Serial(p.device)
        device.close()
        available_ports.append(p.device)
    except Exception:
        pass

display([p for p in available_ports])

# +
try:
    global adevice
    adevice.close()
    time.sleep(0.5)
    if adevice.device.ser.port not in available_ports:
        available_ports.append(adevice.device.ser.port)
except Exception as exception:
    print(exception)

port = available_ports[0]
adevice = BackgroundSerialAsync(port=port, baudrate=115200)
aremote = AsyncRemote(adevice)

# Flush serial data to reach clean state.
await asyncio.wait_for(aremote.flush(), timeout=4)

display(await asyncio.wait_for(aremote.call('gc.mem_free'), timeout=2))

async def init_i2c_grove_board(aremote):
    try:
        # Turn off all pump outputs.
        for i in range(4):
            await aremote.call('motor_ctrl.set_direction', 15, i, False)
        # Set all pump outputs to 100% duty cycle. This lets the pulsing code
        # determine on/off durations for pump outputs.
        await aremote.call('motor_ctrl.set_speed', 15, 1, 1)
    except RuntimeError as exception:
        if 'ETIMEDOUT' in str(exception):
            raise RuntimeError('Error communicating with I2C motor grove.')

await asyncio.wait_for(init_i2c_grove_board(aremote), timeout=2)

# +
root_path = os.path.realpath('..')
tree = host_tree(root_path)
tree.show()

relative_root = tree.model().filePath(tree.rootIndex())
remote_tree = RemoteFileTree()
remote_tree.show()

widget = QtWidgets.QWidget()
combined = QtWidgets.QHBoxLayout()
combined.addWidget(tree)
combined.addWidget(remote_tree)
widget.setLayout(combined)
widget.show()


async def refresh_remote_tree():
    file_info = await aremote.call('util.walk_files', '/')
    model = remote_tree.model()
    model.removeRows(0, model.rowCount())
    main_dict = list_to_tree(sorted(file_info))
    load_project_structure_(main_dict, remote_tree)
    remote_tree.expandAll()


def on_copy_request(loop, sender, label, links):
    relative_root = tree.model().filePath(tree.rootIndex())
    async def wrapped():
        remote_changed = False
        for link in links:
            if link.startswith('remote:///'):
                source = link[len('remote://'):]
                print('copy `%s` to `%s`' % (source,
                                             relative_root + source))
                await aremote.copy_rtol(source, relative_root + source)
            elif link.startswith('file:///'):
                source = os.path.relpath(link[len('file:///'):],
                                         relative_root)
                target = ('/' + source).replace('\\', '/')
                print('copy `%s` to `%s`' % (source, target))
                await aremote.copy_ltor(link[len('file:///'):], target)
                remote_changed = True
            else:
                print('no match: `%s`' % link)
        if remote_changed:
            await refresh_remote_tree()
        
    loop.call_soon_threadsafe(loop.create_task, wrapped())
            
loop = aremote.device.loop
tree.copy_request.connect(ft.partial(on_copy_request, loop, tree, 'local'))
remote_tree.copy_request.connect(ft.partial(on_copy_request, loop, remote_tree, 'remote'))

asyncio.run_coroutine_threadsafe(refresh_remote_tree(), loop)

# +
# future = asyncio.run_coroutine_threadsafe(aremote.reset(), adevice.loop)
# future.add_done_callback(lambda f: print('Reset successful (%d bytes free)' %
#                                          f.result()))
# -

# -------------------------------------------------------------------------------

# +
import ipywidgets as ipw


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

# ------------------------------------------------------------------------

# +
import shutil
import tempfile as tf

import editor

if platform.system() == 'Windows' and 'EDITOR' not in os.environ:
    os.environ['EDITOR'] = 'notepad'

# +
async def view_remote(remote_path):
    '''Open remote path in host text editor.'''
    name = os.path.basename(remote_path)
    tmp_dir = tf.mkdtemp(prefix='rpc_')
    output_path = os.path.join(tmp_dir, name)
    print(output_path, tmp_dir)
    try:
        await aremote.copy_rtol(remote_path, output_path)
        print(output_path)
        editor.edit(output_path)
    finally:
        shutil.rmtree(tmp_dir)

# Run in background serial event loop.
task = asyncio.run_coroutine_threadsafe(view_remote('/LICENSE'), adevice.loop)
# -

await aremote.flush()
