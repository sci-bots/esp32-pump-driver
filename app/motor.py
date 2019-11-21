import gc

import grove_i2c_motor as gm

import pump


class GroveMotorControl:
    def __init__(self, i2c):
        self.i2c = i2c
        self.pins = gm.IN1, gm.IN2, gm.IN3, gm.IN4

    async def pump(self, address, index, pulses, on_ms=50, off_ms=150):
        '''
        Parameters
        ----------
        address : int
            I2C address of motor driver.
        index : int
            Index of motor output to modify.
        pulses : int
            Number of pulses.
        on_ms : int, optional
            Duration for which output should be turned **on**, in milliseconds.
        off_ms : int, optional
            Duration for which output should be turned **off**, in milliseconds.
        '''
        result = await pump.pump(self.i2c, address, self.pins[index], pulses,
                                 on_ms=on_ms, off_ms=off_ms)
        gc.collect()
        return result

    def set_direction(self, address, index, value):
        driver = gm.BaseDriver(self.i2c, address)
        driver.digital_write(self.pins[index], value)
        del driver
        gc.collect()
