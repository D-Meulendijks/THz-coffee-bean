import sys
from PyQt5.QtCore import QThread, pyqtSignal, QObject, pyqtSlot
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QGroupBox, QLabel, QGridLayout, QVBoxLayout, QHBoxLayout, QLineEdit, QDialog
from datetime import datetime
from functools import partial
import logging

from TFCCoffeebean import TFCCoffeeBean, configure_logger

# Worker class handling device operations in a separate thread
class TFCCofffeebeanWorker(QObject):
    connected_stagemover = pyqtSignal(bool)
    connected_teraflash = pyqtSignal(bool)
    message_sent = pyqtSignal(str)

    def __init__(self, tfccoffeebean:TFCCoffeeBean):
        super().__init__()
        self.tfccoffeebean = tfccoffeebean
    
    def update_settings(self, settings:dict):
        self.tfccoffeebean.settings = settings

    def move_stagemovers_relative(self, relative_pos):
        self.tfccoffeebean.stagemover.move_all(relative_pos, mode='relative')

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
        "port": "COM12",
        "device_names": ["x", "y", "z"],
        "max_lenghts": [140, 140, 45],
        "permutation": [2, 0, 1],
    },
    "stagegridmover": {
        "x_min": None,
        "x_max": None,
        "x_n": 15,
        "y_min": None,
        "y_max": None,
        "y_n": 15,
        "z_min": 25,
        "z_max": 25,
        "z_n": 1,
        },
        "calibration": {
        "rough_step_size": 1, #mm
        "margin": 0.6, 
        "max_deviation_from_center": 30 #mm
    },
    "general": {
        "measurement_savefolder": f"./measurements/{datetime.now().strftime('%Y-%m-%d')}",
        "measurement_name": f"{datetime.now().strftime('%H-%M-%S')}.txt",
        "measurement_name_screen": f"{datetime.now().strftime('%H-%M-%S')}_screening.txt",
    }
}

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = settings
        self.TFC = TFCCoffeeBean(self.settings)
        self.TFCCofffeebeanWorker = TFCCofffeebeanWorker(self.TFC)
        self.calibration_values = QLabel("Calibration Values: Not Yet Calibrated")
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Control Panel")
        self.setGeometry(300, 200, 800, 400)


        calibration_button = QPushButton("Calibrate", self)
        calibration_button.clicked.connect(self.calibration_function)

        run_gridmover_button = QPushButton("Run Grid Mover", self)
        run_gridmover_button.clicked.connect(self.open_gridmover_window)

        settings_group_box = self.create_settings_group_box()
        manual_mover_box = self.create_manual_mover()

        main_layout = QHBoxLayout()
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.calibration_values)

        terflash_connection_layout = self.create_teraflash_connection_layout()
        button_layout.addLayout(terflash_connection_layout)

        stagemover_connection_layout = self.create_stagemover_connection_layout()
        button_layout.addLayout(stagemover_connection_layout)
        button_layout.addWidget(calibration_button)
        button_layout.addWidget(run_gridmover_button)
        main_layout.addLayout(button_layout)
        for box in settings_group_box:
            pass
            #main_layout.addWidget(box)
        main_layout.addWidget(manual_mover_box)

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


    def create_manual_mover(self):
        central_button = QPushButton("Center")
        up_button = QPushButton("Up")
        up_button.clicked.connect(partial(self.TFCCofffeebeanWorker.move_stagemovers_relative, [0, 1, 0]))
        up_button_2 = QPushButton("Up")
        down_button = QPushButton("Down")
        down_button.clicked.connect(partial(self.TFCCofffeebeanWorker.move_stagemovers_relative, [0, -1, 0]))
        down_button_2 = QPushButton("Down")
        left_button = QPushButton("Left")
        left_button.clicked.connect(partial(self.TFCCofffeebeanWorker.move_stagemovers_relative, [-1, 0, 0]))
        left_button_2 = QPushButton("Left")
        right_button = QPushButton("Right")
        right_button.clicked.connect(partial(self.TFCCofffeebeanWorker.move_stagemovers_relative, [1, 0, 0]))
        right_button_2 = QPushButton("Right")

        layout = layout = QGridLayout()
        layout.addWidget(central_button, 2, 2)
        layout.addWidget(up_button, 1, 2)
        layout.addWidget(down_button, 3, 2)
        layout.addWidget(left_button, 2, 1)
        layout.addWidget(right_button, 2, 3)
        layout.addWidget(up_button_2, 0, 2)
        layout.addWidget(down_button_2, 4, 2)
        layout.addWidget(left_button_2, 2, 0)
        layout.addWidget(right_button_2, 2, 4)

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
        self.connected_stagemover = self.TFC.connect_stagemover()
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
