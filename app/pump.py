import gc
import uasyncio as asyncio


async def pump(motor_driver, pin, pulses, on_ms=50, off_ms=150):
    '''
    Parameters
    ----------
    motor_driver : grove_i2c_motor.BaseDriver
        Driver I2C proxy exposing ``digital_write()`` method.
    pin : int
        Motor output pin (e.g., ``grove_i2c_motor.IN1``).
    pulses : int
        Number of pulses.
    on_ms : int, optional
        Duration for which output should be turned **on**, in milliseconds.
    off_ms : int, optional
        Duration for which output should be turned **off**, in milliseconds.
    '''
    await asyncio.sleep_ms(0)
    for i in range(pulses):
        print('pump %s (%d/%d) HI' % (motor_driver.addr, i + 1, pulses))
        motor_driver.digital_write(pin, 1)
        await asyncio.sleep_ms(on_ms)
        print('pump %s (%d/%d) LOW' % (motor_driver.addr, i + 1, pulses))
        motor_driver.digital_write(pin, 0)
        await asyncio.sleep_ms(off_ms)
