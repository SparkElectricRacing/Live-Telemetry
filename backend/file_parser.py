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

def parse_in(inp):
    if type(inp) == bytes:
        inp = ''.join(f'{byte:08b}' for byte in inp)
        # print(inp)
    if type(inp) == str:
        inp = int(inp, 2)
    if type(inp) == int or type(inp) == float:
        # inp = inp - ((inp >> 112) << 112)
        # p = inp & 1 # right then left shift
        # data = (inp - ((inp >> 65) << 65) - p) >> 1
        # time = (inp - ((inp >> 97) << 97) - p - (data << 1)) >> 65
        # typ = (inp - ((inp >> 100) << 100) - p - (data << 1) - (time << 65)) >> 97
        # dev_addr = (inp - p - (data << 1) - (time << 65) - (typ << 97)) >> 100
        inp = inp - ((inp >> 128) << 128)
        hcSanValB = inp & 0xFF 
        data = (inp - ((inp >> 72) << 72) - hcSanValB) >> 8
        timestamp = (inp - ((inp >> 104) << 104) - hcSanValB - (data << 8)) >> 72
        subId = (inp - ((inp >> 112) << 112) - hcSanValB - (data << 8) - (timestamp << 72)) >> 104
        canId = (inp - ((inp >> 120) << 120) - hcSanValB - (data << 8) - (timestamp << 72) - (subId << 104)) >> 112
        hcSanValA = inp >> 120
    else: 
        print(type(inp))
        
    
    return hcSanValA, canId, subId, timestamp, data, hcSanValB
    
# dev_addr, typ, time, data, p = parse_in("0000000000000000000001000000000001001000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000001")
# print(dev_addr)
# print(typ)
# print(time)
# print(data)
# print(p)

def read_bin_file(file):
    with open(file, 'rb') as f:
        while True:
            line = f.read(16)
            if not line:
                print("EOF")
                break
            hcSanValA, canId, subId, timestamp, data, hcSanValB = parse_in(line)
            print(hcSanValA, canId, subId, timestamp, data, hcSanValB)
            # row = [hcSanValA, canId, subId, timestamp, data, hcSanValB]
    return

def read_from_arduino(port_name, baud_rate):
    with serial.Serial(port_name, baud_rate, timeout = 1) as ser:
        while True:
            line = ser.readline() # need to now check for not line
            if not line:
                print("waiting on line - empty")
                continue
            try:
                hcSanValA, canId, subId, timestamp, data, hcSanValB = parse_in(line)
                print(hcSanValA, canId, subId, timestamp, data, hcSanValB)
            except Exception as e:
                print("Bad line")
                continue
    return

def read_from_arduino_v2(port_name, baud_rate):
    ser = serial.Serial(port_name, baud_rate, timeout = 1)
    time.sleep(2)
    while True:
        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').rstrip()
            hcSanValA, canId, subId, timestamp, data, hcSanValB = parse_in(line)
            entry = [hcSanValA, canId, subId, timestamp, data, hcSanValB]
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