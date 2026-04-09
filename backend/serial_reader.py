#!/usr/bin/env python3
import time
import os
import signal
import sys
import serial
import re
from queue import Queue
from PySide6.QtSerialBus import QCanBus, QCanBusDevice, QCanBusFrame, QCanDbcFileParser, QCanFrameProcessor
from PySide6.QtCore import QObject, Slot, QCoreApplication, QIODevice

# message should be 36 Hex digits cause 18B and first is 9A and last is BB
# check A-F0-9
msg_format_check = "^(9A|9a)[A-Fa-f0-9]{32}(BB|bb)$"

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
        self.dbcParser = QCanDbcFileParser()
        
        if not self.dbcParser.parse("static/20250206_CM_not_oil-cooled_CAN_DB.dbc"):
            print("dbcfileparser failed to parse the file")
        self.frameProcessor = QCanFrameProcessor()
        self.frameProcessor.setUniqueIdDescription(QCanDbcFileParser.uniqueIdDescription())
        self.frameProcessor.setMessageDescriptions(self.dbcParser.messageDescriptions())
        self.buffer = ''
        try:
            self.ser = serial.Serial('/dev/ttyV0', 115200, rtscts=True,dsrdtr=True)
        except serial.SerialException as e:
            print(e)
            return
        self.boot_time = time.time_ns() // 1000000 # in milliseconds
        while True: # criminal acitvities btw if you can make something that on in_waiting > 0 you trigger handler then do that
            if self.ser.in_waiting:
                # print("did i make it dad", self.ser.in_waiting)
                bits = (self.ser.in_waiting // (36)) * 36
                # print("I made it dad", bits)
                self.handler(bits)
            time.sleep(0.01) 
    
    def handler(self, bits):
        # print('in handler')
        self.buffer = self.ser.read(bits).hex()
        # print(self.buffer)
        # buffer is a string - so basically get buffer length
        buf_size = len(self.buffer)
        if buf_size:
            msgs = buf_size // (36)
            remainder = buf_size % (36)
            msg_queue = Queue()
            for i in range(msgs):
                msg_queue.put(self.buffer[i*36:(i+1)*36])
            self.buffer = b''
            
            # now make a BUNCH of frames
            # 1 + 8 + 4 + 4 + 1 but rn all are 8 bits a byte
            # frameId = f"{frame.frameId():08X}"
            # payload = f"{int(frame.payload().toHex().toUpper().data().decode(), 16):016X}" # make this into 8byte
            # timestamp = f"{(((frame.timeStamp().seconds()*1000000 + frame.timeStamp().microSeconds()) // 1000)-self.boot_time):08X}" 
            # sendable = bin(int(("9A" +payload + frameId + timestamp + "BB"), 16))[2:].zfill(36*4)
            while (not msg_queue.empty()):
                msg = msg_queue.get()
                # check message in valid format
                if not (re.search(msg_format_check, msg)):
                    print("error in message format - possible corruption")
                    continue
                # "9A" + payload + frameId + timestamp + "BB" = 2 + 16 + 8 + 8 + 2
                frame = QCanBusFrame()
                frame.setFrameId(int(msg[18:26], 16))
                frame.setPayload(int(msg[2:18], 16).to_bytes(8, byteorder='big'))
                # timestamp currently relative
                timestamp = QCanBusFrame.TimeStamp.fromMicroSeconds((self.boot_time + int(msg[26:34], 16))*1000)
                frame.setTimeStamp(timestamp)
                parseResult = self.frameProcessor.parseFrame(frame)
                signalValues = parseResult.signalValues
                if "INV_Motor_Speed" in signalValues:
                    signalValues["MPH_SPEED"] = mph_speed(signalValues["INV_Motor_Speed"])
                    signalValues["RPM_SPEED"] = rpm_speed(signalValues["INV_Motor_Speed"]) # currently * -1 unsure of correctness
                # Successfully gets to this point
                for sv in signalValues:
                    print(sv, ":", signalValues[sv])
                
                
                
                
            
if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL) # allows to ^C out of project instead of ^/ core dumping
    app = QCoreApplication(sys.argv)
    s1 = Serial_receiver()
    sys.exit(app.exec())
