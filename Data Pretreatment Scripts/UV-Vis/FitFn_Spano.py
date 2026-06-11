# mypyfit.py
import numpy as np
from scipy.special import factorial
from scipy.optimize import least_squares
from scipy.integrate import simpson

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


def func(hw, base, W, C, E00, sigma, Cpol, Epol, sigma_pol, lambda_squared, Gm_vals):
    """
    모델 함수값을 계산하는 함수.
    hw: photon energy array
    기타 파라미터들은 fitting 변수
    """
    Ep = 0.174  # Vibrational mode energy (eV)
    mVals = np.arange(5)  # 0~4 진동 모드
    factors = (np.exp(-lambda_squared) * lambda_squared**mVals) / np.vectorize(np.math.factorial)(mVals)
    terms = factors * (1 - (W * np.exp(-lambda_squared) / (2 * Ep)) * np.array(Gm_vals))**2

    # Vibronic contribution 계산
    gaussians = np.exp(
        -((hw[:, None] - E00 - np.array(mVals) * Ep - 0.5 * W * lambda_squared**np.array(mVals) * np.exp(-lambda_squared))**2) 
        / (2 * sigma**2)
    ) / (np.sqrt(2 * np.pi) * sigma)

    individual_contributions = base + C * terms * gaussians
    vibronic_contribution_Sum = np.sum(individual_contributions, axis=1) - base * (len(mVals) - 1)

    # Polaronic contribution 계산
    polaronic_contribution = base - Cpol * np.exp(
        -((hw - Epol)**2) / (2 * sigma_pol**2)
    ) / (np.sqrt(2 * np.pi) * sigma_pol)

    # Total absorption
    total_absorption = - base + vibronic_contribution_Sum + polaronic_contribution
    return total_absorption, individual_contributions, vibronic_contribution_Sum, polaronic_contribution


def residuals(params, hw, y, lambda_squared, Gm_vals):
    """
    least_squares에 들어가는 residual 함수
    """
    base, W, C, E00, sigma, Cpol, Epol, sigma_pol = params
    model = func(hw, base, W, C, E00, sigma, Cpol, Epol, sigma_pol, lambda_squared, Gm_vals)
    return model[0] - y


def get_singleFit_params(result_set, label, lsq):
    """
    개별 label, Huang-Rhys factor(lambda^2)에 따른 최적화 파라미터 추출
    """
    __result_info = result_set[label][lsq]
    __result = __result_info.get('result')
    if __result is not None and __result_info.get('success'):
        optimized_params = __result.x
    else:
        optimized_params = __result_info.get('x', None)
    Gm_for_this = __result_info.get('GmVals', None)
    return optimized_params, Gm_for_this


def perform_fitting(
    data_dict,          # {column_name: Series 형태의 y 데이터}
    hw,                 # 전체 x축 (Photon energy)
    fit_range_masks,    # {column_name: boolean mask array}
    ig_values,          # {column_name: 초기 guess array}
    GmVals,             # {lambda^2: Gm array}
    lambda_squared_values, # 리스트 형태
    bounds              # {column_name: (lb_array, ub_array)}
):
    """
    data_dict에 대해 반복적으로 fitting 수행 후, 결과를 반환.
    """
    fit_results = {}
    for name, y in data_dict.items():
        print("Now start fitting for:", name)
        fit_result_forEach = {}

        # 범위 필터링
        hw_filtered = hw[fit_range_masks[name]]
        y_filtered = y[fit_range_masks[name]]

        for lambda_squared in lambda_squared_values:
            try:
                result = least_squares(
                    residuals,
                    ig_values[name],  # initial guess for this Name
                    args=(hw_filtered, y_filtered, lambda_squared, GmVals[lambda_squared]),
                    method="trf",
                    ftol=1e-9,
                    bounds=bounds[name]
                )

                fit_result_forEach[lambda_squared] = {
                    'lambda_squared': lambda_squared,
                    'GmVals': GmVals[lambda_squared],
                    'result': result,
                    'success': result.success,
                    'message': result.message,
                    'nfev': result.nfev,
                    'cost': result.cost,
                    'optimality': result.optimality,
                    'jac': result.jac
                }
                print(f"Fitting completed for {name}, Huang-Rhys factor = {lambda_squared}")

            except Exception as fit_e:
                print(f"Fitting failed for {name}, Huang-Rhys factor = {lambda_squared}: {fit_e}")
                # 실패 시 initial guess를 파라미터로 사용하여 결과 저장
                fit_result_forEach[lambda_squared] = {
                    'lambda_squared': lambda_squared,
                    'GmVals': GmVals[lambda_squared],
                    'result': None,
                    'x': ig_values[name],  # initial guess 사용
                    'success': False,
                    'message': f"Fitting failed, used initial guess. {fit_e}",
                    'nfev': 0,
                    'cost': None,
                    'optimality': None,
                    'jac': None
                }

        fit_results[name] = fit_result_forEach
    
    return fit_results
