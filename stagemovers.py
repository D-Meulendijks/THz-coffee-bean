import logging
from zaber_motion import Units, BinaryCommandFailedException
from zaber_motion.binary import Connection
import numpy as np
from datetime import datetime
from string import Template
import os

from fakeenvironment import FakeConnection, FakeStage


def rearrange_devices(device_list, permutation):
    return [device_list[i] for i in permutation]


class StageMover:

    def __init__(self, settings: dict):
        # Device names ordered in the way they are connected. index 0 = closest to computer
        self.port: str = settings["port"]
        self.device_names: list = settings["device_names"]
        self.max_lengths: list = settings["max_lenghts"]
        self.permutation: list = settings["permutation"]

        self.port_opened: bool = False
        self.homed: bool = False
        self.device_list: list = []
        self.connection = None

    def connect(self, fake: bool = True):
        """
        Connect with the three stages.
        """
        if fake:
            self.connection = FakeConnection()
            self.device_list = [FakeStage(i) for i in range(3)]
            logging.info(f"Found {len(self.device_list)} devices")
            self.port_opened = True
            return True

        try:
            self.connection = Connection.open_serial_port(port_name=self.port, baud_rate=9600)
            logging.info("Connected with serial port")
            self.device_list = self.connection.detect_devices()
            self.device_list = [self.device_list[i] for i in self.permutation]
        except Exception as e:
            logging.critical(f"Error connecting to device: {e}")
            return False
        self.port_opened = True
        logging.info(f"Found {len(self.device_list)} devices")
        return True

    def disconnect(self):
        self.connection.close()

    def get_pos(self):
        """
        Get current position of all stages.
        """
        assert self.port_opened, "Device not connected yet. Use Stage_object.connect()"
        unit = Units.LENGTH_MILLIMETRES
        position = []
        for device in self.device_list:
            position.append(device.get_position(unit=unit))
        return position

    def home(self):
        """
        Sends all stages to the zero position. This function needs to be called upon initialization.
        It can also be used as a reset or recalibrate.
        """
        assert self.port_opened, "Device not connected yet. Use Stage_object.connect()"
        logging.info("Performing home operation")
        try:
            for device in self.device_list:
                device.home()
            self.homed = True
        except BinaryCommandFailedException as e:
            logging.critical(f"Home failed: {e}")
            logging.critical(f"Make sure the knobs on the stages are turned into neutral position.")
        except Exception as e:
            logging.critical(f"Home failed: {e}")

    def move(self, pos: float, device_name: str, mode: str = "absolute") -> float:
        """
        Move stage on axis "device_name" to "pos". Returns ended up position
        """
        device_index = self.device_names.index(device_name)
        if pos > self.max_lengths[device_index]:
            pos = self.max_lengths[device_index]
            logging.warning(
                f"Position {pos} exceeds maximum length of axis {device_name}. Clipping position to maximum value")
        device = self.device_list[device_index]
        try:
            if mode == "absolute":
                end_pos = device.move_absolute(position=float(pos), unit=Units.LENGTH_MILLIMETRES)
            elif mode == "relative":
                end_pos = device.move_relative(position=float(pos), unit=Units.LENGTH_MILLIMETRES)
            else:
                logging.warning(f"Moving {device_name} with mode '{mode}' not found.")
        except BinaryCommandFailedException as e:
            logging.warning(f"Movement exceeded maximum length of axis {device_name}. Please adjust the limits.")
            logging.warning(f"Resulted in error: {e}")
            end_pos = self.get_pos()[device_index]
        return end_pos


    def move_all(self, pos_list: list, mode: str = "absolute") -> list:
        end_pos = []
        for device_name, pos in zip(self.device_names, pos_list):
            end_pos.append(self.move(pos, device_name, ))
        return end_pos


class DeltaTemplate(Template):
    delimiter = "%"


def strfdelta(tdelta, fmt):
    d = {"D": tdelta.days}
    hours, rem = divmod(tdelta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    d["H"] = '{:02d}'.format(hours)
    d["M"] = '{:02d}'.format(minutes)
    d["S"] = '{:02d}'.format(seconds)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)


class StageGridMover:
    """
    Moves a combination of stages in a grid-like configuration.
    Calling a function on every point of the grid
    
    example settings = {
        x_min: 45,
        x_max: 55,
        x_n: 10,
        y_min: 45,
        y_max: 55,
        y_n: 10,
        z_min: 45,
        z_max: 55,
        z_n: 10,
    }
    """

    def __init__(self, stage_mover: StageMover, settings: dict):
        self.stage_mover = stage_mover
        self.x_min: float = settings["x_min"]
        self.y_min: float = settings["y_min"]
        self.z_min: float = settings["z_min"]
        self.x_max: float = settings["x_max"]
        self.y_max: float = settings["y_max"]
        self.z_max: float = settings["z_max"]
        self.x_n: float = settings["x_n"]
        self.y_n: float = settings["y_n"]
        self.z_n: float = settings["z_n"]

    def run_grid(self, func):
        x_grid = np.linspace(self.x_min, self.x_max, self.x_n)
        y_grid = np.linspace(self.y_min, self.y_max, self.y_n)
        z_grid = np.linspace(self.z_min, self.z_max, self.z_n)

        start_time = datetime.now()
        total_iterations = self.x_n * self.y_n * self.z_n
        logging.info("Starting grid measurement")
        iteration = 0
        for z in z_grid:
            self.stage_mover.move(z, "z")
            for x in x_grid:
                self.stage_mover.move(x, "x")
                for y in y_grid:
                    iteration += 1
                    self.stage_mover.move(y, "y")
                    time_passed = datetime.now() - start_time
                    time_left = time_passed * total_iterations / iteration
                    logging.info(
                        f"Position: ({x:04f}, {y:04f}, {z:04f}), Iteration: {iteration}/{total_iterations}, Time passed: {strfdelta(time_passed, '%H:%M:%S')}, Estimated time left: {strfdelta(time_left, '%H:%M:%S')}")
                    func([x, y, z])


