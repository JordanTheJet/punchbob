#!/usr/bin/env python3
"""
Test script for accelerometer sensor (ADXL345 or MPU6050)

Usage:
    python3 sensor_test.py

This will read accelerometer data and display force values in real-time.
"""

import time
import sys

# Try importing sensor libraries
try:
    import smbus
    SMBUS_AVAILABLE = True
except ImportError:
    SMBUS_AVAILABLE = False
    print("⚠️  smbus not available (not on Raspberry Pi)")

# ADXL345 Constants
ADXL345_ADDRESS = 0x53
ADXL345_REG_POWER_CTL = 0x2D
ADXL345_REG_DATA_FORMAT = 0x31
ADXL345_REG_DATAX0 = 0x32

class AccelerometerSimulator:
    """Simulates accelerometer for testing without hardware"""

    def __init__(self):
        print("🔬 Running in SIMULATION mode (no hardware)")

    def read_force(self):
        """Return simulated force value"""
        import random
        # Simulate gravity + noise
        return 1.0 + random.uniform(-0.1, 0.1)


class ADXL345Sensor:
    """ADXL345 accelerometer interface"""

    def __init__(self, address=ADXL345_ADDRESS):
        if not SMBUS_AVAILABLE:
            raise ImportError("smbus not available")

        self.bus = smbus.SMBus(1)  # RPi uses bus 1
        self.address = address
        self.initialize()

    def initialize(self):
        """Initialize ADXL345 sensor"""
        # Set to measurement mode
        self.bus.write_byte_data(self.address, ADXL345_REG_POWER_CTL, 0x08)

        # Set data format (±16g range, full resolution)
        self.bus.write_byte_data(self.address, ADXL345_REG_DATA_FORMAT, 0x0B)

        print("✅ ADXL345 initialized")

    def read_raw(self):
        """Read raw accelerometer values"""
        data = self.bus.read_i2c_block_data(self.address, ADXL345_REG_DATAX0, 6)

        # Convert to signed 16-bit values
        x = (data[1] << 8) | data[0]
        y = (data[3] << 8) | data[2]
        z = (data[5] << 8) | data[4]

        # Convert to signed
        if x > 32767:
            x -= 65536
        if y > 32767:
            y -= 65536
        if z > 32767:
            z -= 65536

        return x, y, z

    def read_force(self):
        """
        Calculate force magnitude from accelerometer.

        Returns force in g's (1g = 9.8 m/s²)
        """
        x, y, z = self.read_raw()

        # Convert to g's (ADXL345 scale factor: 4mg per LSB at ±16g)
        x_g = x * 0.004
        y_g = y * 0.004
        z_g = z * 0.004

        # Calculate magnitude
        magnitude = (x_g**2 + y_g**2 + z_g**2) ** 0.5

        # Subtract gravity baseline (typically ~1g when at rest)
        force = abs(magnitude - 1.0)

        return force


def test_sensor(duration=30):
    """
    Test accelerometer sensor for specified duration.

    Args:
        duration: Test duration in seconds
    """
    print("╔════════════════════════════════════════╗")
    print("║  Accelerometer Test                    ║")
    print("╚════════════════════════════════════════╝")
    print("")

    # Initialize sensor
    try:
        sensor = ADXL345Sensor()
    except (ImportError, OSError) as e:
        print(f"⚠️  Could not initialize ADXL345: {e}")
        print("   Using simulator instead...")
        sensor = AccelerometerSimulator()

    print(f"📊 Reading for {duration} seconds...")
    print("   Hit the sensor to see force spikes!")
    print("")
    print("Time    | Force  | Tier | Visual")
    print("--------|--------|------|" + "-" * 20)

    start_time = time.time()
    max_force = 0
    readings = []

    try:
        while time.time() - start_time < duration:
            force = sensor.read_force()
            readings.append(force)
            max_force = max(max_force, force)

            # Categorize into tiers
            if force < 1.0:
                tier = 1
            elif force < 2.0:
                tier = 2
            elif force < 4.0:
                tier = 3
            elif force < 7.0:
                tier = 4
            else:
                tier = 5

            # Visual bar
            bar_length = int(force * 5)
            bar = "█" * min(bar_length, 50)

            elapsed = time.time() - start_time
            print(f"{elapsed:7.1f}s | {force:6.2f} | T{tier}   | {bar}")

            time.sleep(0.1)  # 10Hz sampling

    except KeyboardInterrupt:
        print("\n⏹️  Stopped by user")

    print("")
    print("═" * 50)
    print(f"📈 Statistics:")
    print(f"   Max force: {max_force:.2f}g")
    print(f"   Avg force: {sum(readings) / len(readings):.2f}g")
    print(f"   Samples: {len(readings)}")
    print("")

    # Calibration suggestions
    print("💡 Calibration recommendations:")
    if max_force > 10:
        print("   ✅ Good dynamic range! Your sensor is working well.")
    elif max_force > 5:
        print("   ⚠️  Moderate range. Try hitting harder or check mounting.")
    else:
        print("   ❌ Low force detected. Check:")
        print("      - Is sensor firmly attached to bag?")
        print("      - Is sensor oriented correctly?")
        print("      - Try hitting harder")

    print("")
    print("🎯 Tier thresholds for this sensor:")
    baseline = 1.0
    print(f"   Tier 1 (Weak):   < {baseline * 1.0:.1f}g")
    print(f"   Tier 2 (Light):  {baseline * 1.0:.1f}g - {baseline * 2.0:.1f}g")
    print(f"   Tier 3 (Medium): {baseline * 2.0:.1f}g - {baseline * 4.0:.1f}g")
    print(f"   Tier 4 (Hard):   {baseline * 4.0:.1f}g - {baseline * 7.0:.1f}g")
    print(f"   Tier 5 (Max):    > {baseline * 7.0:.1f}g")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Test accelerometer sensor')
    parser.add_argument('--duration', type=int, default=30, help='Test duration in seconds')
    args = parser.parse_args()

    test_sensor(args.duration)
