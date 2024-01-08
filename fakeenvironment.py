
import time
import logging
import numpy as np

global realworld_positions
realworld_positions = [0, 0, 0]

class FakePulse:
    def __init__(self, position):
        self.bean_center = np.array([25, 50, 25])
        self.position = position
    
    def signal(self):
        return self.energy()*np.ones(2000)

    def energy(self):
        distance = np.linalg.norm(np.array(self.position) - self.bean_center)
        if distance > 8:
            meas = 100
        else:
            meas = 0.5
        logging.debug(f"{meas}, {self.bean_center}, {self.position}, {distance}")
        return meas

class FakeTFC:
    def __init__(self, settings):
        self.averaging = 1

    def start_laser(self):
        logging.info("Laser started")

    def connect(self):
        time.sleep(1)
        return True

    def set_averaging(self, n):
        self.averaging = n

    def get_corrected_pulse(self, position):
        time.sleep(self.averaging/10000)
        return FakePulse(position)

class FakeConnection:
        def __init__(self):
            time.sleep(1)
            pass
            
        def close(self):
            pass

class FakeStage:
    def __init__(self, device_id):
        self.pos = 25
        self.device_id = device_id

    def move_absolute(self, position, unit="s"):
        time.sleep(0.01)
        self.pos = position
        global realworld_positions
        realworld_positions[self.device_id] = self.pos
        return self.pos

    def get_position(self, unit):
        return self.pos

    def home(self):
        time.sleep(0.05)
        self.pos = 0
        global realworld_positions
        realworld_positions[self.device_id] = 0

    def move_relative(self, position, unit="s"):
        time.sleep(0.01)
        self.pos = self.pos + position
        global realworld_positions
        realworld_positions[self.device_id] = self.pos
        return self.pos