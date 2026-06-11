import originpro as op
import pandas as pd
import numpy as np
from scipy.special import factorial
from scipy.optimize import least_squares
from scipy.integrate import simpson

'''
    print(gr_Page.lname)            # long name
    print(gr_Page.get_str('name'))  # short name
    print(gr_Page.name)             # short name
'''


def init_Project(__path, __name):

    # Very useful, especially during development, when you are
    # liable to have a few uncaught exceptions.
    # Ensures that the Origin instance gets shut down properly.
    # Note: only applicable to external Python.
    import sys
    def origin_shutdown_exception_hook(exctype, value, traceback):
        '''Ensures Origin gets shut down if an uncaught exception'''
        op.exit()
        sys.__excepthook__(exctype, value, traceback)
    if op and op.oext:
        sys.excepthook = origin_shutdown_exception_hook
    
    op.attach()
    if op.get_lt_str('%G') != "UNTITLED":
        op.save()

    # Make Origin instance visible if external python
    if op.oext:
        op.set_show(True)
    
    from os.path import join
    opened_full = join(op.get_lt_str('%X'), op.get_lt_str('%G') + '.opju')
    passed_full = join(__path, __name)

    if __path == "" or __name == "" or passed_full == opened_full:
        op.attach()
        print("Connected to the opened OriginPro project ...")
    else:
        op.project.open(passed_full)
        print("Now opening:\n", passed_full)

    op.save()

    return

def genBookName(name):
    # Does not check if it is short or long name
    return f'[{name}]'

def genSheetName(book_name, sheet_name):
    return genBookName(book_name) +  sheet_name

def wrapBookFinder(sname, lname = ""):

    __wb = op.find_book(type = 'w', name = genBookName(sname)) \
        or op.find_book(type = 'w', name = genBookName(lname))

    if __wb is None:
        __wb = op.new_book(type = 'w')

    return __wb

def wrapSheetFinder(WB = None, sheet_name = ""):

    __wb = WB or op.new_book(type = 'w')

    __wks = op.find_sheet(type = 'w', ref = genSheetName(__wb.name, sheet_name)) \
        or op.find_sheet(type = 'w', ref = genSheetName(__wb.lname, sheet_name))

    if __wks is None:
        __wks = __wb.add_sheet(name = sheet_name)

    return __wks

def get_report_book(__BName_data):

    report_WBbook_Name = f"FitResult-{__BName_data}"

    wb_report = wrapBookFinder(report_WBbook_Name)
    
    if wb_report is None:
        wb_report = op.new_book(type = 'w', lname = report_WBbook_Name)

    return wb_report


def write_result_sheet(__WB_report, __WB_params, __label, __df_curve, base, W, C, E00, sigma, Cpol, Epol, sigma_pol):
    __df__opt_param = pd.DataFrame({__label: [base, W, C, E00, sigma, Cpol, Epol, sigma_pol]})

    ws_report = wrapSheetFinder(__WB_report, __label)
    ws_prams = __WB_params[__label]

    ws_report.from_df(__df_curve)
    ws_prams.from_df(__df__opt_param, 4)

    for i, col in enumerate(__df_curve.columns[3:], start=3):
        ws_report.set_label(col = i, val = simpson(__df_curve[col].values-base, x=__df_curve.iloc[:,0].values), type = 'C')
    return


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
    Ep = 0.174  # Vibrational mode energy (eV)

    mVals = np.arange(5)  # 0~4 nm

    # Vibronic contributions
    factors = (np.exp(-lambda_squared) * lambda_squared**mVals) / np.vectorize(np.math.factorial)(mVals)
    terms = factors * (1 - (W * np.exp(-lambda_squared) / (2 * Ep)) * np.array(Gm_vals))**2
    gaussians = np.exp(-((hw[:, None] - E00 - np.array(mVals) * Ep - 0.5 * W * lambda_squared**np.array(mVals) * np.exp(-lambda_squared))**2) / (2 * sigma**2)) \
                / (np.sqrt(2 * np.pi) * sigma)
    individual_contributions = base + C * terms * gaussians
    
    vibronic_contribution_Sum = np.sum(individual_contributions, axis=1) - base * (len(mVals) - 1)

    # Polaronic contribution
    polaronic_contribution = base - Cpol * np.exp(-((hw - Epol)**2) / (2 * sigma_pol**2)) / (np.sqrt(2 * np.pi) * sigma_pol)

    # Total absorption
    total_absorption = - base + vibronic_contribution_Sum + polaronic_contribution

    return total_absorption, individual_contributions, vibronic_contribution_Sum, polaronic_contribution

# Residuals function for least_squares
def residuals(params, hw, y, lambda_squared, Gm_vals):
    base, W, C, E00, sigma, Cpol, Epol, sigma_pol,  = params
    model = func(hw, base, W, C, E00, sigma, Cpol, Epol, sigma_pol, lambda_squared, Gm_vals)
    return model[0] - y


def get_singleFit_params(__result_set, __label, __lsq):
    __result = __result_set[__label][__lsq]['result']
    if __result is not None and __result_set[__label][__lsq]['success']:
        optimized_params = __result.x
    else:
        optimized_params = __result_set[__label][__lsq]['x']
    
    return optimized_params, __result_set[__label][__lsq]['GmVals']


