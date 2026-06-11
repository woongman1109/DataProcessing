import numpy as np
import matplotlib.pyplot as plt

# Parameters provided by the user
parameters = {
    "A1": 59.52675,
    "w1": 81.20735,
    "c1": 640,
    "A2": 31.93631,
    "w2": 63.57866,
    "c2": 586,
    "A3": 25,
    "w3": 72.226,
    "c3": 542,
    "A4": 34.46771,
    "w4": 107,
    "c4": 503,
    "P": 0,
    "wp": 100,
    "cp": 850,
    "y0": 0.1465
}

# Generate individual Gaussian components
ln2 = np.log(2)
x_values = np.linspace(400, 1000, 1000)

# Calculate individual components
y0 = parameters["y0"]
gaussian1 = parameters["A1"] / (parameters["w1"] * np.sqrt(np.pi / (4 * ln2))) * np.exp(
    -4 * ln2 * (x_values - parameters["c1"]) ** 2 / parameters["w1"] ** 2
)
gaussian2 = parameters["A2"] / (parameters["w2"] * np.sqrt(np.pi / (4 * ln2))) * np.exp(
    -4 * ln2 * (x_values - parameters["c2"]) ** 2 / parameters["w2"] ** 2
)
gaussian3 = parameters["A3"] / (parameters["w3"] * np.sqrt(np.pi / (4 * ln2))) * np.exp(
    -4 * ln2 * (x_values - parameters["c3"]) ** 2 / parameters["w3"] ** 2
)
gaussian4 = parameters["A4"] / (parameters["w4"] * np.sqrt(np.pi / (4 * ln2))) * np.exp(
    -4 * ln2 * (x_values - parameters["c4"]) ** 2 / parameters["w4"] ** 2
)
polaron = -parameters["P"] / (parameters["wp"] * np.sqrt(np.pi / (4 * ln2))) * np.exp(
    -4 * ln2 * (x_values - parameters["cp"]) ** 2 / parameters["wp"] ** 2
)

# Total spectrum
total_spectrum = y0 + gaussian1 + gaussian2 + gaussian3 + gaussian4 + polaron

# Plot each Gaussian component and the total spectrum
plt.figure(figsize=(10, 6))
plt.plot(x_values, gaussian1, label="Gaussian 1 (A1)", linestyle="--")
plt.plot(x_values, gaussian2, label="Gaussian 2 (A2)", linestyle="--")
plt.plot(x_values, gaussian3, label="Gaussian 3 (A3)", linestyle="--")
plt.plot(x_values, gaussian4, label="Gaussian 4 (A4)", linestyle="--")
plt.plot(x_values, polaron, label="Polaron", linestyle="--")
plt.plot(x_values, total_spectrum, label="Total Spectrum", linewidth=2)
plt.title("Individual Gaussian Components and Total Spectrum", fontsize=16)
plt.xlabel("Wavelength (nm)", fontsize=14)
plt.ylabel("Absorption (arbitrary units)", fontsize=14)
plt.legend(fontsize=12)
plt.grid(alpha=0.3)
plt.show()