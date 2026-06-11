# OriginInterface.py
"""
선택된 Fitting 결과를 Origin으로 전송.

구조 (데이터 시트 하나당):
  Workbook "Fitted_{시트이름}"
    ├─ R1           (region 1: raw + fitted curve)
    ├─ R2           (region 2)
    ├─ ...
    └─ Summary      (모든 region 파라미터 요약)
"""

import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import numpy as np
import pandas as pd
from Handler.OriginWrapper import wrapSheetFinder, wrapBookGenerator
from FitFn_GaussExp import model_func, unpack_params


def _write_region(wb, region_idx, result, n_points=500):
    """단일 region의 raw data + fitted curve를 워크시트에 기록."""
    x_raw = result['x']
    y_raw = result['y']
    params = result['params']
    peak_type = result['selected_type']

    x_fit = np.linspace(x_raw.min(), x_raw.max(), n_points)
    total, bkg, peaks = model_func(x_fit, params, peak_type)

    ws_name = f"R{region_idx + 1}"
    wks = wrapSheetFinder(wb, ws_name)

    wks.from_list(col=0, data=x_raw.tolist(), lname='q_raw', units='Å⁻¹', axis='X')
    wks.from_list(col=1, data=y_raw.tolist(), lname='Raw_Y', units='')

    col = 2
    wks.from_list(col=col, data=x_fit.tolist(), lname='q_fit', units='Å⁻¹', axis='X'); col += 1
    wks.from_list(col=col, data=total.tolist(), lname='Fit_Total', units=''); col += 1
    wks.from_list(col=col, data=bkg.tolist(), lname='Background', units=''); col += 1

    type_labels = {'gaussian': 'Gau', 'lorentzian': 'Lor', 'pseudo_voigt': 'PV'}
    type_label = type_labels.get(peak_type, 'Pk')
    for j, pk in enumerate(peaks):
        wks.from_list(col=col, data=(pk + bkg).tolist(),
                       lname=f'{type_label}_{j+1}', units='')
        col += 1

    print(f"    → {ws_name} ({type_label}, {len(peaks)} peaks)")


def _write_summary(wb, sheet_name, regions):
    """파라미터 요약을 Summary 워크시트에 기록."""
    rows = []
    for ri, res in enumerate(regions):
        pt = res['selected_type']
        (a, b, c), peak_params = unpack_params(res['params'], pt)
        base_row = {
            'Region': ri + 1,
            'Type': pt,
            'n_peaks': res['n_peaks'],
            'a': a, 'b': b, 'c': c,
            'Range_LB': res['range'][0],
            'Range_UB': res['range'][1],
            'Success': res['success'],
            'Cost': res['cost'],
        }
        for j, pk in enumerate(peak_params):
            base_row[f'A_{j+1}'] = pk[0]
            base_row[f'Mean_{j+1}'] = pk[1]
            base_row[f'FWHM_{j+1}'] = pk[2]
            if pt == 'pseudo_voigt' and len(pk) > 3:
                base_row[f'eta_{j+1}'] = pk[3]
        rows.append(base_row)

    df = pd.DataFrame(rows)
    wks = wrapSheetFinder(wb, "Summary")
    wks.from_df(df)
    print(f"    → Summary ({len(rows)} region(s))")


def transfer_sheet(wb_name, sheet_name, regions, n_points=500):
    """
    하나의 데이터 시트에 대한 피팅 결과를 Origin Workbook 하나로 전송.

    Args:
        wb_name: 생성할 Workbook 이름 (예: "Fitted_Elvis_Qz1")
        sheet_name: 원본 데이터 시트 이름
        regions: [result_dict, ...] — plot_and_select에서 반환된 region 결과 리스트
    """
    wb = wrapBookGenerator(wb_name)
    print(f"\n  Workbook: [{wb_name}]")

    for ri, res in enumerate(regions):
        _write_region(wb, ri, res, n_points)

    _write_summary(wb, sheet_name, regions)

    print(f"  → [{wb_name}] complete")
