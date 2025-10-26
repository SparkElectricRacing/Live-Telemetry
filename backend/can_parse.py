#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parse candump lines and decode signals from the provided DBC fragments:
- Inverter: 0x0A5 (M165), 0x0A6 (M166), 0x0A7 (M167), plus others if seen
- BMS: 0x6B0, 0x6B1, 0x7C, 0x7D, 0x202, 0x1806E5F4 (extended)
- JB:  0x00E0 (JBStats)

Usage:
  python3 can_parse.py candump.log > all_decoded.jsonl
  # or:
  candump can0 | python3 can_parse.py > all_decoded.jsonl
"""
import sys, re, json, datetime
from collections import defaultdict, deque

LINE_RE = re.compile(r"\((?P<ts>\d+\.\d+)\)\s+\S+\s+(?P<id>[0-9A-Fa-f]+)#(?P<data>[0-9A-Fa-f]{2,16})")

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
def s8(b): return b[0]-256 if b[0] & 0x80 else b[0]
def be_u32(b): return (b[0]<<24)|(b[1]<<16)|(b[2]<<8)|b[3]
def be_s32(b):
    v = be_u32(b)
    return v - 0x100000000 if v & 0x80000000 else v

def iso8601_from_epoch(epoch):
    return datetime.datetime.utcfromtimestamp(epoch).isoformat()

# ---- Signals mapping (offset, length, func, scale, offset, name)
SIGNAL_MAP = {
    # Inverter — M165 (0x0A5)
    0x0A5: [
        (0, 2, le_u16, 0.1, 0.0, "inv_motor_angle_deg"),
        (2, 2, le_s16, 1.0,  0.0, "inv_motor_speed_rpm"),
        (4, 2, le_s16, 0.1, 0.0, "inv_elec_freq_hz"),
        (6, 2, le_s16, 0.1, 0.0, "inv_delta_resolver_deg"),
    ],
    # Inverter — M166 (0x0A6)
    0x0A6: [
        (0, 2, le_s16, 0.1, 0.0, "inv_phase_a_current_A"),
        (2, 2, le_s16, 0.1, 0.0, "inv_phase_b_current_A"),
        (4, 2, le_s16, 0.1, 0.0, "inv_phase_c_current_A"),
        (6, 2, le_s16, 0.1, 0.0, "inv_dc_bus_current_A"),
    ],
    # Inverter — M167 (0x0A7)
    0x0A7: [
        (0, 2, le_s16, 0.1, 0.0, "inv_dc_bus_voltage_V"),
        (2, 2, le_s16, 0.1, 0.0, "inv_output_voltage_V"),
        (4, 2, le_s16, 0.1, 0.0, "inv_vab_vd_voltage_V"),
        (6, 2, le_s16, 0.1, 0.0, "inv_vbc_vq_voltage_V"),
    ],

    # BMS — 0x6B0 (big-endian)
    0x6B0: [
        (0, 2, be_u16, 0.1,  0.0, "bms_pack_current_A"),
        (2, 2, be_u16, 0.1,  0.0, "bms_pack_inst_voltage_V"),
        (4, 1, u8,     0.5,  0.0, "bms_soc_percent_coarse"),
        (5, 2, be_u16, 1.0,  0.0, "bms_relay_state_word"),
    ],
    # BMS — 0x6B1 (big-endian)
    0x6B1: [
        (0, 2, be_u16, 1.0, 0.0, "bms_pack_dcl_A"),
        (2, 1, u8,     1.0, 0.0, "bms_pack_ccl_A"),
        (4, 1, u8,     1.0, 0.0, "bms_high_temp_C"),
        (5, 1, u8,     1.0, 0.0, "bms_low_temp_C"),
    ],
    # BMS — 0x7C
    0x7C: [
        (0, 1, u8,     1.0,  0.0, "bms_flags_b0"),           # bit flags
        (1, 1, u8,     1.0,  0.0, "bms_avg_temp_C"),
        (2, 2, be_u16, 1e-4, 0.0, "bms_avg_cell_voltage_V"),
        (4, 2, be_u16, 0.01, 0.0, "bms_pack_summed_voltage_V"),
        (6, 2, be_u16, 0.05, 0.0, "bms_soc_percent"),
    ],
    # BMS — 0x7D
    0x7D: [
        (0, 2, be_u16, 1e-4, 0.0, "bms_low_cell_voltage_V"),
        (2, 2, be_u16, 1e-4, 0.0, "bms_high_cell_voltage_V"),
        (4, 1, u8,     1.0,  0.0, "bms_max_cell_temp_C"),
    ],
    # BMS — 0x202 (limits fallback)
    0x202: [
        (1, 1, u8,     1.0, 0.0, "bms_max_dcl_A"),
        (2, 2, be_u16, 1.0, 0.0, "bms_max_ccl_A"),
    ],
    # BMS — 0x1806E5F4 (extended)
    0x1806E5F4: [
        (0, 2, be_u16, 0.1, 0.0, "bms_max_pack_voltage_V"),
        (2, 2, be_u16, 0.1, 0.0, "bms_ccl_ext_A"),
        (4, 1, u8,     1.0, 0.0, "bms_dtc_p0a08_flag"),
    ],
    # JBStats — 0x00E0
    0xE0: [
        (0, 1, u8, 1.0, 0.0, "jb_version"),
        (1, 1, u8, 1.0, 0.0, "jb_state"),
        (2, 1, u8, 1.0, 0.0, "jb_flags_b2"),  # LS/HS contacts, precharge, etc.
        (3, 1, u8, 1.0, 0.0, "jb_flags_b3"),  # ISO/BMS/INV fault bits
    ],
}

# Which IDs define a “row” (many sources in one time bucket)
ROW_IDS = set(SIGNAL_MAP.keys())
MERGE_WINDOW_S = 0.20  # merge messages within 200 ms

def decode_frame(can_id, data_bytes):
    out = {}
    for (start, length, func, scale, off, name) in SIGNAL_MAP.get(can_id, []):
        chunk = data_bytes[start:start+length]
        if len(chunk) != length: continue
        raw = func(chunk)
        out[name] = raw * scale + off
    # Expand some bitflags for convenience
    if can_id == 0x7C and "bms_flags_b0" in out:
        b0 = int(out["bms_flags_b0"])
        out.update({
            "bms_charge_power_signal":      1 if (b0 & (1<<0)) else 0,
            "bms_charge_enable_inverted":   1 if (b0 & (1<<1)) else 0,
        })
    if can_id == 0xE0:
        b2 = int(out.get("jb_flags_b2", 0))
        b3 = int(out.get("jb_flags_b3", 0))
        out.update({
            "jb_LS_Contact_EN": 1 if (b2 & (1<<0)) else 0,
            "jb_HS_Contact_EN": 1 if (b2 & (1<<1)) else 0,
            "jb_precharge_EN":  1 if (b2 & (1<<2)) else 0,
            "jb_discharge_EN":  1 if (b2 & (1<<3)) else 0,
            "jb_chrg_pre_EN":   1 if (b2 & (1<<4)) else 0,
            "jb_LS_chrg_EN":    1 if (b2 & (1<<5)) else 0,
            "jb_HS_chrg_EN":    1 if (b2 & (1<<6)) else 0,
            "jb_ISO_OK":        1 if (b3 & (1<<0)) else 0,
            "jb_ISO_FAULT":     1 if (b3 & (1<<1)) else 0,
            "jb_BMS_FAULT":     1 if (b3 & (1<<2)) else 0,
            "jb_INV_FAULT":     1 if (b3 & (1<<3)) else 0,
        })
    return out

def parse_stream(fp):
    buckets = defaultdict(lambda: {"vals": {}, "ids": set(), "start_ts": None})
    order = deque()
    for line in fp:
        m = LINE_RE.search(line)
        if not m: continue
        ts = float(m.group("ts"))
        can_hex = m.group("id")
        data_hex = m.group("data")
        can_id = int(can_hex, 16)
        data = bytes.fromhex(data_hex)
        if can_id not in ROW_IDS:
            continue

        key = round(ts / MERGE_WINDOW_S) * MERGE_WINDOW_S
        b = buckets[key]
        if b["start_ts"] is None:
            b["start_ts"] = ts
            order.append(key)

        decoded = decode_frame(can_id, data)
        b["vals"].update(decoded)
        b["ids"].add(can_id)

        # Emit as soon as we see something from this bucket (streaming approach)
        # You can tighten this to wait for specific combos if you prefer.
        row = {
            "timestamp": iso8601_from_epoch(b["start_ts"]),
        }
        row.update(b["vals"])
        yield row

        # Expire old buckets
        while order and (ts - (order[0] or 0)) > (MERGE_WINDOW_S * 2):
            old = order.popleft()
            buckets.pop(old, None)

def main():
    fp = open(sys.argv[1], "r") if len(sys.argv) > 1 else sys.stdin
    for row in parse_stream(fp):
        print(json.dumps(row, separators=(",", ":")))
    if fp is not sys.stdin:
        fp.close()

if __name__ == "__main__":
    main()
