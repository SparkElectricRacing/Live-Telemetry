import serial # pyserial
import time
import global_vars as gv

def parse_in(inp):
    if type(inp) == bytes:
        inp = ''.join(f'{byte:08b}' for byte in inp)
    if type(inp) == str:
        inp = int(inp, 2)
    if type(inp) == int or type(inp) == float:
        inp = inp - ((inp >> 112) << 112)
        p = inp & 1 # right then left shift
        data = (inp - ((inp >> 65) << 65) - p) >> 1
        time = (inp - ((inp >> 97) << 97) - p - (data << 1)) >> 65
        typ = (inp - ((inp >> 100) << 100) - p - (data << 1) - (time << 65)) >> 97
        dev_addr = (inp - p - (data << 1) - (time << 65) - (typ << 97)) >> 100
    else: 
        print(type(inp))
        
    
    return dev_addr, typ, time, data, p
    
# dev_addr, typ, time, data, p = parse_in("0000000000000000000001000000000001001000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000001")
# print(dev_addr)
# print(typ)
# print(time)
# print(data)
# print(p)

def read_bin_file(file):
    data
    with open(file, 'rb') as f:
        for line in f:
            dev_addr, typ, time, data, p = parse_in(line)
            print(dev_addr, typ, time, data, p)
            row = [dev_addr, typ, time, data, p]
    return

def read_from_arduino(port_name, baud_rate):
    with serial.Serial(port_name, baud_rate, timeout = 1) as ser:
        while True:
            line = ser.readline() # need to now check for not line
            if not line:
                print("waiting on line - empty")
                continue
            try:
                dev_addr, typ, time, data, p = parse_in(line)
                print(dev_addr, typ, time, data, p)
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
            dev_addr, typ, time, data, p = parse_in(line)
            entry = [dev_addr, typ, time, data, p]
            gv.buffer.put(entry)
        time.sleep(0.1)
    # Add error checks for port etc

# def __main__():

read_bin_file("output.bin")