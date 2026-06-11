import originpro as op
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.special import factorial
from scipy.optimize import least_squares

def open_Project(path):
    project_path = path  # Origin 파일 경로
    op.open(project_path)  # Origin 파일 열기
    return

def gen_SheetName(BName, SName):
    return '[' + BName + ']' +  SName

def getWorkSheet(__BName, __SName):
    __wksName = gen_SheetName(__BName, __SName)
    return app.find_sheet(type='w',ref=__wksName)

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
    Ep = 0.176  # Vibrational mode energy (eV)

    mVals = np.arange(5)  # 0~4

    # Vibronic contributions
    factors = (np.exp(-lambda_squared) * lambda_squared**mVals) / np.vectorize(np.math.factorial)(mVals)
    terms = factors * (1 - (W * np.exp(-lambda_squared) / (2 * Ep)) * np.array(Gm_vals))**2
    gaussians = np.exp(-((hw[:, None] - E00 - np.array(mVals) * Ep - 0.5 * W * lambda_squared**np.array(mVals) * np.exp(-lambda_squared))**2) / (2 * sigma**2)) \
                / (np.sqrt(2 * np.pi) * sigma)
    individual_contributions = C * terms * gaussians
    
    vibronic_contribution_Sum = np.sum(individual_contributions, axis=1)

    # Polaronic contribution
    polaronic_contribution = -Cpol * np.exp(-((hw - Epol)**2) / (2 * sigma_pol**2)) / (np.sqrt(2 * np.pi) * sigma_pol)

    # Total absorption
    total_absorption = base + vibronic_contribution_Sum + polaronic_contribution

    return total_absorption, individual_contributions, vibronic_contribution_Sum, polaronic_contribution

# Residuals function for least_squares
def residuals(params, hw, y, lambda_squared, Gm_vals):
    base, W, C, E00, sigma, Cpol, Epol, sigma_pol,  = params
    model = func(hw, base, W, C, E00, sigma, Cpol, Epol, sigma_pol, lambda_squared, Gm_vals)
    return model[0] - y

# .replace({'−': '-'}, regex=True).astype('float')
# GmVals[column] = pdArr_GmVal[column].replace({'−': '-'}, regex=True).astype('float') # to_numpy()


def originTransfer(__range_lb, __range_ub, __nPoints, __reportWBook, __SName, base, W, C, E00, sigma, Cpol, Epol, sigma_pol, lambda_squared, Gm_vals):
    # 예를 들어, fitting이 완료되어 'optimized_params', 'Gm_for_this', 그리고 'func'가 준비되어 있다고 가정
    # 또한 target_lambda_squared, base, W, C, E00, sigma, Cpol, Epol, sigma_pol 값도 얻었다고 가정
    # fitting 결과로부터 최적화 파라미터를 얻었다고 할 때:
    # optimized_params = [base, W, C, E00, sigma, Cpol, Epol, sigma_pol]

    # x-axis range of the plot
    hw_array = np.linspace(__range_lb, __range_ub, __nPoints)

    # func 함수 호출을 통해 해당 구간에 대해 fitted curve 계산
    base, W, C, E00, sigma, Cpol, Epol, sigma_pol = optimized_params
    total_absorption, individual_contributions, vibronic_contribution_Sum, polaronic_contribution = func(hw_array, base, W, C, E00, sigma, Cpol, Epol, sigma_pol, lambda_squared, Gm_vals)

    df_curve = pd.DataFrame({
        'PhotonEnergy(eV)': hw_array,
        'FittedAbsorption': total_absorption,
        'vibronic_contribution_Sum': vibronic_contribution_Sum,
        'polaronic_contribution': polaronic_contribution
    })

    for j in range(individual_contributions.shape[1]):  # 예: j=0~4
        df_curve[f'A\-(0-{j})'] = individual_contributions[:, j]
    
    book = __reportWBook
    wks_1 = book.add_sheet()
    wks_1.name = __SName
    wks_1.from_df(df_curve)

    return

# .replace({'−': '-'}, regex=True).astype('float')
# GmVals[column] = pdArr_GmVal[column].replace({'−': '-'}, regex=True).astype('float') # to_numpy()


