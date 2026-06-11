import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.special import factorial
from scipy.optimize import least_squares

def calculate_Gm(lambda_squared, m):
    """
    Calculate Gm(lambda^2; m) for a given lambda^2 and m.
    Uses a finite sum approximation for Gm values.
    """
    Gm_value = 0
    max_n = 100  # Number of terms in the series approximation
    for n in range(max_n + 1):
        if n != m:
            term = (lambda_squared**n) / (factorial(n) * (n - m))
            Gm_value += term
    return Gm_value


def func(hw, base, W, E00, sigma, C, Epol, Cpol, sigma_pol, lambda_squared, Gm_vals):
    Ep = 0.176  # Vibrational mode energy (eV)

    mVals = np.arange(5)  # 0~4

    # Vibronic contributions
    factors = (np.exp(-lambda_squared) * lambda_squared**mVals) / np.vectorize(np.math.factorial)(mVals)
    terms = factors * (1 - (W * np.exp(-lambda_squared) / (2 * Ep)) * np.array(GmVals[1]))**2
    gaussians = np.exp(-((hw[:, None] - E00 - np.array(mVals) * Ep - 0.5 * W * lambda_squared**np.array(mVals) * np.exp(-lambda_squared))**2) / (2 * sigma**2)) \
                / (np.sqrt(2 * np.pi) * sigma)
    individual_contributions = C * terms * gaussians
    
    vibronic_contribution_Sum = np.sum(individual_contributions, axis=1)


    vibronic_contribution_Sum = np.sum(individual_contributions, axis=1)

    # Polaronic contribution
    polaronic_contribution = -Cpol * np.exp(-((hw - Epol)**2) / (2 * sigma_pol**2)) / (np.sqrt(2 * np.pi) * sigma_pol)

    # Total absorption
    total_absorption = base + vibronic_contribution_Sum + polaronic_contribution

    return total_absorption, individual_contributions, vibronic_contribution_Sum, polaronic_contribution

# Residuals function for least_squares
def residuals(params, hw, y, lambda_squared, Gm_vals):
    base, W, E00, sigma, C, Epol, Cpol, sigma_pol = params
    model = func(hw, base, W, E00, sigma, C, Epol, Cpol, sigma_pol, lambda_squared, Gm_vals)
    return model[0] - y

'''
# Get Gm values from GmVal.xlsx file

# G_m value preset
Path_GmVal = "C:/Users/woong/Dropbox/==== SKKU-SAINT ====/==== SAINT-OSL ====/3. My/Lab etc/Programming/Data Pretreatment Scripts/UV-Vis/GmVal.xlsx" 
pdArr_GmVal = pd.read_excel(Path_GmVal)
GmVals = {} # Index by the value of S, not the order
for column in pdArr_GmVal.columns[1:]:
    GmVals[column] = pdArr_GmVal[column].replace({'−': '-'}, regex=True).astype('float') # to_numpy()
'''

# Huang-Rhys factor
lambda_squared_values = [0.95, 0.96, 0.97, 0.98, 0.99, 1.00]  # Example lambda^2 values

# Calculate Gm for m = 0, 1, 2, 3, 4
m_values = range(5)
GmVals = {lambda_squared: [calculate_Gm(lambda_squared, m) for m in m_values]
          for lambda_squared in lambda_squared_values}

# Lambda^2에 대한 GmVals 출력
for lambda_squared, GmVal in GmVals.items():
    print(f"Lambda^2 = {lambda_squared}")
    for m, Gm_value in enumerate(GmVals):  # enumerate를 사용하여 m 값을 함께 가져옴
        print(f"  Gm(m={m}): {Gm_value:.4f}")


# Load data for fitting (in nm)
path_Data = "C:/Users/woong/Dropbox/==== SKKU-SAINT ====/==== SAINT-OSL ====/2. Measurements/0. Data Processing/Data Pretreatment Scripts/UV-Vis/data.xlsx"
pdArr_Data = pd.read_excel(path_Data)
x = pdArr_Data.iloc[:, 0]  # 첫 번째 열 (Wavelength)
y = pdArr_Data.iloc[:, 1]  # 두 번째 열 (Abs)
hw =  np.array(1240/x)     # Photon energy range (in eV)


# 데이터 범위 제한 (fitting 범위)
fit_Range = [1.75, 2.11]
range_mask = (hw >= fit_Range[0]) & (hw <= fit_Range[1])
hw_filtered = hw[range_mask]
y_filtered = y[range_mask]


# 초기값 및 범위 지정
# 초기값:         base,  W,       E00,         sigma,  C,  Epol, Cpol, sigma_pol
initial_guess = [0.1, 0.02, 1240 / 640.58149, 0.087, 0.42, 0.1, 1e-10, 0.1]  
bounds = ([0.0, -0.02, 1.6, 0.050, 0.2, 0.0, 0.0, 0.05], [0.13, 0.03, 2.0, 0.100, 0.6, 0.5, 1e-9, 0.2])  # 파라미터 범위

