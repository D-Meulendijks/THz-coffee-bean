import matplotlib.pyplot as plt
from datetime import datetime

# File path
file_path = './measurements/2023-12-15/15-49-54.txt'  # Replace with your file path

# Lists to store x, y, and z values
x_values = []
y_values = []
z_values = []
measurements = []

try:
    # Open the file and read lines
    with open(file_path, 'r') as file:
        lines = file.readlines()

        # Extract data from each line
        for line in lines:
            parts = line.strip().split('_')
            date_str, measurement_str, pos_str = parts
            x_str, y_str, z_str = pos_str.split(',')
            # Convert date string to datetime object
            date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')
            x_values.append(float(x_str))
            y_values.append(float(y_str))
            z_values.append(float(z_str))
            measurements.append(float(measurement_str))

    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.scatter(x_values, y_values, c=measurements, cmap='viridis', label='Measurement Values')
    plt.xlabel('X Axis')
    plt.ylabel('Y Axis')
    plt.title('Measurement Values over Time')
    plt.colorbar(label='Z Values')
    plt.legend()
    plt.tight_layout()
    plt.show()

except FileNotFoundError:
    print(f"File '{file_path}' not found.")
except Exception as e:
    print(f"An error occurred: {str(e)}")