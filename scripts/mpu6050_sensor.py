#!/usr/bin/env python3
"""
MPU-6050 (GY-521 module) accelerometer interface

The GY-521 module includes:
- MPU-6050 6-axis gyroscope + accelerometer
- I2C interface
- 3.3V-5V compatible (has onboard voltage regulator)
"""

import time
import sys

try:
    import smbus
    SMBUS_AVAILABLE = True
except ImportError:
    SMBUS_AVAILABLE = False
    print("⚠️  smbus not available")

# MPU-6050 Constants
MPU6050_ADDRESS = 0x68  # Default I2C address
MPU6050_REG_PWR_MGMT_1 = 0x6B
MPU6050_REG_ACCEL_CONFIG = 0x1C
MPU6050_REG_ACCEL_XOUT_H = 0x3B

class MPU6050Sensor:
    """
    MPU-6050 6-axis IMU interface (GY-521 module)

    Wiring:
        GY-521    →    Raspberry Pi
        VCC       →    Pin 2 (5V) or Pin 1 (3.3V)
        GND       →    Pin 6 (GND)
        SDA       →    Pin 3 (GPIO 2)
        SCL       →    Pin 5 (GPIO 3)
    """

    def __init__(self, address=MPU6050_ADDRESS, bus=1):
        if not SMBUS_AVAILABLE:
            raise ImportError("smbus not available")

        self.bus = smbus.SMBus(bus)
        self.address = address
        self.initialize()

    def initialize(self):
        """Initialize MPU-6050 sensor"""
        # Wake up MPU-6050 (default is sleep mode)
        self.bus.write_byte_data(self.address, MPU6050_REG_PWR_MGMT_1, 0x00)
        time.sleep(0.1)

        # Set accelerometer range to ±16g (0x03)
        # 0x00 = ±2g, 0x01 = ±4g, 0x02 = ±8g, 0x03 = ±16g
        self.bus.write_byte_data(self.address, MPU6050_REG_ACCEL_CONFIG, 0x03 << 3)

        print("✅ MPU-6050 initialized (±16g range)")

    def read_raw_accel(self):
        """
        Read raw accelerometer values from MPU-6050

        Returns:
            tuple: (x, y, z) raw values
        """
        # Read 6 bytes starting from ACCEL_XOUT_H
        data = self.bus.read_i2c_block_data(
            self.address,
            MPU6050_REG_ACCEL_XOUT_H,
            6
        )

        # Combine high and low bytes
        x = (data[0] << 8) | data[1]
        y = (data[2] << 8) | data[3]
        z = (data[4] << 8) | data[5]

        # Convert to signed 16-bit
        if x > 32767:
            x -= 65536
        if y > 32767:
            y -= 65536
        if z > 32767:
            z -= 65536

        return x, y, z

    def read_accel_g(self):
        """
        Read accelerometer values in g's

        Returns:
            tuple: (x, y, z) in g's
        """
        x, y, z = self.read_raw_accel()

        # MPU-6050 scale factor at ±16g: 2048 LSB/g
        scale_factor = 2048.0

        x_g = x / scale_factor
        y_g = y / scale_factor
        z_g = z / scale_factor

        return x_g, y_g, z_g

    def read_force(self):
        """
        Calculate force magnitude from accelerometer

        Returns:
            float: Force in g's (0+ range, gravity removed)
        """
        x_g, y_g, z_g = self.read_accel_g()

        # Calculate total magnitude
        magnitude = (x_g**2 + y_g**2 + z_g**2) ** 0.5

        # Remove gravity baseline (~1g when at rest)
        # The magnitude at rest should be ~1g due to gravity
        force = abs(magnitude - 1.0)

        return force

    def calibrate(self, samples=100):
        """
        Calibrate sensor by measuring baseline at rest

        Returns:
            float: Average magnitude at rest
        """
        print(f"📊 Calibrating... Keep sensor still! ({samples} samples)")

        magnitudes = []
        for i in range(samples):
            x_g, y_g, z_g = self.read_accel_g()
            magnitude = (x_g**2 + y_g**2 + z_g**2) ** 0.5
            magnitudes.append(magnitude)
            time.sleep(0.01)

        baseline = sum(magnitudes) / len(magnitudes)
        print(f"✅ Baseline: {baseline:.3f}g")

        return baseline


def test_sensor(duration=30):
    """Test MPU-6050 sensor"""
    print("╔════════════════════════════════════════╗")
    print("║  MPU-6050 (GY-521) Test                ║")
    print("╚════════════════════════════════════════╝")
    print("")

    try:
        sensor = MPU6050Sensor()
    except (ImportError, OSError) as e:
        print(f"❌ Error: {e}")
        print("")
        print("Troubleshooting:")
        print("  1. Check wiring:")
        print("     VCC → 3.3V or 5V")
        print("     GND → GND")
        print("     SDA → GPIO 2 (Pin 3)")
        print("     SCL → GPIO 3 (Pin 5)")
        print("")
        print("  2. Enable I2C:")
        print("     sudo raspi-config → Interface → I2C → Enable")
        print("")
        print("  3. Detect sensor:")
        print("     i2cdetect -y 1")
        print("     Should show 0x68")
        return

    # Calibrate
    baseline = sensor.calibrate()
    print("")

    print(f"📊 Reading for {duration} seconds...")
    print("   Hit the sensor to see force spikes!")
    print("")
    print("Time    | Force  | Tier | Visual")
    print("--------|--------|------|" + "-" * 30)

    start_time = time.time()
    max_force = 0
    readings = []

    try:
        while time.time() - start_time < duration:
            force = sensor.read_force()
            readings.append(force)
            max_force = max(max_force, force)

            # Calculate tier (same as punch_handler.py)
            force_pct = force * 100  # Rough percentage
            if force_pct < 20:
                tier = 1
            elif force_pct < 40:
                tier = 2
            elif force_pct < 60:
                tier = 3
            elif force_pct < 85:
                tier = 4
            else:
                tier = 5

            # Visual bar
            bar_length = int(force * 5)
            bar = "█" * min(bar_length, 50)

            elapsed = time.time() - start_time
            print(f"{elapsed:7.1f}s | {force:6.2f} | T{tier}   | {bar}")

            time.sleep(0.1)  # 10Hz

    except KeyboardInterrupt:
        print("\n⏹️  Stopped")

    print("")
    print("═" * 60)
    print(f"📈 Statistics:")
    print(f"   Max force: {max_force:.2f}g")
    print(f"   Avg force: {sum(readings) / len(readings):.2f}g")
    print(f"   Samples: {len(readings)}")
    print("")

    # Recommendations
    if max_force > 10:
        print("✅ Excellent! Your sensor has great dynamic range.")
    elif max_force > 5:
        print("⚠️  Moderate range. Try hitting harder or check mounting.")
    else:
        print("❌ Low force detected. Check:")
        print("   - Sensor firmly attached?")
        print("   - Correct orientation?")
        print("   - Try hitting harder")

    print("")
    print("🎯 Recommended tier thresholds:")
    print(f"   Tier 1 (Weak):   < 2.0g")
    print(f"   Tier 2 (Light):  2.0g - 4.0g")
    print(f"   Tier 3 (Medium): 4.0g - 7.0g")
    print(f"   Tier 4 (Hard):   7.0g - 12.0g")
    print(f"   Tier 5 (Max):    > 12.0g")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Test MPU-6050 sensor')
    parser.add_argument('--duration', type=int, default=30,
                       help='Test duration in seconds')
    args = parser.parse_args()

    test_sensor(args.duration)
