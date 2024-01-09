import logging
import os
from datetime import datetime

def configure_logger():
    filename_time = datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
    create_folder_if_not_exists(f'./logs')
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