#!/usr/bin/env python3
"""Kisbee 50cc 4T PicoPulse firmware.

Generate a fixed-frequency pulse train on GPIO 11 for a suitable ECU signal
interface. Never connect an ECU voltage directly to the RP2040. On an
RP2040-Zero, the onboard RGB LED on GPIO 16 turns green after initialization.
"""

# Copyright (c) 2025-2026 Florent Kermarrec
# SPDX-License-Identifier: BSD-2-Clause

import utime
import neopixel
from machine import Pin

# Constants ----------------------------------------------------------------------------------------

PIN = 11
FREQ_HZ = 320
PULSE_US = 200
LED_PIN = 16

# Pulse Generator ----------------------------------------------------------------------------------


class PulseGen:
    def __init__(self, pin, freq_hz, pulse_us):
        if freq_hz <= 0:
            raise ValueError("freq_hz must be positive")

        period_us = 1_000_000 // freq_hz
        if not 0 < pulse_us < period_us:
            raise ValueError("pulse_us must be between 0 and the pulse period")

        self.pin = Pin(pin, Pin.OUT, value=0)
        self.period_us = period_us
        self.pulse_us = pulse_us
        self.t_next = utime.ticks_us()

    def run(self):
        while True:
            # Wait for next pulse time.
            while utime.ticks_diff(self.t_next, utime.ticks_us()) > 0:
                pass

            # Send an active-high pulse to the interface stage.
            self.pin.value(1)
            utime.sleep_us(self.pulse_us)
            self.pin.value(0)

            # Preserve the average frequency without passing a negative duration
            # to sleep_us() if an iteration overruns.
            self.t_next = utime.ticks_add(self.t_next, self.period_us)
            remaining_us = utime.ticks_diff(self.t_next, utime.ticks_us())
            if remaining_us > 0:
                utime.sleep_us(remaining_us)
            else:
                self.t_next = utime.ticks_add(utime.ticks_us(), self.period_us)


# Main ---------------------------------------------------------------------------------------------


def main():
    # Validate and initialize the pulse generator before signaling readiness.
    gen = PulseGen(PIN, FREQ_HZ, PULSE_US)

    np = neopixel.NeoPixel(Pin(LED_PIN), 1)
    try:
        np[0] = (0, 255, 0)
        np.write()

        print("RP2040 PulseGen starting (Kisbee 50cc 4T PicoPulse)...")
        print(f"  Pin: GPIO{PIN}")
        print(f"  Frequency: {FREQ_HZ} Hz")
        print(f"  Pulse time: {PULSE_US} us (GPIO active-high)")
        print(f"  Period: {gen.period_us} us")
        print(f"  LED: Green on GPIO{LED_PIN}\n")

        gen.run()
    finally:
        # Leave the interface input and status LED in a defined state on error.
        gen.pin.value(0)
        np[0] = (0, 0, 0)
        np.write()


if __name__ == "__main__":
    main()