def plot(hw, __ranges, __lsq, __dataList_Data, __fit_results):
    import matplotlib.pyplot as plt
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

    for i, (__Name, y) in enumerate(__dataList_Data.items()):
        if i >= len(positions):
            break
        row, col = positions[i]
        ax = axes[row, col]

        optimized_params, Gm_for_this = get_singleFit_params(__fit_results, __Name, __lsq)
        base, W, C, E00, sigma, Cpol, Epol, sigma_pol = optimized_params
        fitted_curve = func(hw, *optimized_params, target_lambda_squared, Gm_for_this)

        ax.axvline(__ranges[__Name][0], color='grey', linestyle='--', linewidth=1, label='LB of fit range')
        ax.axvline(__ranges[__Name][1], color='grey', linestyle='--', linewidth=1, label='UB of fit range')
        ax.plot(hw, y, 'o', label='Raw Data', markersize=5)
        ax.plot(hw, fitted_curve[2] + base, 'o', label='Vibronic Contribution', alpha=0.7, markersize=4)
        ax.plot(hw, fitted_curve[3] + base, '^', label='Polaronic Contribution', alpha=0.7, markersize=4)
        ax.plot(hw, fitted_curve[0], '-', color='black', label='Fitted Curve', linewidth=2)

        for j in range(5):
            ax.plot(hw, fitted_curve[1][:, j] + base, '--', label=f'0-{j} Contribution', alpha=0.7)

        ax.fill_between(hw, y - fitted_curve[0], 0, color='blue', alpha=0.15)
        ax.set_title(f'({__Name }) λ²={__lsq}', fontsize=12)
        ax.set_xlabel('Photon Energy (eV)', fontsize=10)
        ax.set_ylabel('Absorption (a.u.)', fontsize=10)
        ax.grid(alpha=0.3)

    handles, lables = axes[0, 1].get_legend_handles_labels()
    fig.legend(handles, lables, fontsize=8, loc='upper left', bbox_to_anchor=(0,1), bbox_transform=axes[0,0].transAxes)

    plt.tight_layout()
    plt.show()


def originTransfer(__range_lb, __range_ub, __nPoints, __reportWBook, __paramWBook, __SName, base, W, C, E00, sigma, Cpol, Epol, sigma_pol, lambda_squared, Gm_vals):

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
    
    write_result_sheet(__reportWBook, __paramWBook, __SName, df_curve, *optimized_params)

    return

try:
    ##================================================================================================================================================

    opj_path = r"C:\Users\woong\Dropbox\==== SKKU-SAINT ====\==== SAINT-OSL ====\1. Research tmp\2024_Operando GIWAXS"
    opj_name = "Operando GIWAXS_Other data.opju"

    init_Project(opj_path, opj_name)

    ##================================================================================================================================================


    # Huang-Rhys factor used for fitting
    lambda_wb_name = "lambdaSheet"
    lambda_ws_name = "Huang-Rhys factor"
    wb_lambda = wrapBookFinder(lambda_wb_name)
    wks_lambda = wrapSheetFinder(wb_lambda, lambda_ws_name)
    lambda_squared_values = [float(comments) for comments in wks_lambda.get_labels('C')[1:]]
    # print([float(comments) for comments in wks_lambda.get_labels('C')[1:]])

    # Calculate Gm for m = 0, 1, 2, 3, 4
    m_values = wks_lambda.to_df(c1=0, numcols=1).iloc[:,0]
    GmVals = {lambda_squared: [calculate_Gm(lambda_squared, m) for m in m_values]
            for lambda_squared in lambda_squared_values}


    ##================================================================================================================================================


    # Get data for fitting (in [nm])
    data_wb_name = "Book12"
    data_ws_name = "CF"
    wb_data = wrapBookFinder(data_wb_name)
    wks_data = wrapSheetFinder(wb_data, data_ws_name) # Worksheet 객체 반환
    df = wks_data.to_df()

    # Get X-axis values
    x = df.iloc[:,0]
    hw =  np.array(1240/x)     # Photon energy range (in eV)

    # Get Y-axis values
    dataList_Name_fromLName = wks_data.get_labels()[2:wks_data.cols]  # 각 컬럼의 Label
    dataList_Data = df.iloc[:, 2:wks_data.cols].to_dict(orient='series')  # {label: series}

    print("=================Data Transferred Successfully=================")

    ##================================================================================================================================================


    # Initial guesses for fitting
    ig_wb_name = data_wb_name
    ig_ws_name = dataList_Name_fromLName
    wb_ig = wrapBookFinder(ig_wb_name)
    wksArr_ig = [wrapSheetFinder(wb_ig, __wksName_ig) for __wksName_ig in ig_ws_name]


    # 데이터 범위 제한 (fitting 범위)
    fit_range_masks = {}
    ig_values = {}
    bounds = {}
    fit_ranges = {}

    for __wks_ig in wksArr_ig:
        __ig_key = __wks_ig.name
        fit_range_masks[__ig_key] = (hw >= float(__wks_ig.get_labels('C')[1])) & (hw <= float(__wks_ig.get_labels('C')[3]))
        fit_ranges[__ig_key] = [float(__wks_ig.get_labels('C')[1]), float(__wks_ig.get_labels('C')[3])]

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
        hw_filtered = hw[fit_range_masks[__Name]]
        y_filtered = y[fit_range_masks[__Name]]

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

    #plot(hw, fit_Ranges, target_lambda_squared, dataList_Data, fit_results)

    wb_report = get_report_book(data_wb_name)
    wb_params = wb_ig


    for i, (__Name, y) in enumerate(dataList_Data.items()):

        optimized_params, Gm_for_this = get_singleFit_params(fit_results, __Name, target_lambda_squared)
        # base, W, C, E00, sigma, Cpol, Epol, sigma_pol = optimized_params
        fitted_curve = func(hw, *optimized_params, target_lambda_squared, Gm_for_this)

        originTransfer(hw[0], hw[-1], 500, wb_report, wb_params, __Name, *optimized_params, target_lambda_squared, Gm_for_this)


except Exception as e:
    print("An error occurred:", e)

finally:
    op.save()
    op.detach()