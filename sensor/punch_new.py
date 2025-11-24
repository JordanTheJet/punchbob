#!/usr/bin/env python3
"""
punch.py

Sensor + session logic for the GY-521 (MPU-6050).

- Configures accelerometer to ±4 g (sens = 8192.0 LSB/g)
- Continuously reads acceleration
- Detects "hits" based on dynamic acceleration
- Tracks the maximum dynamic acceleration over the session
- Exposes run_punch_session() which returns that max (in g)

Use this as a backend module. A separate script can import
run_punch_session() and decide how to classify / play sounds.
"""

import smbus
import time
import math

# ---------- I2C / MPU6050 setup ----------

BUS_ID = 1
bus = smbus.SMBus(BUS_ID)

PWR_MGMT_1   = 0x6B
ACCEL_CONFIG = 0x1C
ACCEL_XOUT_H = 0x3B
WHO_AM_I     = 0x75

ADDR = None  # will be set by detect_mpu()


def detect_mpu():
    """
    Probe 0x68 and 0x69 for an MPU-6050 and set the global ADDR.
    Raises RuntimeError if not found.
    """
    global ADDR

    for addr in (0x68, 0x69):
        try:
            who = bus.read_byte_data(addr, WHO_AM_I)
            if who == 0x68:
                ADDR = addr
                print(f"Found MPU-6050 at 0x{addr:02X} (WHO_AM_I=0x{who:02X})")
                return
            else:
                print(f"Device at 0x{addr:02X} but WHO_AM_I=0x{who:02X}, skipping")
        except OSError:
            # No device responded at this address, try the next one
            continue

    raise RuntimeError("No MPU-6050 found at 0x68 or 0x69. Check wiring and i2cdetect.")


def write_reg(reg, value):
    """Write a single byte to a device register."""
    bus.write_byte_data(ADDR, reg, value)


def read_word(reg):
    """
    Read a signed 16-bit big-endian value starting at reg.
    Returns a Python int in range [-32768, 32767].
    """
    high = bus.read_byte_data(ADDR, reg)
    low  = bus.read_byte_data(ADDR, reg + 1)
    value = (high << 8) | low
    if value >= 0x8000:
        value = -((65535 - value) + 1)
    return value


def init_mpu():
    """
    Detect the MPU, wake it up, and set accelerometer to ±4 g.

    Returns
    -------
    sens : float
        Sensitivity in LSB/g. For ±4 g, sens = 8192.0.
    """
    detect_mpu()

    # Wake up (clear sleep bit)
    write_reg(PWR_MGMT_1, 0x00)
    time.sleep(0.1)

    # Set accel range to ±4 g (AFS_SEL = 1 -> 0x08)
    # ACCEL_CONFIG bits [4:3] = AFS_SEL:
    #   0 = ±2 g, 1 = ±4 g, 2 = ±8 g, 3 = ±16 g
    write_reg(ACCEL_CONFIG, 0x10)
    time.sleep(0.1)

    sens = 4096.0  # LSB per g for ±4 g range
    print("MPU-6050 configured: ±4 g, sens=8192.0 LSB/g")
    return sens


def read_accel_g(sens):
    """
    Read raw accelerometer data and convert to g units.

    Parameters
    ----------
    sens : float
        Sensitivity in LSB/g (8192.0 for ±4 g).

    Returns
    -------
    (ax_g, ay_g, az_g) : tuple of floats
        Acceleration along X, Y, Z in g units.
        On I2C error, returns (None, None, None).
    """
    try:
        ax_raw = read_word(ACCEL_XOUT_H)
        ay_raw = read_word(ACCEL_XOUT_H + 2)
        az_raw = read_word(ACCEL_XOUT_H + 4)
    except OSError as e:
        print(f"I2C read error: {e}")
        return None, None, None

    ax_g = ax_raw / sens
    ay_g = ay_raw / sens
    az_g = az_raw / sens
    return ax_g, ay_g, az_g


def run_punch_session():
    """
    Run a "punch session" using the accelerometer.

    Hit detection is based on dynamic acceleration (approx magnitude - 1 g).
    We track the maximum dynamic g across all hits in the session.

    Session ends when the user presses Ctrl+C.

    Returns
    -------
    session_max_dyn_g : float
        Maximum dynamic acceleration (in g) observed in the session.
        If no meaningful hits are detected, this may be ~0.0.
    """
    sens = init_mpu()

    in_hit = False
    hit_peak_dyn_g = 0.0
    hit_below_end_counter = 0
    session_max_dyn_g = 0.0

    # Hit detection thresholds (in g, dynamic component)
    HIT_START_G = 0.7   # start counting a hit above this
    HIT_END_G   = 0.3   # consider hit done when below this
    END_SAMPLES = 5     # consecutive samples below end threshold

    print("Punch session running. Hit the target as much as you like.")
    print("Press Ctrl+C to end the session.\n")

    try:
        while True:
            ax_g, ay_g, az_g = read_accel_g(sens)
            if ax_g is None:
                # Skip this sample on I2C error
                time.sleep(0.01)
                continue

            # Total magnitude including gravity
            a_mag_g = math.sqrt(ax_g * ax_g + ay_g * ay_g + az_g * az_g)

            # Approximate dynamic part by subtracting 1 g
            a_dyn_g = max(0.0, a_mag_g - 1.0)

            if not in_hit:
                # Look for start of a hit
                if a_dyn_g > HIT_START_G:
                    in_hit = True
                    hit_peak_dyn_g = a_dyn_g
                    hit_below_end_counter = 0
            else:
                # Update peak for this hit
                if a_dyn_g > hit_peak_dyn_g:
                    hit_peak_dyn_g = a_dyn_g

                # Check for end of hit
                if a_dyn_g < HIT_END_G:
                    hit_below_end_counter += 1
                else:
                    hit_below_end_counter = 0

                if hit_below_end_counter >= END_SAMPLES:
                    # End of this hit
                    print(f"Hit peak: {hit_peak_dyn_g:.2f} g")
                    if hit_peak_dyn_g > session_max_dyn_g:
                        session_max_dyn_g = hit_peak_dyn_g

                    in_hit = False
                    hit_peak_dyn_g = 0.0
                    hit_below_end_counter = 0

            # ~100 Hz loop
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nEnding punch session.")
        print(f"Session max dynamic acceleration: {session_max_dyn_g:.2f} g")
        return session_max_dyn_g


if __name__ == "__main__":
    # If you run this file directly, just run a session and print the max.
    max_g = run_punch_session()
    print(f"\nFinal session max (dynamic g): {max_g:.2f}")

