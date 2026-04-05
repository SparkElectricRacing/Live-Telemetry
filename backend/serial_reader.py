
import time
import os
from queue import Queue
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo
from PySide6.QtSerialBus import QCanBus, QCanBusDevice, QCanBusFrame, QCanDbcFileParser
from PySide6.QtCore import QObject, Slot, QCoreApplication, QIODevice

# For Getting rpm_speed and mph_speed

def rpm_speed(raw_rpm):
    # int16_t rpmSpeed = -1 * static_cast<int16_t>(raw_rpm); // masking off the sign bit
    if raw_rpm > 32767: #for testing files 
        raw_rpm -= 65536
    return -1*raw_rpm
def mph_speed(rpm_speed): # Adapted from the google docs
    FRONT_SPROCKET_TEETH = 16.0
    REAR_SPROCKET_TEETH = 50.0 # Talon TR371 50 520 Sprocket
    WHEEL_DIAMETER_INCHES = 25.7 #Wheel Diameter is 17", with tire ~26"
    PI = 3.14159265358979323846
    INCHES_TO_MILES = 1.0 / 63360.0
    MINUTES_PER_HOUR = 60.0
    # Gear reduction ratio
    gearRatio = FRONT_SPROCKET_TEETH / REAR_SPROCKET_TEETH
    # Rear wheel RPM
    wheelRPM = rpm_speed * gearRatio
    # Wheel circumference in miles
    wheelCircumferenceMiles = PI * WHEEL_DIAMETER_INCHES * INCHES_TO_MILES
    # Speed = wheel RPM * circumference * 60 (minutes to hours)
    speedMPH = wheelRPM * wheelCircumferenceMiles * MINUTES_PER_HOUR
    return speedMPH


class Serial_receiver():
    def __init__(self):
        self.buffer = ''
        self.ser = QSerialPort('/dev/pts/2')
        self.ser.setBaudRate(115200)
        if (not self.ser.open(QIODevice.ReadyOnly)):
            print("nope")
            return 1
        self.ser.readyRead().connect(self.handler)
        
    @Slot()
    def handler(self):
        self.buffer = self.ser.readAll()
        # buffer is a string - so basically get buffer length
        buf_size = self.buffer.length()
        msgs = buf_size // 18
        remainder = buf_size % 18
        msg_queue = Queue()
        for i in range(msgs):
            msg_queue.put(buffer.substr(i*18, 18))
        buffer = buffer.substr(msgs*18, remainder)
        
        # now make a BUNCH of frames
        # 1 + 8 + 4 + 4 + 1 but rn all are 8 bits a byte
        # frameId = f"{frame.frameId():08X}"
        # payload = f"{int(frame.payload().toHex().toUpper().data().decode(), 16):016X}" # make this into 8byte
        # timestamp = f"{(((frame.timeStamp().seconds()*1000000 + frame.timeStamp().microSeconds()) // 1000)-self.boot_time):08X}" 
        # sendable = bin(int(("9A" +payload + frameId + timestamp + "BB"), 16))[2:].zfill(36*4)
        while (not msq_queue.empty()):
            msg = int((msg_queue.get()).substr(), 2)
            msg = hex(msg)
            print(msg)