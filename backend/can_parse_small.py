#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parse candump lines into the exact JSON you want:
{
  "timestamp", "speedMPH", "rpm_speed",
  "pack_voltage", "pack_SOC",
  "avg_temp", "avg_cell_voltage", "low_cell_voltage", "high_cell_voltage", "max_cell_temp",
  "is_charging", "DTC1"
}

Usage:
  python3 can_parse_small.py candump.log > minimal.jsonl
"""

import sys, re, json, datetime
from collections import defaultdict, deque

# ---- Optionally set these to compute speedMPH from motor rpm
GEAR_RATIO = 3.125         # 16:50 GEAR RATIO
TIRE_CIRCUMFERENCE_M = 2.057  #  circumference in m 

LINE_RE = re.compile(r"\((?P<ts>\d+\.\d+)\)\s+\S+\s+(?P<id>[0-9A-Fa-f]+)#(?P<data>[0-9A-Fa-f]{2,16})")

def iso8601_from_epoch(epoch):
    return datetime.datetime.utcfromtimestamp(epoch).isoformat()

# ---- Byte helpers
def be_u16(b): return (b[0] << 8) | b[1]
def be_s16(b):
    v = be_u16(b)
    return v - 0x10000 if v & 0x8000 else v
def le_u16(b): return (b[1] << 8) | b[0]
def le_s16(b):
    v = le_u16(b)
    return v - 0x10000 if v & 0x8000 else v
def u8(b): return b[0]

# ---- IDs we care about
ID_INV_POS   = 0x0A5  # rpm
ID_INV_CURR  = 0x0A6  # dc bus current
ID_INV_VOLT  = 0x0A7  # dc bus voltage
ID_BMS_A     = 0x6B0  # inst voltage, coarse soc
ID_BMS_B     = 0x6B1  # temps (high/low), limits
ID_BMS_AGG   = 0x7C   # avg temp, avg cell V, pack sum V, fine SOC, flags
ID_BMS_EXT   = 0x7D   # low/high cell V, max cell temp
ID_JB        = 0xE0   # junction box flags

MERGE_WINDOW_S = 0.20

def decode(can_id, data):
    out = {}
    # Inverter
    if can_id == ID_INV_POS and len(data) >= 8:
        out["rpm_speed"] = le_s16(data[2:4]) * 1.0  # INV_Motor_Speed
    elif can_id == ID_INV_CURR and len(data) >= 8:
        out["inv_dc_bus_current_A"] = le_s16(data[6:8]) * 0.1
    elif can_id == ID_INV_VOLT and len(data) >= 2:
        out["pack_voltage_inv"] = le_s16(data[0:2]) * 0.1  # as fallback

    # BMS core
    elif can_id == ID_BMS_A and len(data) >= 6:
        out["pack_voltage_bms_inst"] = be_u16(data[2:4]) * 0.1
        out["pack_soc_coarse"] = u8(data[4:5]) * 0.5
    elif can_id == ID_BMS_B and len(data) >= 6:
        out["bms_high_temp_C"] = u8(data[4:5]) * 1.0
    elif can_id == ID_BMS_AGG and len(data) >= 8:
        b0 = u8(data[0:1])
        out["charge_power_signal"] = 1 if (b0 & (1<<0)) else 0
        out["charge_enable_inverted"] = 1 if (b0 & (1<<1)) else 0
        out["avg_temp"] = u8(data[1:2]) * 1.0
        out["avg_cell_voltage"] = be_u16(data[2:4]) * 1e-4
        out["pack_voltage_bms_sum"] = be_u16(data[4:6]) * 0.01
        out["pack_SOC"] = be_u16(data[6:8]) * 0.05
    elif can_id == ID_BMS_EXT and len(data) >= 5:
        out["low_cell_voltage"] = be_u16(data[0:2]) * 1e-4
        out["high_cell_voltage"] = be_u16(data[2:4]) * 1e-4
        out["max_cell_temp"] = u8(data[4:5]) * 1.0

    # JB flags
    elif can_id == ID_JB and len(data) >= 4:
        b2 = u8(data[2:3])
        b3 = u8(data[3:4])
        out.update({
            "jb_LS_chrg_EN":   1 if (b2 & (1<<5)) else 0,
            "jb_HS_chrg_EN":   1 if (b2 & (1<<6)) else 0,
            "jb_chrg_pre_EN":  1 if (b2 & (1<<4)) else 0,
            "ISO_FAULT":       1 if (b3 & (1<<1)) else 0,
            "BMS_FAULT":       1 if (b3 & (1<<2)) else 0,
            "INV_FAULT":       1 if (b3 & (1<<3)) else 0,
        })
    return out

def compute_speed_mph(rpm):
    if rpm is None or GEAR_RATIO is None or TIRE_CIRCUMFERENCE_M is None or GEAR_RATIO == 0:
        return None
    rpm = abs(rpm)
    wheel_rps = (rpm / GEAR_RATIO) / 60.0
    mps = wheel_rps * TIRE_CIRCUMFERENCE_M
    mph = mps * 2.2369362920544
    return mph

def build_row(epoch_ts, vals):
    rpm = vals.get("rpm_speed")
    speed_mph = compute_speed_mph(rpm)

    # choose best voltage and SOC sources
    pack_voltage = vals.get("pack_voltage_bms_sum") \
                   or vals.get("pack_voltage_bms_inst") \
                   or vals.get("pack_voltage_inv")
    pack_soc = vals.get("pack_SOC") or vals.get("pack_soc_coarse")
    avg_temp = vals.get("avg_temp")
    avg_cell_voltage = vals.get("avg_cell_voltage")
    low_cell_voltage = vals.get("low_cell_voltage")
    high_cell_voltage = vals.get("high_cell_voltage")
    max_cell_temp = vals.get("max_cell_temp") or vals.get("bms_high_temp_C")

    # is_charging (flags OR current sign)
    is_chg = False
    if vals.get("charge_power_signal"): is_chg = True
    if vals.get("jb_LS_chrg_EN") or vals.get("jb_HS_chrg_EN") or vals.get("jb_chrg_pre_EN"):
        is_chg = True
    if "inv_dc_bus_current_A" in vals:
        # NOTE: polarity may differ on your system; flip if needed.
        if vals["inv_dc_bus_current_A"] < 0:
            is_chg = True

    # very simple DTC pack: combine some JB faults
    dtc = 0
    if vals.get("ISO_FAULT"): dtc |= (1<<2)
    if vals.get("BMS_FAULT"): dtc |= (1<<1)
    if vals.get("INV_FAULT"): dtc |= (1<<0)

    return {
        "timestamp": iso8601_from_epoch(epoch_ts),
        "vehicle_speed": speed_mph,  # Frontend expects vehicle_speed
        "speedMPH": speed_mph,  # Keep for backward compatibility
        "rpm_speed": rpm,
        "battery_voltage": pack_voltage,  # Frontend expects battery_voltage
        "pack_voltage": pack_voltage,  # Keep for backward compatibility
        "battery_soc": pack_soc,  # Frontend expects battery_soc
        "pack_SOC": pack_soc,  # Keep for backward compatibility
        "avg_temp": avg_temp,
        "avg_cell_voltage": avg_cell_voltage,
        "low_cell_voltage": low_cell_voltage,
        "high_cell_voltage": high_cell_voltage,
        "max_cell_temp": max_cell_temp,
        "is_charging": bool(is_chg),
        "DTC1": dtc,
    }

def main():
    fp = open(sys.argv[1], "r") if len(sys.argv) > 1 else sys.stdin
    MERGE_WINDOW_S = 0.20
    buckets = defaultdict(lambda: {"vals": {}, "start_ts": None})
    order = deque()

    for line in fp:
        m = LINE_RE.search(line)
        if not m: continue
        ts = float(m.group("ts"))
        can_id = int(m.group("id"), 16)
        data = bytes.fromhex(m.group("data"))

        key = round(ts / MERGE_WINDOW_S) * MERGE_WINDOW_S
        b = buckets[key]
        if b["start_ts"] is None:
            b["start_ts"] = ts
            order.append(key)

        b["vals"].update(decode(can_id, data))

        # Emit a row each time we absorb something (streamy, low-latency)
        row = build_row(b["start_ts"], b["vals"])
        print(json.dumps(row, separators=(",", ":")))

        # Expire old buckets
        while order and (ts - (order[0] or 0)) > (MERGE_WINDOW_S * 2):
            old = order.popleft()
            buckets.pop(old, None)

    if fp is not sys.stdin:
        fp.close()

if __name__ == "__main__":
    main()
