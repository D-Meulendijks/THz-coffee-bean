import sys
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QThread, pyqtSignal, QObject, pyqtSlot
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QGroupBox, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QLineEdit, QDialog, QSpinBox, QDoubleSpinBox
from datetime import datetime
from functools import partial
import logging

from settings import get_settings
from logger_settings import configure_logger, create_folder_if_not_exists
from TFCCoffeebean import TFCCoffeeBean
from Devices.TeraFlashClient.Pulse import TFPulse
from guiqwt.curve import CurvePlot
from guiqwt.builder import make
from qwt import QwtPlot
import threading
import time

# Worker class handling device operations in a separate thread
class TFCCofffeebeanWorker(QObject):
    connected_stagemover = pyqtSignal(bool)
    connected_teraflash = pyqtSignal(bool)
    trace = pyqtSignal(TFPulse)
    updated_position = pyqtSignal(list)
    message_sent = pyqtSignal(str)

    def __init__(self, tfccoffeebean:TFCCoffeeBean):
        super().__init__()
        self.tfccoffeebean = tfccoffeebean

    def update_settings(self, settings:dict):
        self.tfccoffeebean.settings = settings

    @pyqtSlot()
    def move_stagemovers_relative(self, relative_pos):
        try:
            position = self.tfccoffeebean.stagemover.move_all(relative_pos, mode='relative')
            self.updated_position.emit(position)
        except Exception as e:
            logging.warning(f"Error moving stage: {e}")

    def start_continous_measurement_collector_thread(self):
        measure_thread = threading.Thread(target=self.continous_measurement_collector)
        measure_thread.daemon = True
        measure_thread.start()

    @pyqtSlot()
    def continous_measurement_collector(self):
        self.stopped = False
        while not self.stopped:
            try:
                self.current_pulse = self.tfccoffeebean.teraflash.get_corrected_pulse()
                self.trace.emit(self.current_pulse)
            except Exception as e:
                logging.warning(f"Error making THz measurement: {e}")
            time.sleep(0.05)

    @pyqtSlot()
    def measure_trace(self):
        try:
            self.tfccoffeebean.save_pulse(self.current_pulse)
        except Exception as e:
            logging.warning(f"Error saving THz measurement: {e}")

    @pyqtSlot()
    def home(self):
        try:
            self.tfccoffeebean.stagemover.home()
            self.updated_position.emit([0, 0, 0])
        except Exception as e:
            logging.warning(f"Error homing: {e}")

    @pyqtSlot()
    def connect_stagemover(self):
        connection_status = self.tfccoffeebean.connect_stagemover()
        self.connected_stagemover.emit(connection_status)

    @pyqtSlot()
    def connect_teraflash(self):
        connection_status = self.tfccoffeebean.connect_teraflash()
        self.connected_teraflash.emit(connection_status)

    @pyqtSlot(str)
    def send_message(self, position):
        response = self.device.send_message(position)
        self.message_sent.emit(response)

