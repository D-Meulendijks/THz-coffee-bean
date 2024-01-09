from datetime import datetime

def get_settings():
    settings = {
        "teraflash": {
            "toptica_IP": "169.254.132.84",
            "TFC_BEGIN": 1070,
            "TFC_AVERAGING": 10,
            "TRANSFER": "block",
            "TFC_RANGE": 100.,
            "RESOLUTION": 0.001,
        },
        "stagemover": {
            "port": "COM4",
            "device_names": ["x", "y", "z"],
            "max_lenghts": [48, 150, 48],
            "permutation": [1, 0, 2],
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
            "rough_step_size": 1,  # mm
            "margin": 0.6,
            "max_deviation_from_center": 15  # mm
        },
        "general": {
            "measurement_savefolder": f"./measurements/{datetime.now().strftime('%Y-%m-%d')}",
            "measurement_name": f"{datetime.now().strftime('%H-%M-%S')}_info.txt",
            "measurement_name_screen": f"{datetime.now().strftime('%H-%M-%S')}_info_screening.txt",
        }
    }
    return settings

