from fastapi import FastAPI
from . import global_vars as gv
from .arduino_reader import read_from_arduino
import threading
from queue import Empty

app = FastAPI()

#master switch for switching between a test file and real arduino
TEST_MODE = True #SET THIS FALSE WHEN TESTING WITH REAL ARDUINO
if(TEST_MODE):
    port_name = "not_a_port"
else:
    port_name = "/dev/ttyUSB0"
baud_rate = 115200

##runs read_from_arduino on a separate thread so it can share memory with dash
@app.on_event("startup")
async def startup_event():
    print("starting background thread")
    thread = threading.Thread(
        target=read_from_arduino, 
        args=(port_name, baud_rate), 
        daemon=True
    )
    thread.start()


SIGNAL_TYPES = {
    "avg_temp": { "Time" : int, "Data": int, "GPS": (int, int)},
    "avg_cell_voltage": { "Time" : int, "Data": float, "GPS": (int, int)},
    "pack_voltage": { "Time" : int, "Data": float, "GPS": (int, int)},
    "pack_SOC": { "Time" : int, "Data": float, "GPS": (int, int)},
    "is_charging": { "Time" : int, "Data": bool, "GPS": (int, int)},
    "low_cell_voltage": { "Time" : int, "Data": float, "GPS": (int, int)},
    "high_cell_voltage": { "Time" : int, "Data": float, "GPS": (int, int)},
    "max_cell_temp": { "Time" : int, "Data": int, "GPS": (int, int)},
    "DTC1": { "Time" : int, "Data": int, "GPS": (int, int)},
    # "raw_rpm": { "Time" : int, "Data": float, "GPS": (int, int)},
    "speedMPH": { "Time" : int, "Data": float, "GPS": (int, int)},
    "rpm_speed": { "Time" : int, "Data": float, "GPS": (int, int)}
}

@app.get("/data/receive")
async def read_root():
    size = gv.buffer.qsize()
    
    # Inputs
    # hcSanValA, signal_name, timestamp, data, hcSanValB
    # hardcoded sanity assert value (0xbb)
    # signal_name - made in file_parser.py
    # timestamp, in ms from device enable
    # data, big-endian? (i need to double check the endianness but memcpy gives the correct result either way)
    # hardcoded sanity assert value (0x9a)
    
    # Output Format
    # {"RPM": {"Time":[...], "Data":[...]}, "Voltage": {"Time":[...], "Data":[...]}, ...}
    
    # Criteria:
    # Make sure sanity assert values are valid
    # Make sure signal name is valid - currently omitting any bad signal names or incorrect sanity bits from json
    
    signals = { name: { "Time": [], "Data": [] , "GPS": []} for name in SIGNAL_TYPES }
    
    rows = []
    for _ in range(size):
        try:
            rows.append(gv.buffer.get()) # get_nowait() if wanted to attempt use later see if good
        except Empty:
            break
        
    for row in rows:
        if row[0] == 0xBB and row[6] == 0x9A: # Will not receive data that does not have correct sanity bytes
            if row[1] in signals:
                type_info = SIGNAL_TYPES[row[1]]
                signals[row[1]]["Time"].append(type_info["Time"](row[2]))
                signals[row[1]]["Data"].append(type_info["Data"](row[3]))
                signals[row[1]]["GPS"].append((row[4], row[5]))
                # signals[row[1]].append({
                #     "Time": type_info["Time"](row[2]),
                #     "Data": type_info["Data"](row[3])
                # })
    return signals

