from fastapi import FastAPI
from backend import global_vars as gv

app = FastAPI()

@app.get("/data/recieve")
def read_root():
    size = gv.buffer.qsize()
    
    # hcSanValA, canId, subId, timestamp, data, hcSanValB
    
    # hardcoded sanity assert value (0xbb)
    # CAN device id
    # Subidentifier (for devices that send more than one type of data per address, i.e. from BMS AUX (0x7D): 0x00 = low cell V, 0x01 = high cell V, etc.)
    # timestamp, in ms from device enable
    # data, big-endian? (i need to double check the endianness but memcpy gives the correct result either way)
    # hardcoded sanity assert value (0x9a)
    
    # Change to be this
    # {"RPM": {"Time":[...], "Data":[...]}, "Voltage": {"Time":[...], "Data":[...]}, ...}
    

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