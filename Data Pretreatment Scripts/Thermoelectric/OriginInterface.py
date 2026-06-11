from Handler.OriginWrapper import wrapBookFinder, wrapSheetFinder, genBookName

import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import originpro as op
import pandas as pd
import numpy as np
from scipy.integrate import simpson

def get_report_book(book_name_data):
    """
    결과를 저장할 Report Book을 찾거나, 없으면 새로 만든다.
    """
    report_WBbook_Name = f"FitResult-{book_name_data}"
    wb_report = wrapBookFinder(report_WBbook_Name)
    if wb_report is None:
        wb_report = op.new_book(type='w', lname=report_WBbook_Name)
    return wb_report


def write_result_sheet(__WB_report, __WB_params, __label, __df_curve,
                       base, W, C, E00, sigma, Cpol, Epol, sigma_pol):
    """
    결과 DataFrame을 Origin 워크시트에 쓰는 함수
    """
    __df__opt_param = pd.DataFrame({__label: [base, W, C, E00, sigma, Cpol, Epol, sigma_pol]})
    ws_report = wrapSheetFinder(__WB_report, __label)
    ws_prams = __WB_params[__label]

    # Fitted curve 데이터
    ws_report.from_df(__df_curve)
    # 최적화된 파라미터
    ws_prams.from_df(__df__opt_param, 4)

    # 적분값(예시) 등의 추가 컬럼 라벨 세팅
    for i, col in enumerate(__df_curve.columns[2:], start=2):
        ws_report.set_label(
            col=i,
            val=simpson(__df_curve[col].values - base, x=__df_curve.iloc[:, 0].values),
            type='C'
        )


def originTransfer(range_lb, range_ub, nPoints,
                   __reportWBook, __paramWBook, __SName,
                   base, W, C, E00, sigma, Cpol, Epol, sigma_pol,
                   lambda_squared, Gm_vals):
    """
    주어진 파라미터로 (range_lb ~ range_ub) 구간에 대해
    Fitted Curve를 계산한 뒤 Origin 워크시트로 전달
    """
    # x-axis range
    hw_array = np.linspace(range_lb, range_ub, nPoints)

    # func 함수로 fitted curve 계산
    total_absorption, individual_contributions, vibronic_contribution_Sum, polaronic_contribution = \
        func(hw_array, base, W, C, E00, sigma, Cpol, Epol, sigma_pol, lambda_squared, Gm_vals)

    df_curve = pd.DataFrame({
        'PhotonEnergy(eV)': hw_array,
        'FittedAbsorption': total_absorption,
        'vibronic_contribution_Sum': vibronic_contribution_Sum,
        'polaronic_contribution': polaronic_contribution
    })

    for j in range(individual_contributions.shape[1]):
        df_curve[f'A-(0-{j})'] = individual_contributions[:, j]

    write_result_sheet(
        __WB_report=__reportWBook,
        __WB_params=__paramWBook,
        __label=__SName,
        __df_curve=df_curve,
        base=base, W=W, C=C, E00=E00, sigma=sigma, Cpol=Cpol, Epol=Epol, sigma_pol=sigma_pol
    )
