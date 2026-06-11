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

    opj_name = "test.opju"
    opj_path = r"C:\Users\woong\Dropbox\==== SKKU-SAINT ====\==== SAINT-OSL ====\2. Measurements\0. Data Processing\Data Pretreatment Scripts"

    init_Project(opj_path, opj_name)
    
    wb = wrapBookFinder("asdf")
    print(wb)
    wks = wrapSheetFinder(wb)
    print(wks)


except Exception as e:
    print("An error occurred:", e)

finally:
    op.save()
    op.detach()