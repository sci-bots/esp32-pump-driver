import gc
import json

from machine import Pin, I2C, UART
import bootstrap
import config
import machine
import motor
import ota
import rpc
import uasyncio as asyncio
import util
import wifimgr


def main():
    LED_PIN = config.CONFIG.get('led_pin', 13)
    pin = Pin(LED_PIN, Pin.OUT)
    pin.value(0)

    # Attempt to connect to Wifi network.
    wlan = wifimgr.get_connection()

    # Bind to UART 2 to handle RPC requests.
    uart = UART(2, baudrate=115200)
    uart_awriter = asyncio.StreamWriter(uart, {})
    uart_areader = asyncio.StreamReader(uart)

    # Bind I2C connection for controlling motor drivers
    i2c_config = config.CONFIG.get('i2c', {})
    i2c = I2C(scl=Pin(i2c_config.get('scl', 22)),
              sda=Pin(i2c_config.get('sda', 23)),
              freq=i2c_config.get('freq', 10000))

    motor_ctrl = motor.GroveMotorControl(i2c)

    # Expose globals to RPC context
    context = globals().copy()
    # Expose locals to RPC context ([note MicroPython `locals()` caveat][1])
    #
    # [1]: https://github.com/micropython/micropython/wiki/Differences#differences-by-design
    context.update(locals())

    # Explicitly add local variables to context, since (see [here][1]):
    #
    # > MicroPython optimizes local variable handling and does not record or
    # > provide any introspection info for them, e.g. **locals() doesn't have
    # > entries for locals.**
    #
    # [1]: https://github.com/micropython/micropython/wiki/Differences#differences-by-design
    context['i2c'] = i2c
    context['motor_ctrl'] = motor_ctrl
    context['uart'] = uart
    context['wlan'] = wlan

    # Remove `rpc` module from context to avoid recursive reference in
    # `rpc.rpc()` function.
    rpc = context.pop('rpc', None)

    # Reclaim memory associated with any temporary allocations.
    gc.collect()

    loop = asyncio.get_event_loop()

    pin = Pin(LED_PIN, Pin.OUT)
    pin.value(1)

    # Start RPC task.
    loop.run_until_complete(rpc.rpc(uart_areader, uart_awriter,
                                    context=context))

    pin.value(0)

    # Reclaim memory associated with any temporary allocations.
    gc.collect()
