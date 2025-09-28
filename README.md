# Live-Telemetry

Modular Live Telemetry Project for Zephryus:
- Communicates through low frequency radio  
- Includes dashboard for visualization

## Set-up

### Linux/WSL Install for Dashboard (all commands on WSL unless specified)

#### Python Setup

1. Update existing dependencies `sudo apt update`

2. Install Python through terminal `sudo apt install python3 -y`

3. Install Python library manager with `sudo apt install python3-pip -y` 

4. Create virtual enviornment with `python3 -m venv env`

5. Enter virtual enviornment `source env/bin/activate`

6. Install libraries with `pip install -r requirements.txt`

#### Arduino Setup

1. Open Powershell as Admin

2. On Powershell run `usbipd list` to list all USB devices attached to Windows, noting which device is the ESP32

3. On Powershell run `usbipd attach --wsl --busid <BUSID>` to attach USB device to WSL, where `<BUSID>` is the value from step 8 ex. `2-1`

4. Go back to WSL and run `lsusb` to confirm that the ESP32 is now visible inside WSL. Example output `ID 10c4:ea60 Silicon Labs CP210x USB to UART Bridge`

5. Run `dmesg | grep tty` to see which COM port Linux assigned to the USB port. Look for something like `/dev/ttyUSB0`

6. Run `sudo chmod 666 <PORT NAME>` to give the port permissions, port name is defined above

7. Inside `FILE TBD` replace the port name with the one from `dmesg/lsusb`