from datetime import datetime

def get_settings():
    settings = {
        "teraflash": {
            "toptica_IP": "169.254.132.84",
            "TFC_BEGIN": 2280,
            "TFC_AVERAGING": 1,
            "TRANSFER": "block",
            "TFC_RANGE": 200.,
            "RESOLUTION": 0.001,
        },
        "stagemover": {
            "port": "COM4",
            "device_names": ["x", "y", "z"],
            "max_lenghts": [148, 48, 48],
            "permutation": [1, 0, 2],
        },
        "stagegridmover": {
            "x_min": 92.0,
            "x_max": 94.8,
            "x_n": 5,
            "y_min": 33.8,
            "y_max": 33.8,
            "y_n": 1,
            "z_min": 0.5,
            "z_max": 47.5,
            "z_n": 100,
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

