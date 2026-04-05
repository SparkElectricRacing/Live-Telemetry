#!/usr/bin/env python3
# goal is to receive CAN Messages
# will receive the ones animesh sends and then
# will check their format
# then will try to make sure in good format for use
# then send thru to the backend as our input data
import sys
import signal
import time
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo
from PySide6.QtSerialBus import QCanBus, QCanBusDevice
from PySide6.QtCore import QObject, Slot, QCoreApplication, QIODevice
try:
    # for the server from the root directory
    from backend import global_vars as gv  
except (ImportError, ModuleNotFoundError):
    # for running arduino_reader.py directly for testing
    import global_vars as gv
    
# Run this for your serial ports
# socat -d -d pty,raw,echo=0 pty,raw,echo=0

# To test (linux pls):

# sudo modprobe vcan
# sudo ip link add dev vcan0 type vcan
# sudo ip link set up vcan0

# candump vcan0

# Then run the CAN Testbench - be sure to open that env in sep terminal first and dl everything
# ./GUI.py

# CANBus class
class CANBus():
    
    # This is init it sets up our signal slot connection so we can receive msgs
    def __init__(self):
        # Set up a CANBus device with socketcan for vcan0
        # can be changed but rn want vcan0 for simulation tests
        # if want real input then rly we are not using this file - will instead connect to the
        # bike via arduino. Antenna will send msg thru to arduino we plug into computer and then
        # that data will go thru to the backend and populate frontend
        self.device, self.error = QCanBus.instance().createDevice("socketcan", "vcan0")
        if self.device:
            # now device must be connected
            if not self.device.connectDevice():
                print("failed to initialise connection with device")
            # This sets up a signal slot pair
            ####### Set the program's start time in milliseconds to get approp for making 4 byte timestamps relative to bike ignition
            self.device.framesReceived.connect(self.frame_receiver)
            # what this means is that whenever we receive a frame, we automatically have it handled by our frame_receiver
            # no while loops needed and no busy waiting!
            
            # QSerialPort setup
            self.ser = QSerialPort('/dev/pts/1')
            self.ser.setBaudRate(115200)
            
            if (not self.ser.open(QIODevice.WriteOnly)):
                print("nope")
                return
            self.boot_time = time.time_ns() // 1000000 # in milliseconds
    # This func is called whenever we receive a frame
    @Slot()
    def frame_receiver(self):
        while self.device.framesAvailable():
            frame = self.device.readFrame()
            # We get here so are receiving messages.
            # print(frame.toString())
            # print(f"{(frame.timeStamp().seconds()*1000000 + frame.timeStamp().microSeconds()):016X}") # 8 bytes of timestamp - could be 7
            # print(f"{(((frame.timeStamp().seconds()*1000000 + frame.timeStamp().microSeconds()) // 1000)-self.boot_time):016X}") 
            # get relative timestamp format and have it 4 Byte
            # print(f"{frame.frameId():08X}")
            # print(f"{int(frame.payload().toHex().toUpper().data().decode(), 16):016X}")
            # example format of in msg - note we are infact getting this data in little endian (@1 on dbc file). Big Endian would be @0 but yeah
            # little endian format - im not converting for now. If our results are not what we sent thru then will change 
            # (defer if not sure necessary and then if necessary implement later otherwise dont)
            frameId = f"{frame.frameId():08X}"
            payload = f"{int(frame.payload().toHex().toUpper().data().decode(), 16):016X}" # make this into 8byte
            timestamp = f"{(((frame.timeStamp().seconds()*1000000 + frame.timeStamp().microSeconds()) // 1000)-self.boot_time):08X}" 
            sendable = bin(int(("9A" +payload + frameId + timestamp + "BB"), 16))[2:].zfill(36*4)
            self.ser.write(sendable)
            
            
if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL) # allows to ^C out of project instead of ^/ core dumping
    app = QCoreApplication(sys.argv)
    c1 = CANBus()
    sys.exit(app.exec())
    
    
# use relative sent thru and on backend take realtime and then check clockdrift and make sure ur times are in fact synced
