from stagemovers import StageMover, StageGridMover, StageCalibrator
import logging
from datetime import datetime
import os
from fakeenvironment import FakeTFC
import numpy as np
import matplotlib.pyplot as plt
from settings import get_settings
from logger_settings import configure_logger, create_folder_if_not_exists

# Dependencies for Teraflash
import sys
sys.path.append("C:\\terasoft\\")
from Devices.Data.ReadWriteData import Data
from Devices.TeraFlashClient import TeraFlashClient, State
import threading
from Devices.TeraFlashClient.Pulse import TFPulse

PLOT_MAXIMUM_ENERGY = 6000
PLOT_MINIMUM_ENERGY = 0


class TFC(TeraFlashClient):
    def __init__(self, teraflash_settings):
        super().__init__(teraflash_settings["toptica_IP"])
        self.teraflash_settings = teraflash_settings

    def connect_teraflash(self):
        logging.info(f"Connecting...")
        connection_result = self.connect()
        logging.info(f"Connected")
        return connection_result

    def start_laser(self):
        self.set_averaging(self.teraflash_settings["TFC_AVERAGING"])
        if self.teraflash_settings["TRANSFER"] == "block":
            self.set_block_transfer()
        else:
            self.set_sliding_transfer()
        self.set_begin(self.teraflash_settings["TFC_BEGIN"])
        self.set_range(self.teraflash_settings["TFC_RANGE"])
        self.start(wait=True)
        logging.info("Connected and started the laser")

    def get_corrected_pulse(self):
        pulse = self.get_next_trace()
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
        self.values.append([new_values[0], new_values[1]])
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
        self.teraflash = TFC(self.settings["teraflash"])
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
        self.current_trace = None

    def save_pulse(self, pulse):
        file_name = "C:\\Users\\20192137\\Documents\\THz-coffee-bean\\measurements\\pulses"
        dat = Data(pulse=pulse)
        dat.save(file_name)
        logging.info(f'pulse saved to: {dat.filename}')


    def measurement_thread(self):
        self.stopped = False
        while not self.stopped:
            if self.teraflash.running():
                self.current_trace = self.teraflash.get_corrected_pulse()


    def connect_teraflash(self):
        try:
            connection_info = self.teraflash.connect_teraflash()
            self.teraflash.start_laser()
            logging.debug(f"Teraflash connection info: \n {connection_info}")
            logging.debug(f"Starting measurement thread")
            measure_thread = threading.Thread(target=self.measurement_thread)
            measure_thread.daemon = True
            measure_thread.start()
            logging.debug(f"Thread started")
            return True
        except:
            return False
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
        self.settings["stagegridmover"]["x_n"] = 25
        self.settings["stagegridmover"]["y_n"] = 25
        self.plotter = MeasurementPlotter(self.settings)
        self.plotter.create_plot()
        logging.info(f"Starting gridmove")
        self.stagegridmover = StageGridMover(self.stagemover, self.settings["stagegridmover"])
        self.stagegridmover.run_grid(self.measure_and_log)
        
        plt.ioff()  # Turn off interactive mode to keep the plot open after the program finishes
        plt.show()

    def measure_and_log(self, position):
        pulse = self.teraflash.get_corrected_pulse()
        self.save_pulse(pulse)
        self.plotter.update_plot([pulse.energy(), position])
        # current_time = datetime.now()

        # pulse_name = f"{current_time.strftime('%Y-%m-%d_%H-%M-%S-%f')}.npy"
        # pulse_path = os.path.join(self.measurement_savefolder_pulses, pulse_name)
        # np.save(pulse_path, measurement)
        # with open(self.measurement_savepath, 'a') as file:
        #     file.write(f"{current_time.strftime('%Y-%m-%d %H:%M:%S.%f')}_{pulse_path}_{position[0]},{position[1]},{position[2]}\n")
        return pulse

    def measure_and_log_screen(self, position):
        pulse = self.teraflash.get_corrected_pulse()
        self.save_pulse(pulse)
        self.plotter.update_plot([pulse.energy(), position])
        # current_time = datetime.now()
        # pulse_name = f"{current_time.strftime('%Y-%m-%d_%H-%M-%S-%f')}.npy"
        # pulse_path = os.path.join(self.measurement_savefolder_pulses, pulse_name)
        # np.save(pulse_path, measurement)
        # with open(self.measurement_savepath_screen, 'a') as file:
        #     file.write(f"{current_time.strftime('%Y-%m-%d %H:%M:%S.%f')}_{pulse_path}_{position[0]},{position[1]},{position[2]}\n")
        return pulse



if __name__=="__main__":
    configure_logger()
    settings = get_settings()
    a = TFCCoffeeBean(settings)
    a.connect_teraflash()
    a.connect_stagemover()
    a.calibrate()
    a.run_gridmover()