try:
    # Open Origin project file
    app = op.project
    opj_path = r"C:\Users\woong\Dropbox\==== SKKU-SAINT ====\==== SAINT-OSL ====\1. Research tmp\2024_Operando GIWAXS\Operando GIWAXS_Other data.opju"
    app.open(opj_path)

    # Huang-Rhys factor used for fitting
    lambda_wb_ref = "lambdaSheet"
    lambda_ws_ref = "Huang-Rhys factor"
    wks_lambda = getWorkSheet(lambda_wb_ref, lambda_ws_ref)
    lambda_squared_values = [float(comments) for comments in wks_lambda.get_labels('C')[1:]]
    # print([float(comments) for comments in wks_lambda.get_labels('C')[1:]])

    # Calculate Gm for m = 0, 1, 2, 3, 4
    m_values = wks_lambda.to_df(c1=0, numcols=1).iloc[:,0]
    GmVals = {lambda_squared: [calculate_Gm(lambda_squared, m) for m in m_values]
            for lambda_squared in lambda_squared_values}

    '''
    # Lambda^2에 대한 GmVals 출력
    for lambda_squared, __Corr_Gm_array in GmVals.items():
        print(f"Lambda^2 = {lambda_squared}")
        for m, __Corr_Gm_val in enumerate(__Corr_Gm_array):  # enumerate를 사용하여 m 값을 함께 가져옴
            print(f"  Gm(m={m}): {__Corr_Gm_val:.4f}")
    '''

    ##================================================================================================================================================

    # Get data for fitting (in [nm])
    data_wb_ref = "Book10"
    data_ws_ref = "MC"
    wks = getWorkSheet(data_wb_ref, data_ws_ref) # Worksheet 객체 반환
    df = wks.to_df()

    # Get X-axis values
    x = df.iloc[:,0]
    hw =  np.array(1240/x)     # Photon energy range (in eV)

    # Get Y-axis values
    dataList_Name_fromLName = [LName for LName in wks.get_labels()[1:wks.cols]]
    dataList_Data = df.iloc[:,1:wks.cols]

    print("=================Data Transferred Successfully=================")
    ##================================================================================================================================================

    # Initial guesses for fitting
    ig_wb_ref = data_wb_ref
    ig_ws_ref = dataList_Name_fromLName
    wksArr_ig = [getWorkSheet(ig_wb_ref, __wksName_ig) for __wksName_ig in ig_ws_ref]


    # 데이터 범위 제한 (fitting 범위)
    fit_Range_masks = {}
    ig_values = {}
    bounds = {}
    fit_Ranges = {}

    for __wks_ig in wksArr_ig:
        __ig_key = __wks_ig.get_str('name')
        fit_Range_masks[__ig_key] = (hw >= float(__wks_ig.get_labels('C')[1])) & (hw <= float(__wks_ig.get_labels('C')[3]))
        fit_Ranges[__ig_key] = [float(__wks_ig.get_labels('C')[1]), float(__wks_ig.get_labels('C')[3])]

        __lb = __wks_ig.to_df().iloc[:,1]
        __ig_val = __wks_ig.to_df().iloc[:,2]
        __ub = __wks_ig.to_df().iloc[:,3]
        ig_values[__ig_key] = __ig_val
        bounds[__ig_key] = (__lb, __ub)

    print("=================Parameters Transferred Successfully=================")
    ##================================================================================================================================================

    # Least squares fitting
    fit_results = {}

    for __Name, y in dataList_Data.items():
        print("Now start fitting for:", __Name)
        fit_result_forEach = {}

        # 범위 필터링
        hw_filtered = hw[fit_Range_masks[__Name]]
        y_filtered = y[fit_Range_masks[__Name]]

        for lambda_squared in lambda_squared_values:
            try:
                result = least_squares(
                    residuals,
                    ig_values[__Name],  # initial guess for this Name
                    args=(hw_filtered, y_filtered, lambda_squared, GmVals[lambda_squared]),
                    method="trf",
                    ftol=1e-9,
                    bounds=bounds[__Name]
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

                print(f"Fitting completed for {__Name}, Huang-Rhys factor = {lambda_squared}")

            except Exception as fit_e:
                print(f"Fitting failed for {__Name}, Huang-Rhys factor = {lambda_squared}: {fit_e}")
                # 실패 시 initial guess를 파라미터로 사용하여 결과 저장
                fit_result_forEach[lambda_squared] = {
                    'lambda_squared': lambda_squared,
                    'GmVals': GmVals[lambda_squared],
                    'result': None,
                    'x': ig_values[__Name],  # initial guess 사용
                    'success': False,
                    'message': "Fitting failed, used initial guess",
                    'nfev': 0,
                    'cost': None,
                    'optimality': None,
                    'jac': None
                }

        fit_results[__Name] = fit_result_forEach
    # print(fit_results['−0.3 V'][1]['result'].x)



    '''
    ‘trf’ : Trust Region Reflective algorithm, particularly suitable for large sparse problems with bounds.
            Generally robust method.

    ‘dogbox’ : dogleg algorithm with rectangular trust regions, typical use case is small problems with bounds.
            Not recommended for problems with rank-deficient Jacobian.

    ‘lm’ : Levenberg-Marquardt algorithm as implemented in MINPACK. Doesn’t handle bounds and sparse Jacobians.
        Usually the most efficient method for small unconstrained problems.
    '''

    # 첫 번째 Huang-Rhys factor 선택
    target_lambda_squared = lambda_squared_values[0]
    '''
    # 가로 3, 세로 3 그리드를 만들고, 특정한 위치에 그래프를 배치한다는 가정은 그대로 유지
    positions = [
        (1, 0), # i=0, 데이터1
        (0, 1), # i=1, 데이터2
        (0, 2), # i=2, 데이터3
        (1, 1), # i=3, 데이터4
        (1, 2), # i=4, 데이터5
        (2, 1), # i=5, 데이터6
        (2, 2)  # i=6, 데이터7
    ]

    fig, axes = plt.subplots(nrows=3, ncols=3, figsize=(12, 12), sharex=True)

    # dataList_Data: {__Name: y_array, ...}
    # hw_data: {__Name: hw_array, ...}
    # fit_results, GmVals, target_lambda_squared, fit_Range 등이 기존과 동일하다고 가정

    for i, (__Name, y) in enumerate(dataList_Data.items()):
        if i >= len(positions):
            break
        row, col = positions[i]
        ax = axes[row, col]

        fit_info = fit_results[__Name][target_lambda_squared]['result']
        if fit_info is not None and fit_results[__Name][target_lambda_squared]['success']:
            optimized_params = fit_info.x
        else:
            optimized_params = fit_results[__Name][target_lambda_squared]['x']

        base, W, C, E00, sigma, Cpol, Epol, sigma_pol = optimized_params
        Gm_for_this = fit_results[__Name][target_lambda_squared]['GmVals']
        fitted_curve = func(hw, *optimized_params, target_lambda_squared, Gm_for_this)

        ax.axvline(fit_Ranges[__Name][0], color='grey', linestyle='--', linewidth=1, label='LB of fit range')
        ax.axvline(fit_Ranges[__Name][1], color='grey', linestyle='--', linewidth=1, label='UB of fit range')
        ax.plot(hw, y, 'o', label='Raw Data', markersize=5)
        ax.plot(hw, fitted_curve[2] + base, 'o', label='Vibronic Contribution', alpha=0.7, markersize=4)
        ax.plot(hw, fitted_curve[3] + base, '^', label='Polaronic Contribution', alpha=0.7, markersize=4)
        ax.plot(hw, fitted_curve[0], '-', color='black', label='Fitted Curve', linewidth=2)

        for j in range(5):
            ax.plot(hw, fitted_curve[1][:, j] + base, '--', label=f'0-{j} Contribution', alpha=0.7)

        ax.fill_between(hw, y - fitted_curve[0], 0, color='blue', alpha=0.15)
        ax.set_title(f'({__Name}) λ²={target_lambda_squared}', fontsize=12)
        ax.set_xlabel('Photon Energy (eV)', fontsize=10)
        ax.set_ylabel('Absorption (a.u.)', fontsize=10)
        ax.grid(alpha=0.3)

    h, l = axes[0, 1].get_legend_handles_labels()
    fig.legend(h, l, fontsize=8, loc='upper left', bbox_to_anchor=(0,1), bbox_transform=axes[0,0].transAxes)

    plt.tight_layout()
    plt.show()
    '''

    wb_report = op.new_book('w')
    wb_report.lname = f"FitResult-{data_wb_ref}-{data_ws_ref}"

    for i, (__Name, y) in enumerate(dataList_Data.items()):

        fit_info = fit_results[__Name][target_lambda_squared]['result']
        if fit_info is not None and fit_results[__Name][target_lambda_squared]['success']:
            optimized_params = fit_info.x
        else:
            optimized_params = fit_results[__Name][target_lambda_squared]['x']

        base, W, C, E00, sigma, Cpol, Epol, sigma_pol = optimized_params
        Gm_for_this = fit_results[__Name][target_lambda_squared]['GmVals']
        originTransfer(hw[0], hw[-1], 500, wb_report, __Name, *optimized_params, target_lambda_squared, Gm_for_this)

    op.save()


except Exception as e:
    print("An error occurred:", e)

finally:
    op.utils.exit()