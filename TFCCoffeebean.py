from stagemovers import StageMover, StageGridMover, StageCalibrator
import logging
from datetime import datetime
import os
from fakeenvironment import FakeTFC
import numpy as np
import matplotlib.pyplot as plt

PLOT_MAXIMUM_ENERGY = 100
PLOT_MINIMUM_ENERGY = 0


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

class TFC:
    def __init__(self, teraflash_settings):
        super().__init__(teraflash_settings["toptica_IP"])
        self.teraflash_settings = teraflash_settings

    def connect(self):
        logging.info(f"Connecting...")
        connection_result = self.connect()
        logging.info(f"Connected")
        return connection_result

    def start_laser(self):
        self.set_averaging(self.settings.TFC_AVERAGING)
        if self.teraflash_settings["TRANSFER"] == "block":
            self.set_block_transfer()
        else:
            self.set_sliding_transfer()
        self.set_begin(self.teraflash_settings.TFC_BEGIN)
        self.set_range(self.teraflash_settings.TFC_RANGE)
        self.start(wait=True)
        print("Connected and started the laser")

    def get_corrected_pulse(self):
        pulse = self.get_trace()
        offset = pulse.E()[0:10].mean()
        pulse.subtract_offset(offset)
        return pulse

        
class MeasurementPlotter:
    def __init__(self, settings: dict):
        self.width = settings["stagegridmover"]["x_n"] # width
        self.height = settings["stagegridmover"]["y_n"] # height
        self.x_max = settings["stagegridmover"]["x_max"]
        self.x_min= settings["stagegridmover"]["x_min"]
        self.y_max = settings["stagegridmover"]["y_max"]
        self.y_min= settings["stagegridmover"]["y_min"]

        self.image_data = np.zeros((self.width, self.height))
        self.batch_number = 5
        self.batch_iteratator = 0
        self.values = []

    def create_plot(self):
        plt.ion()  # Enable interactive mode
        self.fig, self.ax = plt.subplots()
        self.im = self.ax.imshow(self.image_data, cmap='viridis', interpolation='nearest',
                                 extent=(self.x_min, self.x_max, self.y_min, self.y_max), vmin=PLOT_MINIMUM_ENERGY, vmax=PLOT_MAXIMUM_ENERGY)
        plt.colorbar(self.im)  # Add a colorbar to show measurement values
        self.ax.set_title('Measurements in Image')
        self.ax.set_xlabel('X-axis')
        self.ax.set_ylabel('Y-axis')
        plt.show()

    def update_plot(self, new_values):
        self.batch_iteratator += 1
        self.values.append([np.max(new_values[0]), new_values[1]])
        if self.batch_iteratator % self.batch_number != 0:
            return
        
        x_coords = np.linspace(self.x_min, self.x_max, self.width)
        y_coords = np.linspace(self.y_min, self.y_max, self.height)

        for value in self.values:
            measurement, [x_pos, y_pos, _] = value

            # Interpolate positions to map to image grid
            x_pixel = np.argmin(np.abs(x_coords - x_pos))
            y_pixel = np.argmin(np.abs(y_coords - y_pos))

            if 0 <= x_pixel < self.width and 0 <= y_pixel < self.height:
                self.image_data[y_pixel, x_pixel] = measurement

        self.values = []

        # Update the displayed image
        self.im.set_data(self.image_data)
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()


