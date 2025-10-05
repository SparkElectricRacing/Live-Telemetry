from fastapi import FastAPI
from backend import global_vars as gv
from queue import Empty

app = FastAPI()

SIGNAL_TYPES = {
    "avg_temp": { "Time" : int, "Data": int},
    "avg_cell_voltage": { "Time" : int, "Data": float},
    "pack_voltage": { "Time" : int, "Data": float},
    "pack_SOC": { "Time" : int, "Data": float},
    "is_charging": { "Time" : int, "Data": bool},
    "low_cell_voltage": { "Time" : int, "Data": float},
    "high_cell_voltage": { "Time" : int, "Data": float},
    "max_cell_temp": { "Time" : int, "Data": int},
    "DTC1": { "Time" : int, "Data": int},
    # "raw_rpm": { "Time" : int, "Data": float},
    "speedMPH": { "Time" : int, "Data": float},
    "rpm_speed": { "Time" : int, "Data": float}
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
    
    signals = { name: { "Time": [], "Data": [] } for name in SIGNAL_TYPES }
    
    rows = []
    for _ in range(size):
        try:
            rows.append(gv.buffer.get()) # get_nowait() if wanted to attempt use later see if good
        except Empty:
            break
        
    for row in rows:
        if row[0] == 0xBB & row[4] == 0x9A: # Will not receive data that does not have correct sanity bytes
            if row[1] in signals:
                type_info = SIGNAL_TYPES[row[1]]
                signals[row[1]]["Time"].append(type_info["Time"](row[2]))
                signals[row[1]]["Data"].append(type_info["Data"](row[3]))
                # signals[row[1]].append({
                #     "Time": type_info["Time"](row[2]),
                #     "Data": type_info["Data"](row[3])
                # })
    return signals