# Least squares fitting
fit_results = []
for lambda_squared in lambda_squared_values:
    result = least_squares(
        residuals,
        initial_guess,
        args=(hw_filtered, y_filtered, lambda_squared, GmVals[lambda_squared]),
        method="trf",
        ftol=1e-9,
        bounds=bounds
    )
    # 각 lambda_squared에 대한 결과 저장
    fit_results.append((lambda_squared, GmVals[lambda_squared], result))

'''
‘trf’ : Trust Region Reflective algorithm, particularly suitable for large sparse problems with bounds.
        Generally robust method.

‘dogbox’ : dogleg algorithm with rectangular trust regions, typical use case is small problems with bounds.
           Not recommended for problems with rank-deficient Jacobian.

‘lm’ : Levenberg-Marquardt algorithm as implemented in MINPACK. Doesn’t handle bounds and sparse Jacobians.
       Usually the most efficient method for small unconstrained problems.
'''

# 결과 출력
lambda_squared, Gm, result = fit_results[5]
optimized_params = result.x
print(f"Lambda^2 = {lambda_squared} | Gm: ", Gm)
print(f"  base = {optimized_params[0]:.4f}")
print(f"  W = {optimized_params[1]:.4f},    E00 = {optimized_params[2]:.4f},  sigma = {optimized_params[3]:.4f}, C = {optimized_params[4]:.4f}")
print(f"  Epol = {optimized_params[5]:.4f}, Cpol = {optimized_params[6]:.4f}, sigma_pol = {optimized_params[7]:.4f}")

fitted_curve = func(hw, *optimized_params, lambda_squared, GmVals[lambda_squared])

# 독립적인 플롯 창 생성
plt.figure(figsize=(10, 6))
plt.axvline(fit_Range[0], color='grey', linestyle='--', linewidth=1, label='LB of fit range')
plt.axvline(fit_Range[1], color='grey', linestyle='--', linewidth=1, label='UB of fit range')
plt.plot(hw, y, 'o', label='Raw Data', markersize=5)
plt.plot(hw, fitted_curve[2] + optimized_params[0], 'o', label='Vibronic Contribution', alpha=0.7, markersize=4)
plt.plot(hw, fitted_curve[3] + optimized_params[0], '^', label='Polaronic Contribution', alpha=0.7, markersize=4)
plt.plot(hw, fitted_curve[0], '-', color='black', label='Fitted Curve', linewidth=2)
for i in range(5):
    plt.plot(hw, fitted_curve[1][:, i] + optimized_params[0], '--', label=f'0-{i} Contribution', alpha=0.7)
plt.fill_between(hw, y - fitted_curve[0], 0, color='blue', alpha=0.15)
plt.title(f'Fitting for Lambda^2 = {lambda_squared}', fontsize=16)
plt.xlabel('Photon Energy (eV)', fontsize=14)
plt.ylabel('Absorption (a.u.)', fontsize=14)
plt.legend(fontsize=12)
plt.grid(alpha=0.3)
plt.show()

'''
for lambda_squared, Gm, result in fit_results:
    optimized_params = result.x
    print(f"Lambda^2 = {lambda_squared} | Gm: ", Gm)
    print(f"  base = {optimized_params[0]:.4f}")
    print(f"  W = {optimized_params[1]:.4f},    E00 = {optimized_params[2]:.4f},  sigma = {optimized_params[3]:.4f}, C = {optimized_params[4]:.4f}")
    print(f"  Epol = {optimized_params[5]:.4f}, Cpol = {optimized_params[6]:.4f}, sigma_pol = {optimized_params[7]:.4f}")

    fitted_curve = func(hw, *optimized_params, lambda_squared, GmVals[lambda_squared])

    # 독립적인 플롯 창 생성
    plt.figure(figsize=(10, 6))
    plt.axvline(fit_Range[0], color='grey', linestyle='--', linewidth=1, label='LB of fit range')
    plt.axvline(fit_Range[1], color='grey', linestyle='--', linewidth=1, label='UB of fit range')
    plt.plot(hw, y, 'o', label='Raw Data', markersize=5)
    plt.plot(hw, fitted_curve[2] + optimized_params[0], 'o', label='Vibronic Contribution', alpha=0.7, markersize=4)
    plt.plot(hw, fitted_curve[3] + optimized_params[0], '^', label='Polaronic Contribution', alpha=0.7, markersize=4)
    plt.plot(hw, fitted_curve[0], '-', color='black', label='Fitted Curve', linewidth=2)
    for i in range(5):
        plt.plot(hw, fitted_curve[1][:, i] + optimized_params[0], '--', label=f'0-{i} Contribution', alpha=0.7)
    plt.fill_between(hw, y - fitted_curve[0], 0, color='blue', alpha=0.15)
    plt.title(f'Fitting for Lambda^2 = {lambda_squared}', fontsize=16)
    plt.xlabel('Photon Energy (eV)', fontsize=14)
    plt.ylabel('Absorption (a.u.)', fontsize=14)
    plt.legend(fontsize=12)
    plt.grid(alpha=0.3)
    plt.show()
    '''

'''
  base = 0.1300
  W = 0.0271,    E00 = 1.9163,  sigma = 0.0884, C = 0.4230
  Epol = 0.1000, Cpol = 0.0000, sigma_pol = 0.1000
'''