class TFCCoffeeBean:
    def __init__(self, settings):
        self.settings = settings
        self.teraflash = FakeTFC(self.settings["teraflash"])
        self.stagemover = StageMover(self.settings["stagemover"])
        logging.debug(f"Settings: {self.settings}")

        self.measurement_savefolder = self.settings["general"]["measurement_savefolder"]
        self.measurement_savefolder_pulses = os.path.join(self.measurement_savefolder, "pulses")
        create_folder_if_not_exists(self.measurement_savefolder)
        create_folder_if_not_exists(self.measurement_savefolder_pulses)
        self.measurement_savepath = os.path.join(self.measurement_savefolder, self.settings["general"]["measurement_name"])
        self.measurement_savepath_screen = os.path.join(self.measurement_savefolder, self.settings["general"]["measurement_name_screen"])
        logging.debug(f"Savepaths: {self.measurement_savepath}, {self.measurement_savepath_screen}")
        self.pulse_db = []
        self.temp_pulse_db = []
        self.plot_batch_counter = 0

    def connect_teraflash(self):
        connection = self.teraflash.connect()
        self.teraflash.start_laser()
        return connection
        #self.stagemover.home()

    def connect_stagemover(self):
        connection = self.stagemover.connect()
        return connection

    def calibrate(self):
        self.stagecalibrator = StageCalibrator(self.settings["calibration"], self.teraflash.get_corrected_pulse, self.stagemover)

        logging.info(f"Starting calibration")
        self.teraflash.set_averaging(1)
        [x_min, x_max, y_min, y_max] = self.stagecalibrator.rough_calibration()
        self.teraflash.set_averaging(self.settings["teraflash"]['TFC_AVERAGING'])
        logging.info(f"Calibration resulted in x: [{x_min}, {x_max}], y: [{y_min}, {y_max}]")

        self.settings["stagegridmover"]["x_min"] = x_min
        self.settings["stagegridmover"]["x_max"] = x_max
        self.settings["stagegridmover"]["y_min"] = y_min
        self.settings["stagegridmover"]["y_max"] = y_max
        logging.debug(f"New settings: {self.settings}")

        self.run_gridmover_screen()
        return [x_min, x_max, y_min, y_max]

    def run_gridmover_screen(self):
        self.settings["stagegridmover"]["x_n"] = 10
        self.settings["stagegridmover"]["y_n"] = 10
        self.plotter = MeasurementPlotter(self.settings)
        self.plotter.create_plot()
        self.teraflash.set_averaging(2)
        logging.info(f"Starting gridmove screen")
        self.stagegridmover = StageGridMover(self.stagemover, self.settings["stagegridmover"])
        self.stagegridmover.run_grid(self.measure_and_log_screen)
        self.teraflash.set_averaging(self.settings["teraflash"]['TFC_AVERAGING'])

    def run_gridmover(self):
        self.settings["stagegridmover"]["x_n"] = 100
        self.settings["stagegridmover"]["y_n"] = 100
        self.plotter = MeasurementPlotter(self.settings)
        self.plotter.create_plot()
        logging.info(f"Starting gridmove")
        self.stagegridmover = StageGridMover(self.stagemover, self.settings["stagegridmover"])
        self.stagegridmover.run_grid(self.measure_and_log)
        
        plt.ioff()  # Turn off interactive mode to keep the plot open after the program finishes
        plt.show()

    def measure_and_log(self, position):
        measurement = self.teraflash.get_corrected_pulse(self.stagemover.get_pos()).signal()
        current_time = datetime.now()
        self.plotter.update_plot([measurement, position])

        pulse_name = f"{current_time.strftime('%Y-%m-%d_%H-%M-%S-%f')}.npy"
        pulse_path = os.path.join(self.measurement_savefolder_pulses, pulse_name)
        np.save(pulse_path, measurement)
        with open(self.measurement_savepath, 'a') as file:
            file.write(f"{current_time.strftime('%Y-%m-%d %H:%M:%S.%f')}_{pulse_path}_{position[0]},{position[1]},{position[2]}\n")
        return measurement

    def measure_and_log_screen(self, position):
        measurement = self.teraflash.get_corrected_pulse(self.stagemover.get_pos()).signal()
        current_time = datetime.now()
        self.plotter.update_plot([measurement, position])

        pulse_name = f"{current_time.strftime('%Y-%m-%d_%H-%M-%S-%f')}.npy"
        pulse_path = os.path.join(self.measurement_savefolder_pulses, pulse_name)
        np.save(pulse_path, measurement)
        with open(self.measurement_savepath_screen, 'a') as file:
            file.write(f"{current_time.strftime('%Y-%m-%d %H:%M:%S.%f')}_{pulse_path}_{position[0]},{position[1]},{position[2]}\n")
        return measurement

def configure_logger():
    filename_time = datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
    file_handler = logging.FileHandler(f'./logs/debug_log_{filename_time}.log')
    file_handler.setLevel(logging.DEBUG)  # Set the file handler level to capture all levels

    file_handler_warning = logging.FileHandler(f'./logs/info_log_{filename_time}.log')
    file_handler_warning.setLevel(logging.INFO)  # Set the file handler level to capture all levels

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

if __name__=="__main__":
    configure_logger()
    settings = {
        "teraflash":    {
            "toptica_IP": "192.168.1.10",
            "TFC_BEGIN": 1070,
            "TFC_AVERAGING": 10,
            "TRANSFER": "block",
            "TFC_RANGE": 100.,
            "RESOLUTION": 0.001,
        },
        "stagemover":    {
            "port": "COM4",
            "device_names": ["x", "y", "z"],
            "max_lenghts": [48, 140, 48],
            "permutation": [2, 0, 1],
        },
        "stagegridmover": {
            "x_min": None,
            "x_max": None,
            "x_n": 15,
            "y_min": None,
            "y_max": None,
            "y_max": None,
            "y_n": 15,
            "z_min": 25,
            "z_max": 25,
            "z_n": 1,
            },
        "calibration": {
            "rough_step_size": 1, #mm
            "margin": 0.6, 
            "max_deviation_from_center": 15 #mm
        },
        "general": {
            "measurement_savefolder": f"./measurements/{datetime.now().strftime('%Y-%m-%d')}",
            "measurement_name": f"{datetime.now().strftime('%H-%M-%S')}_info.txt",
            "measurement_name_screen": f"{datetime.now().strftime('%H-%M-%S')}_info_screening.txt",
        }
    }
    a = TFCCoffeeBean(settings)
    a.connect()
    a.calibrate()
    a.run_gridmover()