class StageCalibrator:
    """
    Figures out what minimum and maximum values to use for the StageGridMover
    """

    def __init__(self, settings_calibration: dict, measure_function, stagemover: StageMover):
        self.settings = settings_calibration
        self.measure_function = measure_function
        self.stagemover = stagemover

    def rough_calibration(self):
        self.start_positions = [25, 50, 25]#self.stagemover.get_pos()
        self.stagemover.home()

        self.middle_positions = self.start_positions
        calibrated_positions = []
        for device_id in range(2):
            middlepos = 0
            for direction in [False, True]:
                self.stagemover.move_all(self.middle_positions)
                logging.info(f"Calibrating {self.stagemover.device_names[device_id]} +")
                offset, _, _ = self.calibrate_axis(device_id, direction)
                calibrated_positions.append(offset)
                middlepos = middlepos + offset / 2
            self.middle_positions[device_id] = middlepos
        x_min, x_max, y_min, y_max = calibrated_positions
        return [x_min, x_max, y_min, y_max]

    def calibrate_axis(self, device_id: int, direction: bool = True):
        current_position = self.stagemover.get_pos()
        pos = current_position[device_id]
        energies = []
        offsets = []
        margin = self.settings["margin"]
        max_deviation_from_center = self.settings["max_deviation_from_center"]
        device_name = self.stagemover.device_names[device_id]

        calibration_step_size = self.settings["rough_step_size"]
        if not direction:  # negative direction
            calibration_step_size = -calibration_step_size

        for _ in range(100): # soft limit
            pos_within_min_boundary = pos < max_deviation_from_center + self.start_positions[device_id] - calibration_step_size
            pos_within_max_boundary = pos > self.start_positions[device_id] - max_deviation_from_center + calibration_step_size
            if not (pos_within_min_boundary and pos_within_max_boundary):
                break
            print(f"{device_name}: {pos} mm")
            pos = self.stagemover.move(calibration_step_size, device_name, "relative")
            pulse = self.measure_function(self.stagemover.get_pos())
            energies.append(pulse.energy())
            offsets.append(pos)

        background_reference = np.mean(np.sort(energies)[-5:])  # Calculate average energy of 5 maximum energies
        energy_margin = margin * background_reference

        energies = np.array(energies)
        offsets = np.array(offsets)

        energies_passed = energies[energies < energy_margin]
        offsets_passed = offsets[energies < energy_margin]
        if len(offsets_passed > 0):
            last_offset = offsets_passed[-1]
        else:
            last_offset = offsets[0]

        return last_offset, energies_passed, energies_passed


def create_folder_if_not_exists(folder_path):
    # Check if the folder exists
    if not os.path.exists(folder_path):
        try:
            # Create the folder if it doesn't exist
            os.makedirs(folder_path)
            logging.info(f"Folder '{folder_path}' created successfully.")
        except OSError as e:
            logging.critical(f"Failed to create folder '{folder_path}': {e}")
    else:
        logging.debug(f"Folder '{folder_path}' already exists, no new one created.")


def configure_logger():
    create_folder_if_not_exists("./logs")
    filename_time = datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
    file_handler = logging.FileHandler(f'./logs/log_{filename_time}.log')
    file_handler.setLevel(logging.DEBUG)  # Set the file handler level to capture all levels

    file_handler_warning = logging.FileHandler(f'./logs/warnlog_{filename_time}.log')
    file_handler_warning.setLevel(logging.WARNING)  # Set the file handler level to capture all levels

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S')
    file_handler.setFormatter(formatter)
    file_handler_warning.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    logging.root.addHandler(file_handler)
    logging.root.addHandler(file_handler_warning)
    logging.root.addHandler(console_handler)
    logging.root.setLevel(logging.DEBUG)


if __name__ == "__main__":
    configure_logger()

    stagegridmover_settings = {
        "x_min": 35,
        "x_max": 65,
        "x_n": 15,
        "y_min": 35,
        "y_max": 65,
        "y_n": 15,
        "z_min": 22,
        "z_max": 22,
        "z_n": 1,
    }

    stagemover_settings = {
        "port": "COM4",
        "device_names": ["x", "y", "z"],
        "max_lenghts": [140, 140, 45],
        "permutation": [2, 0, 1],
    }

    try:
        stage_mover = StageMover(stagemover_settings)
        stage_mover.connect()
        stage_mover.home()
        stage_mover.move_all([10, 0, 0])

        # stage_grid_mover = StageGridMover(stage_mover, stagegridmover_settings)
        # stage_grid_mover.run_grid(call_function)
        # stage_mover.home()
    except Exception as e:
        logging.CRITICAL(f"Program crashed: {e}")
    finally:
        stage_mover.disconnect()
