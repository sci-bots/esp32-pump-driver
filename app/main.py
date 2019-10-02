import gc

from bootstrap import fetch_update
from machine import Pin, I2C, UART
import asyn
import bootstrap
import motor
import rpc
import uasyncio as asyncio
import wifimgr


def main():
    # Attempt to connect to Wifi network.
    wlan = wifimgr.get_connection()

    # Bind to UART 2 to handle RPC requests.
    uart = UART(2, baudrate=115200)
    uart_awriter = asyncio.StreamWriter(uart, {})
    uart_areader = asyncio.StreamReader(uart)

    # Bind I2C connection for controlling motor drivers
    i2c = I2C(scl=Pin(5), sda=Pin(4), freq=100000)

    # Reclaim memory associated with any temporary allocations.
    gc.collect()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(rpc.rpc(uart_areader, uart_awriter))

    # Reclaim memory associated with any temporary allocations.
    gc.collect()

    g = globals()
    g['wlan'] = wlan
    g['motor_ctrl'] = motor.GroveMotorControl(i2c)
