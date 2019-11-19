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
import itertools as it
import logging
logging.basicConfig(level=logging.INFO)
import time

from asyncserial import BackgroundSerialAsync
from rpc_host import AsyncRemote
import host

try:
    global adevice
    adevice.close()
    time.sleep(0.5)
except Exception as exception:
    print(exception)

# Get serial port connected to UART2 on Huzzah32 ESP32 board.
uart2_port = host.get_port(vid=0x0403, pid=0x6015)
print('found uart2 port: %s' % uart2_port.device)

adevice = BackgroundSerialAsync(port=uart2_port.device, baudrate=115200)
aremote = AsyncRemote(adevice)

# # Configuration

# For each pump and valve:
#  - `addr`: I2C address of corresponding Grove motor control board
#  - `index`: output index (0-3) within the Grove motor control board
pumps = OrderedDict([('16-3', {'addr': 16, 'index': 3}),
                     ('16-4', {'addr': 16, 'index': 4}),
                     ('17-1', {'addr': 17, 'index': 1}),
                     ('17-2', {'addr': 17, 'index': 2}),
                     ('17-3', {'addr': 17, 'index': 3}),
                     ('17-4', {'addr': 17, 'index': 4}),
                     ('18-1', {'addr': 18, 'index': 1}),
                     ('18-2', {'addr': 18, 'index': 2}),
                     ('18-3', {'addr': 18, 'index': 3}),
                     ('18-4', {'addr': 18, 'index': 4})])
    
valves = OrderedDict([('15-1', {'addr': 15, 'index': 1}),
                      ('15-2', {'addr': 15, 'index': 2}),
                      ('15-3', {'addr': 15, 'index': 3}),
                      ('15-4', {'addr': 15, 'index': 4}),
                      ('16-1', {'addr': 16, 'index': 1}),
                      ('16-2', {'addr': 16, 'index': 2})])

i2c_devices = asyncio.run_coroutine_threadsafe(aremote.call('i2c.scan'),
                                               aremote.device.loop).result()
driver_addresses = sorted(set(d['addr'] for d in it.chain(pumps.values(),
                                                          valves.values())))
missing_drivers = set(driver_addresses) - set(i2c_devices)
if missing_drivers:
    logging.warning('The following pump/valve I2C driver boards were '
                    'not found: %s' % sorted(missing_drivers))
host.control_widget(aremote, pumps, valves)
