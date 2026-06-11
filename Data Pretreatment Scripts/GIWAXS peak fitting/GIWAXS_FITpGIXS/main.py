# main.py
"""
GIWAXS 1D 프로파일 피팅 메인 스크립트.
백엔드를 'qtagg'로 변경하여 PyQt6 UI와의 충돌을 방지함.
"""

import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import matplotlib
# TkAgg 대신 qtagg를 사용하여 PyQt6 UI와 백엔드를 통일합니다.
matplotlib.use('qtagg') 
import matplotlib.pyplot as plt

import numpy as np
import originpro as op
from PyQt6.QtWidgets import QApplication

from dataAssign import opj_path, opj_name, data_wb_name
from Handler.OriginWrapper import init_Project, wrapBookFinder

from peakPicker import pick_peaks_interactive, pick_region_detail, generate_region_ig
from FitFn_GaussExp import fit_region
from pyView import plot_and_select
from OriginInterface import transfer_sheet

# PyQt6 Application 인스턴스를 루프 밖에서 미리 생성합니다.
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

try:
    init_Project(opj_path, opj_name)
    wb = wrapBookFinder(data_wb_name)

    data_dict = {}
    idx = 0
    while True:
        try: wks = wb[idx]
        except (TypeError, IndexError): break
        
        sheet_name = wks.name
        try:
            x, y = wks.to_list(col=0), wks.to_list(col=1)
            if x and y:
                data_dict[sheet_name] = (np.array(x, dtype=float), np.array(y, dtype=float))
        except: pass
        idx += 1

    n_total_sheets = len(data_dict)

    for sheet_idx, (sn, (x, y)) in enumerate(data_dict.items(), 1):
        print(f"\n{'='*60}\n  Sheet [{sheet_idx}/{n_total_sheets}]: {sn}\n{'='*60}")

        try:
            # 1. Peak 위치 선택
            rough_peaks = pick_peaks_interactive(x, y, title=sn)
            plt.close('all') # 선택 창 닫기
            if not rough_peaks: continue

            # 2. Region별 범위 설정
            region_infos = []
            for i, rp in enumerate(rough_peaks):
                rng, peaks = pick_region_detail(x, y, rp, i, len(rough_peaks), sn)
                plt.close('all') # 각 Region 설정 창 닫기

                if rng is None: continue
                plb, pub = rng
                mask = (x >= plb) & (x <= pub)
                x_fit, y_fit = x[mask], y[mask]

                if len(x_fit) < 5: continue

                bkg_ig, peak_ig_list = generate_region_ig(x_fit, y_fit, peaks)
                region_infos.append({
                    'range': (plb, pub), 'x': x_fit, 'y': y_fit,
                    'peak_positions': peaks, 'bkg_ig': bkg_ig, 'peak_ig_list': peak_ig_list,
                })

            if not region_infos: continue

            # 3. 피팅 실행
            regions = []
            for i, reg in enumerate(region_infos):
                result = fit_region(reg['x'], reg['y'], reg['bkg_ig'], reg['peak_ig_list'], reg['peak_positions'])
                result.update({
                    'range': reg['range'], 'x': reg['x'], 'y': reg['y'],
                    'peak_positions': reg['peak_positions'], 
                    'original_peak_ig': reg['peak_ig_list'], 'original_bkg_ig': reg['bkg_ig']
                })
                regions.append(result)

            # 4. 피팅 결과 UI (plot_and_select) - 여기서 block되어야 함
            while True:
                # 여기서 QApplication 인스턴스를 재사용합니다.
                view_result = plot_and_select(sn, regions, data_dict)

                if view_result['action'] == 'confirm':
                    selected = view_result['results']
                    break
                elif view_result['action'] == 'reset':
                    # Reset 로직 (생략 - 기존과 동일)
                    ri = view_result['region_ri']
                    old_reg = regions[ri]
                    init_pos = old_reg['peak_positions'][0] if old_reg['peak_positions'] else (x.mean(), y.max())
                    rng, new_peaks = pick_region_detail(x, y, init_pos, ri, 1, sn)
                    plt.close('all')
                    if rng and new_peaks:
                        plb, pub = rng
                        rmask = (x >= plb) & (x <= pub)
                        bkg_ig, p_ig = generate_region_ig(x[rmask], y[rmask], new_peaks)
                        new_res = fit_region(x[rmask], y[rmask], bkg_ig, p_ig, new_peaks)
                        new_res.update({'range':(plb, pub), 'x':x[rmask], 'y':y[rmask], 'peak_positions':new_peaks, 'original_peak_ig':p_ig, 'original_bkg_ig':bkg_ig})
                        regions[ri] = new_res

            # 5. Origin 전송 및 정리
            transfer_sheet(f"Fitted_{sn}", sn, selected)
            print(f"  → [{sn}] Processed and Transferred.")

        except Exception as e:
            print(f"  ⚠ {sn} Error: {e}")
            continue

except Exception as e:
    print(f"Fatal Error: {e}")
finally:
    op.save()
    op.detach()