import gc
import machine

import uasyncio as asyncio


# See http://wiki.seeedstudio.com/Grove-I2C_Motor_Driver_V1.3/
MotorSpeedSet             = 0x82
PWMFrequenceSet           = 0x84
DirectionSet              = 0xaa
MotorSetA                 = 0xa1
MotorSetB                 = 0xa5
Nothing                   = 0x01


class GroveMotorControl:
    def __init__(self, i2c):
        self.i2c = i2c
        self.directions = {}

        # Direction I2C command consists of 3 bytes:
        #
        #  1. Direction command code (i.e., `DirectionSet`)
        #  2. 4-bit encoding; each bit corresponding to the direction of the
        #     respective output on the motor driver.
        #  3. Termination character (i.e., `Nothing`)
        #
        # To avoid memory fragmentation, we allocate a [buffer][1] to be reused
        # by all I2C motor driver commands. Note that bytes **(1)** and **(3)**
        # are constant. The `set_direction()` function below sets the value of
        # the 4-bit encoding in the buffer (i.e., **(2)** above) before sending
        # the command to the motor driver.
        #
        # [1]: http://docs.micropython.org/en/v1.9.3/wipy/reference/speed_python.html#buffers
        self.direction_buffer = bytearray(3)
        self.direction_buffer[0] = DirectionSet
        self.direction_buffer[2] = Nothing

    def set_direction(self, address, index, on):
        '''
        Parameters
        ----------
        address : int
            I2C address of motor driver.
        index : int
            Index of motor output to modify.
        on : bool
            If ``True``, turn corresponding motor output **on**. Otherwise,
            turn it **off**.
        '''
        self.directions.setdefault(address, 0x0)
        if on:
            self.directions[address] |= (1 << index)
        else:
            self.directions[address] &= ~(1 << index)
        self.direction_buffer[1] = self.directions[address]
        print('set_direction(%d, %s)' %
              (address, bin(self.direction_buffer[1])))
        self.i2c.writeto(address, self.direction_buffer)

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
        for i in range(pulses):
            print('pump %s (%d/%d) HI' % (address, i + 1, pulses))
            self.set_direction(address, index, True)
            await asyncio.sleep_ms(on_ms)
            print('pump %s (%d/%d) LOW' % (address, i + 1, pulses))
            self.set_direction(address, index, False)
            await asyncio.sleep_ms(off_ms)
        gc.collect()
        return address

    def set_speed(self, address, speed_a, speed_b):
        i2c_buffer = bytearray(4)
        i2c_buffer[0] = MotorSpeedSet
        i2c_buffer[1] = int(max(0, speed_a) * 255)
        i2c_buffer[2] = int(max(0, speed_b) * 255)
        i2c_buffer[-1] = Nothing
        self.i2c.writeto(address, i2c_buffer)
        gc.collect()
