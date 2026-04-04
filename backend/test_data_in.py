# goal is to receive CAN Messages
# will receive the ones animesh sends and then
# will check their format
# then will try to make sure in good format for use
# then send thru to the backend as our input data
from PySide6.QtSerialBus import QCanBus, QCanBusDevice
from PySide6.QtCore import QObject, Slot

# To test:

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
        self.device, self.error = QCanBus.createDevice("socketcan", "vcan0")
        if not self.device.connectDevice():
            print("failed to initialise connection with device")
        # now device must be connected
        self.device.framesReceived.connect(self.frame_receiver)
    
    # This func is called whenever we receive a frame
    @Slot()
    def frame_receiver(self):
        while self.device.framesAvailable():
            frame = self.device.readFrame()
            print(frame.toString())
