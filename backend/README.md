# Backend

## file_parser.py

This reads 16 byte lines from the arduino using pyserial, and then parses them according to the specifications laid out below.

[0] hardcoded sanity assert value (0xbb)
[1] CAN device id
[2] Subidentifier (for devices that send more than one type of data per address, i.e. from BMS AUX (0x7D): 0x00 = low cell V, 0x01 = high cell V, etc.)
[3-6] timestamp, in ms from device enable
[7-14*] data, big-endian
[15*] hardcoded sanity assert value (0x9a)

Then with our CAN device id and Subidentifier we need to find our signal name. The pairings are below.

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

This corresponds with the table below. We also need to take our data bytes and perform the conversions outlined below to get our real data.

| Frame ID                | Sub Signal        | Type     | Data Format / Conversion                                                                    |
| ----------------------- | ----------------- | -------- | ------------------------------------------------------------------------------------------- |
| BMS_MSG (0x07C)         | avg_temp          | int      | `static_cast<int>(frame->data[1])`                                                          |
| BMS_MSG (0x07C)         | avg_cell_voltage  | double   | `static_cast<double>((frame->data[2] << 8) + frame->data[3]) / 10000`                       |
| BMS_MSG (0x07C)         | pack_voltage      | double   | `static_cast<double>((frame->data[4] << 8) OR frame->data[5]) / 100`                        |
| BMS_MSG (0x07C)         | pack_SOC          | double   | `static_cast<double>((frame->data[6] << 8) OR frame->data[7]) / 20`                         |
| BMS_MSG (0x07C)         | is_charging       | bool     | `frame->data[0] == 1`                                                                       |
| BMS_AUX_MSG (0x07D)     | low_cell_voltage  | double   | `static_cast<double>((frame->data[0] << 8) + frame->data[1]) / 10000`                       |
| BMS_AUX_MSG (0x07D)     | high_cell_voltage | double   | `static_cast<double>((frame->data[2] << 8) + frame->data[3]) / 10000`                       |
| BMS_AUX_MSG (0x07D)     | max_cell_temp     | int      | `static_cast<int>(frame->data[4])`                                                          |
| BMS_AUX_MSG (0x07D)     | DTC1              | int      | `static_cast<int>((frame->data[6] << 8) OR frame->data[7])`                                 |
| INV_MOTOR_SPEED (0x0A5) | raw_rpm           | uint16_t | `raw_rpm = frame->data[2] OR (frame->data[3] << 8)`                                         |
| INV_MOTOR_SPEED (0x0A5) | rpmSpeed          | int16_t  | `int16_t rpmSpeed = -1 * static_cast<int16_t>(raw_rpm)`                                     |
| INV_MOTOR_SPEED (0x0A5) | mphSpeed          | int      | `int mphSpeed = rpms_to_mph(static_cast<int>(rpmSpeed))`                                    |

Then we send the data through to a thread-safe buffer in global_vars.py.

## server.py

Here we take our data and put it in a JSON organised in the below format.

{"RPM": {"Time":[...], "Data":[...]}, "Voltage": {"Time":[...], "Data":[...]}, ...}

This is sent off to the front-end for use.
