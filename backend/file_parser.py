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
        return hcSanValA, signal_name, timestamp, data, hcSanValB
    else: 
        print(type(inp))
        return 0, "", 0, 0, 0

def read_bin_file(file):
    # look at changing logic to include := walrus operator while loop with conditional to verify 16 bytes acc taken
    with open(file, 'rb') as f:
        while True:
            line = f.read(16)
            if not line:
                print("EOF")
                break
            hcSanValA, signal_name, timestamp, data, hcSanValB = parse_in(line)
            print(hcSanValA, signal_name, timestamp, data, hcSanValB)
    return

def read_from_arduino(port_name, baud_rate):
    with serial.Serial(port_name, baud_rate, timeout = 1) as ser:
        while True:
            line = ser.readline() # need to now check for not line
            if not line:
                print("waiting on line - empty")
                continue
            try:
                hcSanValA, signal_name, timestamp, data, hcSanValB = parse_in(line)
                print(hcSanValA, signal_name, timestamp, data, hcSanValB)
            except Exception as e:
                print("Bad line")
                continue
    return

def read_from_arduino_v2(port_name, baud_rate):
    ser = serial.Serial(port_name, baud_rate, timeout = 1)
    time.sleep(2)
    while True:
        while ser.in_waiting > 16:
            line = ser.readline().decode('utf-8').rstrip()
            hcSanValA, signal_name, timestamp, data, hcSanValB = parse_in(line)
            entry = [hcSanValA, signal_name, timestamp, data, hcSanValB]
            gv.buffer.put(entry)
        time.sleep(0.1)
    # Add error checks for port etc

def read_from_arduino_v3(port_name, baud_rate):
    ser = serial.Serial(port_name, baud_rate, timeout = 1)
    time.sleep(2)
    try:
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').rstrip()
                print(line)
    except KeyboardInterrupt:
        print("Exiting...")
        ser.close()

# def __main__():

read_bin_file("output.bin")

port_name = "/dev/ttyUSB0"
baud_rate = 115200