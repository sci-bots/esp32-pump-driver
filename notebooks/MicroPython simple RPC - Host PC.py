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
import threading

import asyncserial


async def wrap_background_loop(func, serial_loop, *args, **kwargs):
    loop = asyncio.get_event_loop()
    co_result = asyncio.Event()

    def co_func():
        async def _func(*args, **kwargs):
            try:
                co_result.result = await func(*args, **kwargs)
            except Exception as exception:
                co_result.result = exception
            finally:
                loop.call_soon_threadsafe(co_result.set)

        serial_loop.create_task(_func(*args, **kwargs))

    serial_loop.call_soon_threadsafe(co_func)
    await co_result.wait()
    if isinstance(co_result.result, Exception):
        raise co_result.result 
    else:
        return co_result.result 


class BackgroundSerialAsync:
    def __init__(self, *args, **kwargs):
        loop_started = threading.Event()

        def start():
            if platform.system() == 'Windows':
                # Need to use Proactor (IOCP) event loop for serial port.
                loop = asyncio.ProactorEventLoop()
            else:
                loop = asyncio.new_event_loop()
            self.device = asyncserial.AsyncSerial(*args, loop=loop, **kwargs)
            self.loop = loop
            loop.call_soon(loop_started.set)
            loop.run_forever()

        self.thread = threading.Thread(target=start)
        self.thread.daemon = True
        self.thread.start()
        
        loop_started.wait()

    def write(self, *args, **kwargs):
        return wrap_background_loop(self.device.write, self.loop, *args, **kwargs)
    
    def read_exactly(self, *args, **kwargs):
        return wrap_background_loop(self.device.read_exactly, self.loop, *args, **kwargs)
    
    def read(self, *args, **kwargs):
        return wrap_background_loop(self.device.read, self.loop, *args, **kwargs)
    
    async def readline(self):
        data = b''
        while True:
            data += await self.read(1)
            if data and data[-1] == ord(b'\n'):
                return data
    
    def close(self):
        self.loop.call_soon_threadsafe(self.device.close)
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# +
import sys
import serial

import json


class RemoteBase:
    def __init__(self, device):
        self.device = device
    
    def _base_call(self, base_message, command, *args, **kwargs):
        raise NotImplementedError
        
    def call(self, command, *args, **kwargs):
        return self._base_call({}, command, *args, **kwargs)
    
    def await_(self, command, *args, **kwargs):
        return self._base_call({'async': True}, command, *args, **kwargs)
    
    def create_task(self, command, *args, **kwargs):
        return self._base_call({'async': 'task'}, command, *args, **kwargs)
    
    
class Remote(RemoteBase):
    def _base_call(self, base_message, command, *args, **kwargs):
        message = base_message.copy()
        message.update({'command': command, 'args': args,
                        'kwargs': kwargs})
        self.device.write(json.dumps(message).encode('utf8') + b'\r\n')
        response = json.loads(self.device.readline())
        if 'error' in response:
            raise RuntimeError('Error: `%s`' % response['error'])
        return response['result']
            
            
class AsyncRemote(RemoteBase):
    async def _base_call(self, base_message, command, *args, **kwargs):
        message = base_message.copy()
        message.update({'command': command, 'args': args,
                        'kwargs': kwargs})
        await self.device.write(json.dumps(message).encode('utf8') + b'\r\n')
        response = json.loads(await self.device.readline())
        if 'error' in response:
            raise RuntimeError('Error: `%s`' % response['error'])
        return response['result']


# -

with BackgroundSerialAsync(port='COM18', baudrate=115200) as adevice:
    aremote = AsyncRemote(adevice)
    await aremote.call('gc.collect')
    display(await aremote.call('gc.mem_free'))

with serial.Serial('COM18', baudrate=115200) as device:
    remote = Remote(device)
    remote.call('gc.collect')
    display(remote.call('gc.mem_free'))

# +
API_TOKEN = 'c8005277d02736892f49d9e5402b73ded68fba9d'

with BackgroundSerialAsync(port='COM18', baudrate=115200) as adevice:
# await aremote.call('ota.fetch_update', API_TOKEN, tag='v0.4')
# print(await aremote.call('open("/ota-next/app/main.py").read'))
# print(await aremote.call('gc.mem_free'))
# remote.call('open("/VERSION").read')
# remote.call('ota.swap', '/ota-previous', '', '/ota-next')
