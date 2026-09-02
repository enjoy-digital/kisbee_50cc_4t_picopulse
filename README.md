# 🐝 Kisbee 50cc 4T PicoPulse — RP2040 Speed-Signal Emulator

[Français](README_FR.md)

> [!WARNING]
> This is an experimental educational project, not a road-approved product. Modifying a vehicle’s
> speed-limiting system may be illegal, unsafe, and incompatible with its insurance or approval.

Your Peugeot Kisbee 50 4T is electronically limited: the ECU watches a speed-sensor signal and
starts to cut power when it thinks you’re going too fast (typically ~45 km/h).

This project uses a small RP2040 board running MicroPython to **pretend to be the wheel sensor** and
feed the ECU a “safe” low-speed signal, even when the scooter is actually going faster.

Simple, cheap, reversible. 🙂

## Repository contents

- [`kisbee.py`](kisbee.py) — MicroPython firmware, installed on the board as `main.py`.
- [`diagram.png`](diagram.png) — conceptual signal-flow overview.
- [`images/`](images/) — privacy-sanitized assembly and installation photos.

## Background and reference

The initial investigation for this project was informed by the community experiments documented
in [“2021 Peugeot Kisbee 4T Euro5 derestriction using Arduino (also works for Euro4)” on
Reddit](https://www.reddit.com/r/scooters/comments/13rbkxj/2021_peugeot_kisbee_4t_euro5_derestriction_using/).
Thanks to the original author and contributors for sharing their findings.

---

## How the stock speed limiter works

![Kisbee speed sensor and ECU overview](diagram.png)

*Conceptual signal-flow overview—not a pin-level electrical schematic. The required ECU interface
and protection components are described in the deployment section.*

On the stock Kisbee:

- A **pickup sensor** looks at the **clutch bell**, which has **4 protrusions** (bumps).
- The **final-drive reduction** between the clutch bell and rear wheel is fixed: the clutch bell
  turns about **11× per wheel revolution**.
- So the ECU sees:

  - `4 pulses / bell turn × ~11 bell turns / wheel rev ≈ 44 pulses / wheel rev`.

- With a typical rear tyre (110/70-12), the wheel circumference is about **1.44 m**.

From that, we can approximate:

```text
f_Hz ≈ 8.5 × v_kmh
```

Examples (stock gearing & 110/70-12):

| Road speed | Sensor frequency |
|-----------:|------------------|
| 30 km/h    | ≈ 255 Hz         |
| 40 km/h    | ≈ 339 Hz         |
| 45 km/h    | ≈ 381 Hz         |
| 50 km/h    | ≈ 424 Hz         |
| 60 km/h    | ≈ 509 Hz         |

Community reports and scope captures suggest that, on the 45 km/h moped version, the ECU starts
limiting a bit below **~400 Hz** (≈ 45 km/h by the table).

**Key idea:** if we keep the ECU’s *seen* frequency under this threshold, it will not activate the
  limiter, even if the real wheel speed is higher.

### Why not just unplug the speed sensor?

Simply disconnecting the sensor does **not** work:

- The ECU continuously checks that a **valid pulse train** is present.
- If the signal disappears (open circuit, no pulses, constant level), the ECU detects a fault.
- When that happens:
  - The **ECU warning LED** turns on.
  - The ECU falls back to a **safe/limp mode** with an even **lower speed limit** than stock.

So instead of removing the signal, we must **replace it with a plausible one**: something that looks
like a real sensor output, but stays below the limiter threshold. That’s exactly what this project
does.

---

### Common mechanical solution: modifying the clutch bell

A very common “workshop” or DIY trick to defeat the limiter is to **physically reduce the number of teeth/bulges** seen by the sensor on the clutch bell.

From the factory, the bell has **4 protrusions** that pass in front of the pickup sensor.
Some people:

- Open the transmission,
- Remove the clutch bell,
- **Grind off or cut away 2 of the 4 protrusions**.

Result:

- For the same real wheel speed, the sensor now sees **half the pulses**.
- The ECU thinks the scooter is going **twice as slow** as it really is, so it never reaches the
  limiter frequency.
- This is functionally similar to what we do electronically: **lower the apparent frequency** seen by the ECU.

However, this mechanical approach has several downsides:

- It requires **more teardown** (remove the cover, belt, clutch, bell, etc.).
- Once you have cut the protrusions, it’s **not really reversible**:
  - To go back to stock, you need to **buy a new clutch bell**.
- The machining needs to be done cleanly and symmetrically:
  imbalance or rough edges can cause **vibration** or reduce part lifetime.

The RP2040-based solution in this project achieves **the same effect on frequency**, but:

- Involves **no permanent modification** of the engine or transmission,
- Is **easily reversible** (just unplug the box and reconnect the sensor),
- And can be removed or reinstalled in a few minutes.

---

## Tech basics – What the RP2040-Zero actually does

The MicroPython firmware is a tiny fixed-frequency pulse generator with a built-in status LED:

- On startup it turns the onboard RGB LED **green**.
  This confirms that `main.py` reached its initialization stage; the LED does not independently
  prove that the ECU-facing waveform is correct.

- It outputs an endless train of short pulses on **GPIO 11** at **320 Hz**.
  With the stock Kisbee gearing and tyre, that corresponds to roughly **38 km/h**, safely below the
  ECU’s ~380–400 Hz limiter threshold.

- Each period is:

  - `1_000_000 / 320 ≈ 3125 µs` total,
  - with a **200 µs active-high pulse** on GPIO 11 and the rest idle, i.e. about **6 % duty cycle**.

- Timing is based on `utime.ticks_us()`:
  the code schedules the next edge using microsecond ticks, so the average frequency stays close to
  320 Hz even though MicroPython adds a bit of jitter.

- On the scooter side, this 3.3 V pulse train is turned into an ECU-compatible sensor signal using
  a small interface:
  typically a **pull-up plus “pull-low only” stage** (open-drain style) or a tiny
  **transistor/MOSFET board** to match the original sensor’s behaviour. This stage may invert the
  controller-side pulse.

Effectively, the real wheel sensor is disconnected from the ECU, and this firmware feeds it a
constant, plausible “I’m cruising at ~38 km/h” signal instead.
The variator and engine are then free to push past the stock speed limit without the ECU retarding
ignition or flagging a sensor fault.


---

## Deployment

### 1. Hardware you need

- **Appropriately rated 12 V → 5 V DC-DC converter** and a small inline fuse (from the scooter’s
  12 V supply to USB/5 V for the board)
  Example: [step-down 12 V → 5 V module](https://www.amazon.fr/dp/B0FKM9X3J4)

- **Waveshare-compatible RP2040-Zero board**. The supplied firmware uses GPIO 11 for the signal and
  GPIO 16 for this board’s RGB status LED. Other RP2040 boards require adapting these pins and
  possibly the LED code.
  Specifications: [Waveshare RP2040-Zero](https://www.waveshare.com/rp2040-zero.htm)

- **ECU signal interface**, such as a correctly rated open-drain transistor/MOSFET stage and any
  required pull-up components. Do not connect an ECU or 12 V signal directly to an RP2040 GPIO.

- **Automotive connectors / crimp kit** to make a clean inline harness to the ECU speed sensor
  Example: [connector assortment](https://www.amazon.fr/dp/B0FBWDKK8L)

- **Weather-resistant enclosure, wire, heat-shrink tubing, strain relief, and cable ties**.

Product listings and prices change; the links above are examples, not endorsements. Check every
part’s voltage rating, pinout, and suitability before ordering or connecting it.

---

### 2. Wiring & mounting

> **Do this at your own risk; double-check polarity and wiring.**

![Complete plug-in harness before installation](images/complete-plug-in-harness.jpg)

*Complete plug-in harness before installation: automotive connectors, power converter, and the
enclosed RP2040 controller.*

1. **Power:**
   - Work with the ignition off and disconnect the battery before modifying the harness.
   - Take **12 V** and **GND** from the scooter, preferably from a fused, ignition-switched line.
   - Feed them into the **12 V→5 V converter**.
   - Verify the converter’s polarity and 5 V output with a multimeter before connecting the board.
   - Power the RP2040-Zero through USB-C or its specified 5 V/VSYS input—never through its 3.3 V pin.
   - Make sure the RP2040-Zero GND and ECU GND are common.

2. **Speed signal:**
   - Confirm the speed-sensor connector and ECU-side signal wire for your exact model and year;
     wiring can vary.
   - Unplug the **speed sensor connector** and route the ECU side to your box.
   - Connect **GPIO 11** (`PIN = 11` in `kisbee.py`) to the low-voltage input of the interface stage.
   - Connect the ECU’s **speed input** to the output of that interface stage.
   - Never expose the RP2040 GPIO to 5 V, 12 V, or an unverified ECU signal.
   - Keep the original sensor connector accessible so you can revert to stock if needed.

   ![RP2040-Zero connected to the signal-injector harness](images/rp2040-signal-injector-wiring.jpg)

   *Close-up of the RP2040-Zero connected to the signal-injector harness, before closing the
   enclosure.*

3. **Mechanical mount:**
   - Put the RP2040-Zero + DC-DC + any interface board in a **weather-resistant enclosure** and
     protect the connections with heat-shrink tubing.
   - Fix it under the seat or fairing with **zip ties**, away from exhaust and moving parts.
   - Add strain relief and make sure cables can’t rub through, get pinched, or collect water.

   ![Final system installed on the scooter](images/installed-under-seat.jpg)

   *Example of the final system installed beneath the scooter bodywork.*

You’ll end up with a **plug-in harness** that can be removed to go fully back to stock.

---

### 3. Programming the RP2040-Zero

You only need to set this up once. After that, the normal startup sequence is:
**power on → green LED → confirm normal operation**.
Program the board on the bench, disconnected from the scooter wiring and power supply.

1. **Flash MicroPython:**
   - Download the latest stable UF2 from the official
     [MicroPython page for the Waveshare RP2040-Zero](https://micropython.org/download/WAVESHARE_RP2040_ZERO/).
   - Hold **BOOTSEL** on the RP2040-Zero and plug it into your PC.
   - A drive named `RPI-RP2` appears.
   - Copy the downloaded UF2 file to it and wait for the board to reboot.

2. **Install [`mpremote`](https://docs.micropython.org/en/latest/reference/mpremote.html) on your PC:**

   ```bash
   pipx install mpremote
   ```

   Alternatively:

   ```bash
   python3 -m pip install --user mpremote
   ```

3. **Copy the script as `main.py` (auto-run on boot)** from the repository directory:

   ```bash
   mpremote fs cp kisbee.py :main.py
   mpremote reset
   ```

   `mpremote` automatically selects the first USB serial device. If several are connected, run
   `mpremote connect list` and add `connect <port>` before `fs cp`.

   After this, every time the RP2040-Zero powers up, it automatically starts generating pulses.

---

### 4. Bench validation

- Confirm that the status LED turns **green**.
- With an oscilloscope or logic analyser, verify approximately **320 Hz** and a **200 µs
  active-high pulse** on GPIO 11.
- Verify the interface stage separately and confirm that its ECU-facing voltage and polarity match
  the original sensor before connecting it to the scooter.

---

### 5. Using it on the scooter

* Plug the RP2040-Zero into your **5 V supply** on the scooter.
* Turn the ignition on so the 12 V → 5 V converter powers the board.
* Check the board’s **green LED**:

  * **Green LED on** → the script initialized. It does not replace the electrical checks described
    above or confirm by itself that the ECU receives the expected signal.
* From there, the ECU just sees a nice, tame ~38 km/h forever – what you do with the *real* speed is up to you.

Ride responsibly. 🏆

---

## Safety, legality & responsibility

This project is **experimental** and is published for **educational purposes only**.

- It is intended as a way to **discover and learn electronics, microcontrollers and ECUs**,
  especially for young people who want to understand how their scooter works at a technical level.
- We deliberately **do not sell ready-made kits**:
  the idea is that anyone using this project should **design, assemble and understand their own setup**,
  not just plug in a black box.

By using this code and the associated ideas, you agree that:

- You are **solely responsible** for any modification you make to your vehicle.
- You must ensure that your scooter **remains compliant with local laws and regulations**
  (speed limits for mopeds, licence category, type approval, etc.).
- Any change to the ECU signals or speed limitation can:
  - **Affect safety** (braking distance, handling, crash severity),
  - **Void warranty**,
  - **Affect insurance cover** or how an insurer or expert evaluates an accident.

If this project is used by minors, it should be **under the supervision of a responsible adult**
who understands the risks and the legal context.

Nothing in this repository is legal advice, and the author(s) cannot be held liable for:

- Damage to people, vehicles or property,
- Loss of insurance coverage,
- Fines, legal issues or any other consequence arising from the use or misuse of this information.

If in doubt, keep it on the **bench** as a fun electronics experiment, and ride your scooter in fully **legal** configuration.

---

## License and trademarks

The source code is licensed under the [BSD 2-Clause License](LICENSE).

“Peugeot” and “Kisbee” are used only to identify vehicle compatibility. This independent project
is not affiliated with, sponsored by, or endorsed by the vehicle manufacturer. Product and company
names remain the property of their respective owners.
