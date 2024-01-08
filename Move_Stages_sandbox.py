from zaber_motion import Units, Library
from zaber_motion.binary import Connection

class Stage:
    def __init__(self, port="COM12"):
        self.MAX_LENGTH_X = 152.4
        self.MAX_LENGTH_Y = 146.7
        self.CALIBRATION_STEP_SIZE = 0.1
        self.start_x = 0
        self.start_y = 0
        self.connection = Connection.open_serial_port(port_name=port, baud_rate=9600)
        self.port_opened = True
        self.device_list = self.connection.detect_devices()
        print("Found {} devices".format(len(self.device_list)))
        self.device_left_right = self.device_list[1]
        self.device_up_down = self.device_list[0]
        self.device_forw_back = self.device_list[2]
        self.x_pos = self.device_left_right.get_position(unit=Units.LENGTH_MILLIMETRES)
        self.y_pos = self.device_up_down.get_position(unit=Units.LENGTH_MILLIMETRES)
        self.z_pos = self.device_forw_back.get_position(unit=Units.LENGTH_MILLIMETRES)
        self.x_pos_offset = 0
        self.y_pos_offset = 0
        self.z_pos_offset = 0
        self.MANUAL_OFFSET_X_B = 800000.0
        self.MANUAL_OFFSET_X_E = 3036.0
        self.MANUAL_OFFSET_Y_B = 647463.0
        self.MANUAL_OFFSET_Y_E = 200384

    def home(self):
        for device in self.device_list:
            device.home()


if __name__ == "__main__":
    try:
        stage = Stage(port="COM12")
        stage.home()
        x = input("Move stage x where? (mm): ")
        y = input("Move stage y where? (mm): ")
        z = input("Move stage z where? (mm): ")
        if x != '':
            pos_x = stage.device_left_right.move_absolute(position=float(x), unit=Units.LENGTH_MILLIMETRES)
        if y != '':
            pos_y = stage.device_up_down.move_absolute(position=139.2416 - float(y), unit=Units.LENGTH_MILLIMETRES)
        if z != '':
            pos_z = stage.device_forw_back.move_absolute(position=float(z), unit=Units.LENGTH_MILLIMETRES)
        # print("X: {} mm, Y: {} mm, Z: {} mm".format(pos_x, pos_y, pos_z))
    finally:
        stage.connection.close()