# Your settings dictionary
settings = get_settings()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = settings
        self.TFC = TFCCoffeeBean(self.settings)
        self.TFCCofffeebeanWorker = TFCCofffeebeanWorker(self.TFC)
        self.calibration_values = QLabel("Calibration Values: Not Yet Calibrated")
        self.step_size = 1
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Control Panel")
        self.setGeometry(300, 200, 800, 400)


        calibration_button = QPushButton("Calibrate", self)
        calibration_button.clicked.connect(self.calibration_function)
        calibration_button.setFixedSize(100, 30)

        run_gridmover_button = QPushButton("Run Grid Mover", self)
        run_gridmover_button.clicked.connect(self.open_gridmover_window)
        run_gridmover_button.setFixedSize(100, 30)

        settings_group_box = self.create_settings_group_box()
        manual_mover_box = self.create_manual_mover()
        manual_measurer_box = self.create_manual_measurer()

        main_layout = QHBoxLayout()
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.calibration_values)

        terflash_connection_layout = self.create_teraflash_connection_layout()
        button_layout.addLayout(terflash_connection_layout)

        stagemover_connection_layout = self.create_stagemover_connection_layout()
        button_layout.addLayout(stagemover_connection_layout)
        button_layout.addWidget(calibration_button)
        button_layout.addWidget(run_gridmover_button)
        button_layout.addWidget(manual_mover_box)
        main_layout.addLayout(button_layout, 1)
        for box in settings_group_box:
            pass
            #main_layout.addWidget(box)
        #main_layout.addWidget(manual_mover_box)
        main_layout.addWidget(manual_measurer_box, 2)

        self.setLayout(main_layout)
        self.show()



    def create_teraflash_connection_layout(self):
        self.connection_status_teraflash = QLabel("Teraflash: Not Connected")
        self.connection_status_teraflash.setFixedSize(150, 30)
        self.connect_teraflash_button = QPushButton("Connect", self)
        self.connect_teraflash_button.clicked.connect(self.connect_teraflash)
        ip_label = QLabel("IP:")
        ip_entry = QLineEdit(str(settings['teraflash']['toptica_IP']))
        ip_entry.setFixedSize(100, 30)
        ip_entry.textChanged.connect(self.update_toptica_ip)
        layout = QHBoxLayout()
        layout.addWidget(self.connection_status_teraflash)
        layout.addWidget(self.connect_teraflash_button)
        layout.addWidget(ip_label)
        layout.addWidget(ip_entry)
        return layout

    def update_toptica_ip(self, text):
        self.settings['teraflash']['toptica_IP'] = text
        self.TFCCofffeebeanWorker.update_settings(self.settings)
        logging.debug(self.settings)

    def create_stagemover_connection_layout(self):
        self.connection_status_stagemover = QLabel("Stages: Not Connected")
        self.connection_status_stagemover.setFixedSize(150, 30)
        self.connect_stagemover_button = QPushButton("Connect", self)
        self.connect_stagemover_button.clicked.connect(self.connect_stagemover)
        com_label = QLabel("COM:")
        port_entry = QLineEdit(str(settings['stagemover']['port']))
        port_entry.setFixedSize(100, 30)
        port_entry.textChanged.connect(self.update_stagemover_port)
        layout = QHBoxLayout()
        layout.addWidget(self.connection_status_stagemover)
        layout.addWidget(self.connect_stagemover_button)
        layout.addWidget(com_label)
        layout.addWidget(port_entry)
        return layout

    def update_stagemover_port(self, text):
        self.settings['stagemover']['port'] = text
        self.TFCCofffeebeanWorker.update_settings(self.settings)
        logging.debug(self.settings)

    def create_settings_group_box(self):
        settings_group_box = []
        #settings_group_box = QGroupBox("Settings")

        for category, values in settings.items():
            layout = QVBoxLayout()
            settings_group_box.append(QGroupBox(f"{category.capitalize()}"))
            #layout.addWidget(QLabel(category.capitalize() + ":"))
            for key, value in values.items():
                setting_line = QHBoxLayout()
                setting_line.addWidget(QLabel(key.replace('_', ' ').capitalize() + ":"))
                line_edit = QLineEdit(str(value))
                setting_line.addWidget(line_edit)
                layout.addLayout(setting_line)

            settings_group_box[-1].setLayout(layout)
        return settings_group_box


    def set_position_label(self, position):
        try:
            self.pos_label.setText(f"x: {position[0]:.2f}, y: {position[1]:.2f}, z: {position[2]:.2f}")
        except Exception as e:
            logging.warning(f"Cannot set position label: {e}")

    def move_stages(self, direction):
        relative_position = [self.step_size*v for v in direction]
        self.TFCCofffeebeanWorker.move_stagemovers_relative(relative_position)


    def set_step_size(self, size):
        try:
            float_size = float(size)
            self.step_size = float_size
            logging.info(f"Step size set to: {size}")
        except Exception as e:
            logging.warning(f"Step size ({size}) not convertable to float, leaving it as {self.step_size}.")

    def update_plot(self, updated_trace):
        self.curve_time.set_data(updated_trace.t(), updated_trace.E())
        self.plot_time.replot()
        self.curve_freq.set_data(updated_trace.f(), updated_trace.S())
        self.plot_freq.replot()

        pp_trace = updated_trace.E().max() - updated_trace.E().min()
        energy_trace = updated_trace.energy()
        pp_str = '%.2f' % pp_trace
        energy_str = '%.2f' % energy_trace
        self.peakpeak.set_text('%-20s %s<br>%-20s        %s' % \
                               ('peak-peak (nA):', pp_str, \
                                'energy:', energy_str))

    def autoscale(self):
        self.plot_time.do_autoscale(replot=False)
        self.plot_freq.do_autoscale(replot=False)

    def update_averaging(self, newvalue):
        try:
            int_newvalue = int(newvalue)
            self.TFCCofffeebeanWorker.tfccoffeebean.teraflash.set_averaging(int_newvalue)
        except:
            logging.warning(f"Error updating averaging value, {newvalue} is not an integer")

    def create_manual_measurer(self):
        measure_button = QPushButton("Save Trace")
        measure_button.clicked.connect(self.TFCCofffeebeanWorker.measure_trace)
        autoscale_button = QPushButton("Adjust scale")
        autoscale_button.clicked.connect(self.autoscale)
        averaging_entry = QSpinBox()
        averaging_entry.setValue(self.TFCCofffeebeanWorker.tfccoffeebean.teraflash.averaging)
        averaging_entry.setMinimum(1)
        averaging_entry.textChanged.connect(self.update_averaging)

        spinBoxBegin = QDoubleSpinBox()
        spinBoxBegin.setAccelerated(False)
        spinBoxBegin.setMaximum(3000)
        spinBoxBegin.setSingleStep(50)
        spinBoxBegin.setValue(self.TFCCofffeebeanWorker.tfccoffeebean.teraflash.begin)
        spinBoxBegin.setObjectName("spinBoxBegin")

        spinBoxRange = QDoubleSpinBox()
        spinBoxRange.setMinimum(20)
        spinBoxRange.setMaximum(200)
        spinBoxRange.setSingleStep(10)
        spinBoxRange.setValue(self.TFCCofffeebeanWorker.tfccoffeebean.teraflash.range)
        spinBoxRange.setObjectName("spinBoxRange")


        self.TFCCofffeebeanWorker.trace.connect(lambda trace: self.update_plot(trace))

        self.plot_time = CurvePlot()
        self.curve_time = make.curve([], [], color='b', title='pulse')
        self.plot_time.add_item(self.curve_time)
        self.plot_time.setAxisTitle(QwtPlot.yLeft, 'Electric field (a.u.)')
        self.plot_time.setAxisTitle(QwtPlot.xBottom, 'time (ps)')


        self.peakpeak = make.label("", "TR", (-10, 10), "TR")
        self.peakpeak.set_text_style(QFont('Lucida Console', 14))
        self.plot_time.add_item(self.peakpeak)

        self.plot_freq = CurvePlot()
        self.curve_freq = make.curve([], [], color='b', title='spectrum')
        self.plot_freq.add_item(self.curve_freq)
        self.plot_freq.setAxisTitle(QwtPlot.yLeft, 'Power spectrum (a.u.)')
        self.plot_freq.setAxisTitle(QwtPlot.xBottom, 'frequency (THz)')

        layout = QGridLayout()
        buttons = QGridLayout()
        buttons.addWidget(measure_button, 0, 0)
        buttons.addWidget(autoscale_button, 0, 1)
        buttons.addWidget(QLabel("Averaging:"), 0, 2)
        buttons.addWidget(averaging_entry, 0, 3)
        buttons.addWidget(QLabel("Begin:"), 1, 0)
        buttons.addWidget(spinBoxBegin, 1, 1)
        buttons.addWidget(QLabel("Range:"), 1, 2)
        buttons.addWidget(spinBoxRange, 1, 3)
        layout.addLayout(buttons, 0, 0)
        layout.addWidget(self.plot_time, 1, 0)
        layout.addWidget(self.plot_freq, 2, 0)
        widget = QGroupBox(f"Measurement section")
        widget.setLayout(layout)
        return widget

    def create_manual_mover(self):
        button_size = (100, 100)
        central_button = QPushButton("Center")
        central_button.setFixedSize(*button_size)
        central_button.clicked.connect(self.TFCCofffeebeanWorker.home)
        ypos_button = QPushButton("Y+")
        ypos_button.setFixedSize(*button_size)
        ypos_button.clicked.connect(partial(self.move_stages, [0, -1, 0]))
        yneg_button = QPushButton("Y-")
        yneg_button.setFixedSize(*button_size)
        yneg_button.clicked.connect(partial(self.move_stages, [0, 1, 0]))

        xneg_button = QPushButton("X-")
        xneg_button.setFixedSize(*button_size)
        xneg_button.clicked.connect(partial(self.move_stages, [-1, 0, 0]))
        xpos_button = QPushButton("X+")
        xpos_button.setFixedSize(*button_size)
        xpos_button.clicked.connect(partial(self.move_stages, [1, 0, 0]))

        zneg_button = QPushButton("Z-")
        zneg_button.setFixedSize(*button_size)
        zneg_button.clicked.connect(partial(self.move_stages, [0, 0, -1]))
        zpos_button = QPushButton("Z+")
        zpos_button.setFixedSize(*button_size)
        zpos_button.clicked.connect(partial(self.move_stages, [0, 0, 1]))

        self.pos_label = QLabel("x: 0.0, y: 0.0, z: 0.0")
        self.TFCCofffeebeanWorker.updated_position.connect(self.set_position_label)
        step_size_label = QLabel("set_step_size")
        step_size_edit = QLineEdit(str(self.step_size))
        step_size_edit.setFixedSize(100, 30)
        step_size_edit.textChanged.connect(self.set_step_size)

        layout = QVBoxLayout()

        movement_buttons = QHBoxLayout()
        cross_buttons = QGridLayout()
        cross_buttons.addWidget(central_button, 2, 2)
        cross_buttons.addWidget(ypos_button, 1, 2)
        cross_buttons.addWidget(yneg_button, 3, 2)
        cross_buttons.addWidget(xneg_button, 2, 1)
        cross_buttons.addWidget(xpos_button, 2, 3)
        movement_buttons.addLayout(cross_buttons)

        z_buttons = QVBoxLayout()

        z_buttons.addWidget(zpos_button, 0)
        z_buttons.addWidget(zneg_button, 1)
        movement_buttons.addLayout(z_buttons)

        layout.addLayout(movement_buttons)


        manual_mover_settings_buttons = QHBoxLayout()
        manual_mover_settings_buttons.addWidget(step_size_label)
        manual_mover_settings_buttons.addWidget(step_size_edit)
        manual_mover_settings_buttons.addWidget(self.pos_label)
        layout.addLayout(manual_mover_settings_buttons)

        widget = QGroupBox(f"Manual mover")
        widget.setLayout(layout)
        return widget

    def connect_teraflash(self):
        self.connection_status_teraflash.setText("Teraflash: Connecting...")
        self.connection_status_teraflash.setStyleSheet("color: gray")
        QApplication.processEvents()
        logging.info(f"Connecting to teraflash at {settings['teraflash']['toptica_IP']}...")
        self.TFCCofffeebeanWorker.connected_teraflash.connect(lambda status: self.update_teraflash_status(status))
        self.TFCCofffeebeanWorker.connect_teraflash()
        self.TFCCofffeebeanWorker.start_continous_measurement_collector_thread()

    def update_teraflash_status(self, status):
        self.connected_teraflash = status
        logging.info(f"Connection teraflash: {self.connected_teraflash}")
        if self.connected_teraflash:
            self.connection_status_teraflash.setText("Teraflash: Connected")
            self.connection_status_teraflash.setStyleSheet("color: green")
        else:
            self.connection_status_teraflash.setText(f"Teraflash: Not connected")
            self.connection_status_teraflash.setStyleSheet("color: red")

    def connect_stagemover(self):
        self.connection_status_stagemover.setText("Stages: Connecting...")
        self.connection_status_stagemover.setStyleSheet("color: gray")
        QApplication.processEvents()
        logging.info(f"Connecting to linear stages at {self.settings['stagemover']['port']}...")
        self.TFCCofffeebeanWorker.connected_stagemover.connect(lambda status: self.update_stagemover_status(status))
        self.TFCCofffeebeanWorker.connect_stagemover()

    def update_stagemover_status(self, status):
        self.connected_stagemover = status
        logging.info(f"Connection linear stages: {self.connected_stagemover}")
        if self.connected_stagemover:
            self.connection_status_stagemover.setText(f"Stages: Connected")
            self.connection_status_stagemover.setStyleSheet("color: green")
        else:
            self.connection_status_stagemover.setText(f"Stages: Not connected")
            self.connection_status_stagemover.setStyleSheet("color: red")

    def calibration_function(self):
        calibration_result = self.TFC.calibrate()
        self.calibration_values.setText(f"Calibration Values: {calibration_result}")

    def open_gridmover_window(self):
        self.TFC.run_gridmover()





class GridMoverWindow(QDialog):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Grid Mover")
        self.setGeometry(300, 200, 300, 200)
        # Add functionality and widgets for grid mover window as needed


class SettingsWindow(QDialog):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Settings")
        self.setGeometry(300, 200, 400, 300)

        # Create QLineEdit fields for each setting that needs to be editable
        # Populate QLineEdit fields with existing settings values

        vbox = QVBoxLayout()
        # Add QLineEdit fields and labels for settings here
        # Example:
        # line_edit = QLineEdit(self)
        # line_edit.setText(str(self.settings['teraflash']['toptica_IP']))
        # vbox.addWidget(QLabel("Toptica IP"))
        # vbox.addWidget(line_edit)

        self.setLayout(vbox)
        self.show()


def main():
    configure_logger()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
