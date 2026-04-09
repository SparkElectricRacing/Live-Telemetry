#!/usr/bin/env python3
# goal is to receive CAN Messages
# will receive the ones animesh sends and then
# will check their format
# then will try to make sure in good format for use
# then send thru to the backend as our input data
import sys
import signal
import time
import serial
from PySide6.QtSerialBus import QCanBus, QCanBusDevice
from PySide6.QtCore import QObject, Slot, QCoreApplication
try:
    # for the server from the root directory
    from backend import global_vars as gv  
except (ImportError, ModuleNotFoundError):
    # for running arduino_reader.py directly for testing
    import global_vars as gv
    
# Run this for your serial ports
# sudo socat -d -d PTY,link=/dev/ttyV0 PTY,link=/dev/ttyV1

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
        self.boot_time = time.time_ns() // 1000000 # in milliseconds
        self.device, self.error = QCanBus.instance().createDevice("socketcan", "vcan0")
        if self.device:
            if not self.device.connectDevice():
                print("failed to initialise connection with device")
            self.device.framesReceived.connect(self.frame_receiver)
            try:
                self.ser = serial.Serial('/dev/ttyV1', 115200, rtscts=True,dsrdtr=True)
            except serial.SerialException as e:
                print(e)
                return
            
            
    # This func is called whenever we receive a frame
    @Slot()
    def frame_receiver(self):
        while self.device.framesAvailable():
            frame = self.device.readFrame()
            #print(frame.toString())
            #print(f"{(frame.timeStamp().seconds()*1000000 + frame.timeStamp().microSeconds()):016X}") # 8 bytes of timestamp - could be 7
            #print(f"{(((frame.timeStamp().seconds()*1000000 + frame.timeStamp().microSeconds()) // 1000)-self.boot_time):016X}") 
            #print(f"{frame.frameId():08X}")
            #print(f"{int(frame.payload().toHex().toUpper().data().decode(), 16):016X}")
            frameId = f"{frame.frameId():08X}"
            payload = f"{int(frame.payload().toHex().toUpper().data().decode(), 16):016X}" # make this into 8byte
            timestamp = f"{(((frame.timeStamp().seconds()*1000000 + frame.timeStamp().microSeconds()) // 1000)-self.boot_time):08X}" 
            sendable = int(("9A" +payload + frameId + timestamp + "BB"), 16).to_bytes(18, byteorder='big')
            print("9A" + payload + frameId + timestamp + "BB")
            #print(sendable)
            #print(type(sendable))
            self.ser.write(sendable)
            
            
if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL) # allows to ^C out of project instead of ^/ core dumping
    app = QCoreApplication(sys.argv)
    c1 = CANBus()
    sys.exit(app.exec())
    
    
# use relative sent thru and on backend take realtime and then check clockdrift and make sure ur times are in fact synced
