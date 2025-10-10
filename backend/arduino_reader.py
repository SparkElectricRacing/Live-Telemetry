import serial # pyserial
import time
import global_vars as gv

# [0] hardcoded sanity assert value (0xbb)
# [1] CAN device id
# [2] Subidentifier (for devices that send more than one type of data per address, i.e. from BMS AUX (0x7D): 0x00 = low cell V, 0x01 = high cell V, etc.)
# [3-6] timestamp, in ms from device enable
# [7-14*] data, big-endian? (i need to double check the endianness but memcpy gives the correct result either way)
# [15*] hardcoded sanity assert value (0x9a)
# So 16 bytes / entry gives us a lot of wiggle room for the amt of data we send over
def avg_temp(data):
    # static_cast<int>(frame->data[1])
    return ((data >> 8) & 0xFF)
def avg_cell_voltage(data):
    # static_cast<double>((frame->data[2] << 8) + (frame->data[3])) / 10000;
    return ((((data >> 16) & 0xFF) << 8) + ((data >> 24) & 0xFF)) / 10000
def pack_voltage(data):
    # static_cast<double>((frame->data[4] << 8) | (frame->data[5])) / 100;
    return ((((data >> 32) & 0xFF) << 8) | ((data >> 40) & 0xFF)) / 100
def pack_SOC(data):
    # static_cast<double>((frame->data[6] << 8) | (frame->data[7])) / 20;
    return ((((data >> 48) & 0xFF) << 8) | ((data >> 56) & 0xFF)) / 20
def is_charging(data):
    # frame->data[0] == 1
    return ((data) & 0xFF) == 1
def low_cell_voltage(data):
    # static_cast<double>((frame->data[0] << 8) + (frame->data[1])) / 10000;
    return (((data & 0xFF) << 8) + ((data >> 8) & 0xFF)) / 100000
def high_cell_voltage(data):
    # static_cast<double>((frame->data[2] << 8) + (frame->data[3])) / 10000;
    return ((((data >> 16) & 0xFF) << 8) + ((data >> 24) & 0xFF)) / 10000 
def max_cell_temp(data):
    # static_cast<int>(frame->data[4]);
    return (data >> 32) & 0xFF
def dtc1(data):
    # static_cast<int>((frame->data[6] << 8) | (frame->data[7]));
    return (((data >> 48) & 0xFF) << 8) | ((data >> 56) & 0xFF)
def raw_rpm(data):
    # uint16_t raw_rpm = frame->data[2] | (frame->data[3] << 8);
    return (((data >> 16) & 0xFF) << 8) | (((data >> 24) & 0xFF))

# For Getting rpm_speed and mph_speed

def rpm_speed(raw_rpm):
    # int16_t rpmSpeed = -1 * static_cast<int16_t>(raw_rpm); // masking off the sign bit
    return -1*raw_rpm
def mph_speed(rpm_speed): # Adapted from the google docs
    FRONT_SPROCKET_TEETH = 16.0
    REAR_SPROCKET_TEETH = 50.0 # Talon TR371 50 520 Sprocket
    WHEEL_DIAMETER_INCHES = 25.7 #Wheel Diameter is 17", with tire ~26"
    PI = 3.14159265358979323846
    INCHES_TO_MILES = 1.0 / 63360.0
    MINUTES_PER_HOUR = 60.0
    # Gear reduction ratio
    gearRatio = FRONT_SPROCKET_TEETH / REAR_SPROCKET_TEETH
    # Rear wheel RPM
    wheelRPM = rpm_speed * gearRatio
    # Wheel circumference in miles
    wheelCircumferenceMiles = PI * WHEEL_DIAMETER_INCHES * INCHES_TO_MILES
    # Speed = wheel RPM * circumference * 60 (minutes to hours)
    speedMPH = wheelRPM * wheelCircumferenceMiles * MINUTES_PER_HOUR
    return speedMPH

SIGNALS = {
        (0x7C, 0): "avg_temp",
        (0x7C, 1): "avg_cell_voltage",
        (0x7C, 2): "pack_voltage",
        (0x7C, 3): "pack_SOC",
        (0x7C, 4): "is_charging",
        (0x7D, 0): "low_cell_voltage",
        (0x7D, 1): "high_cell_voltage",
        (0x7D, 2): "max_cell_temp",
        (0x7D, 3): "DTC1",
        (0xA5, 0): "raw_rpm",
    }

CONVERSIONS = {
    "avg_temp": avg_temp,
    "avg_cell_voltage": avg_cell_voltage,
    "pack_voltage": pack_voltage,
    "pack_SOC": pack_SOC,
    "is_charging": is_charging,
    "low_cell_voltage": low_cell_voltage,
    "high_cell_voltage": high_cell_voltage,
    "max_cell_temp": max_cell_temp,
    "DTC1": dtc1,
    "raw_rpm": raw_rpm
}

def parse_in(inp):
    inp = int.from_bytes(inp, byteorder='big') # quicker
    # if type(inp) == bytes:
    #     inp = ''.join(f'{byte:08b}' for byte in inp)
    # if type(inp) == str:
    #     inp = int(inp, 2)
    if type(inp) == int or type(inp) == float:
        # inp = inp & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF # 16 byte to ensure only dealing with 16 bytes
        hcSanValB = inp & 0xFF 
        data = (inp >> 8) & 0xFFFFFFFFFFFFFFFF # 8 byte
        timestamp = (inp >> 72) & 0xFFFFFFFF # 4 byte
        subId = (inp >> 104) & 0xFF
        canId = (inp >> 112) & 0xFF
        hcSanValA = (inp >> 120) & 0xFF
        signal_name = SIGNALS.get((canId, subId), "")
        try:
            result = CONVERSIONS[signal_name](data)
        except Exception as e:
            result = f"Decode error: {e}"
        return hcSanValA, signal_name, timestamp, result, hcSanValB
    else: 
        print(type(inp))
        return 0, "", 0, 0, 0

def read_from_arduino(port_name, baud_rate):
    ser = serial.Serial(port_name, baud_rate, timeout = 1)
    time.sleep(2)
    try:
        while True:
            while ser.in_waiting > 16:
                line = ser.readline().decode('utf-8').rstrip()
                hcSanValA, signal_name, timestamp, data, hcSanValB = parse_in(line)
                if signal_name == "raw_rpm":
                    rpmSpeed = rpm_speed(data)
                    entry = [hcSanValA, "rpm_speed", timestamp, rpmSpeed, hcSanValB]
                    gv.buffer.put(entry)
                    speedMPH = mph_speed(rpmSpeed)
                    entry = [hcSanValA, "speedMPH", timestamp, speedMPH, hcSanValB]
                    gv.buffer.put(entry)
                else:
                    entry = [hcSanValA, signal_name, timestamp, data, hcSanValB]
                    gv.buffer.put(entry)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Exiting...")
        ser.close()


port_name = "/dev/ttyUSB0"
baud_rate = 115200
if __name__ == "__main__":
    while True:
        read_from_arduino()