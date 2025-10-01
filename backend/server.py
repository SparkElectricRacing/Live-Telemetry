from fastapi import FastAPI
from backend import global_vars as gv

app = FastAPI()

@app.get("/data/recieve")
def read_root():
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

    for _ in range(size):
        signals = {
            "avg_temp": [],
            "avg_cell_voltage": [],
            "pack_voltage": [],
            "pack_SOC": [],
            "is_charging": [],
            "low_cell_voltage": [],
            "high_cell_voltage": [],
            "max_cell_temp": [],
            "DTC1": [],
            "raw_rpm": []
        }
        row = gv.buffer.get()
        if row[0] == 0xBB & row[4] == 0x9A: # Will not receive data that does not have correct sanity bytes
            row_object = {
                "TIMESTAMP": row[2],
                "DATA": row[3]
            }
            if row[1] in signals:
                signals[row[1]].append(row_object)
    return signals