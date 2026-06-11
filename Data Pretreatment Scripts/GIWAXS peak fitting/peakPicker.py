# peakPicker.py
"""
matplotlib 기반 interactive peak 피팅 모듈.

워크플로우 (시트마다):
  Step 1) 전체 데이터에서 대략적 peak 위치 클릭 → fitting region 개수 결정
  Step 2) 각 region마다:
          - RangeSlider로 fitting 범위 드래그
          - 좌클릭으로 peak 추가 (여러 개 가능)
          - [Show Peaks] / [Clear All] / [Confirm]
"""

import matplotlib.pyplot as plt
from matplotlib.widgets import Button, RangeSlider
from matplotlib.path import Path as MplPath
import numpy as np


def _valid_mask(y):
    """y가 유효한 (0이 아니고 finite한) 인덱스를 반환."""
    return np.isfinite(y) & (y != 0)


# =============================================================================
# Step 1: 대략적 Peak 위치 지정 (전체 데이터)
# =============================================================================

def pick_peaks_interactive(x, y, title=""):
    """전체 데이터에서 peak 위치 클릭. → fitting region 수를 결정."""
    valid = _valid_mask(y)
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.canvas.manager.set_window_title('Step 1: Select Peak Positions')
    ax.plot(x[valid], y[valid], 'k-', linewidth=1, label='Data')
    ax.set_title(f'{title}\n[Left-click: add peak]', fontsize=12)
    ax.set_xlabel('q (Å⁻¹)')
    ax.set_ylabel('Intensity')
    ax.grid(alpha=0.3)

    state = {'peaks': [], 'markers': [], 'labels': []}

    list_text = ax.text(
        0.02, 0.95, '', transform=ax.transAxes, fontsize=9,
        verticalalignment='top', fontfamily='monospace',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='lightyellow', alpha=0.9)
    )

    def update_list_text():
        if not state['peaks']:
            list_text.set_text('')
        else:
            lines = [f"Peaks ({len(state['peaks'])})"]
            for i, (px, py) in enumerate(state['peaks']):
                lines.append(f"  {i+1}. x={px:.4f}  y={py:.2e}")
            list_text.set_text('\n'.join(lines))
        fig.canvas.draw_idle()

    def rescale_y():
        yv = y[valid]
        if len(yv) == 0: return
        if ax.get_yscale() == 'log':
            yp = yv[yv > 0]
            if len(yp) == 0: return
            lmin, lmax = np.log10(yp.min()), np.log10(yp.max())
            lr = lmax - lmin if lmax > lmin else 1.0
            ax.set_ylim(10 ** (lmin - lr * 0.2), 10 ** (lmax + lr * 0.2))
        else:
            ymin, ymax = yv.min(), yv.max()
            sp = ymax - ymin if ymax > ymin else abs(ymax) * 0.1 or 1.0
            ax.set_ylim(ymin - sp * 0.2, ymax + sp * 0.2)
        fig.canvas.draw_idle()

    def on_click(event):
        if event.inaxes != ax or event.button != 1: return
        px, py = event.xdata, event.ydata
        state['peaks'].append((px, py))
        mk, = ax.plot(px, py, 'rv', markersize=10, zorder=5)
        state['markers'].append(mk)
        lbl = ax.annotate(
            f'{len(state["peaks"])}', (px, py),
            textcoords="offset points", xytext=(6, 8),
            fontsize=9, color='red', fontweight='bold')
        state['labels'].append(lbl)
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect('button_press_event', on_click)

    fig.subplots_adjust(bottom=0.15)

    ax_show = fig.add_axes([0.12, 0.02, 0.14, 0.04])
    btn_show = Button(ax_show, 'Show Peaks', hovercolor='#e8f5e9')
    btn_show.on_clicked(lambda e: update_list_text())

    ax_clr = fig.add_axes([0.29, 0.02, 0.12, 0.04])
    btn_clr = Button(ax_clr, 'Clear All', hovercolor='#ffebee')
    def on_clear(event):
        for mk in state['markers']: mk.remove()
        for lb in state['labels']: lb.remove()
        state['peaks'].clear(); state['markers'].clear(); state['labels'].clear()
        list_text.set_text(''); fig.canvas.draw_idle()
    btn_clr.on_clicked(on_clear)

    ax_lg = fig.add_axes([0.44, 0.02, 0.12, 0.04])
    btn_lg = Button(ax_lg, 'Log scale', hovercolor='lightgray')
    def on_log(event):
        if ax.get_yscale() == 'linear':
            ax.set_yscale('log'); btn_lg.label.set_text('Linear')
        else:
            ax.set_yscale('linear'); btn_lg.label.set_text('Log scale')
        rescale_y()
    btn_lg.on_clicked(on_log)

    ax_cfm = fig.add_axes([0.82, 0.02, 0.14, 0.04])
    btn_cfm = Button(ax_cfm, 'Confirm', hovercolor='#fff3e0')
    result = {'confirmed': False}
    def on_confirm(event):
        result['confirmed'] = True; plt.close(fig)
    btn_cfm.on_clicked(on_confirm)

    print(f"\n  → {title}: 좌클릭으로 peak 추가 → [Confirm]")
    plt.show(block=True)

    peaks = state['peaks'] if result['confirmed'] else []
    print(f"  → {len(peaks)} region(s) confirmed.")
    return peaks


# =============================================================================
# Step 2: Region별 범위 + 복수 peak 지정
# =============================================================================

def pick_region_detail(x, y, init_peak_pos, region_idx, n_regions, sheet_title=""):
    """
    하나의 fitting region 설정:
      - RangeSlider로 범위 드래그
      - 좌클릭으로 peak 추가 (초기 peak 1개 미리 표시)
      - [Show Peaks] / [Clear All] / [Rescale] / [Full] / [Log] / [Confirm]

    Returns:
        (lb, ub): fitting 범위
        peak_positions: [(px, py), ...] 확정된 peak 리스트
        또는 (None, None) 취소 시
    """
    fig = plt.figure(figsize=(10, 7))
    fig.canvas.manager.set_window_title(
        f'Step 2: Select Region & Peaks — {sheet_title} R{region_idx+1}')

    ax_left, ax_right = 0.10, 0.95
    ax_width = ax_right - ax_left
    ax = fig.add_axes([ax_left, 0.36, ax_width, 0.60])
    valid = _valid_mask(y)
    ax.plot(x[valid], y[valid], 'k-', linewidth=1, label='Data')
    ax.set_ylabel('Intensity')
    ax.grid(alpha=0.3)

    x_min, x_max = float(x.min()), float(x.max())

    # ── Peak 상태 (복수 peak 지원) ──────────────────────────────────────────
    state = {'peaks': [init_peak_pos], 'markers': [], 'labels': []}

    # 초기 peak 마커
    ipx, ipy = init_peak_pos
    mk, = ax.plot(ipx, ipy, 'rv', markersize=10, zorder=10)
    state['markers'].append(mk)
    lbl = ax.annotate('1', (ipx, ipy), textcoords="offset points",
                       xytext=(6, 8), fontsize=9, color='red', fontweight='bold', zorder=10)
    state['labels'].append(lbl)

    # peak 리스트 텍스트
    list_text = ax.text(
        0.02, 0.95, '', transform=ax.transAxes, fontsize=9,
        verticalalignment='top', fontfamily='monospace',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='lightyellow', alpha=0.9)
    )

    def update_list_text():
        if not state['peaks']:
            list_text.set_text('')
        else:
            lines = [f"Peaks ({len(state['peaks'])})"]
            for i, (px, py) in enumerate(state['peaks']):
                lines.append(f"  {i+1}. x={px:.4f}  y={py:.2e}")
            list_text.set_text('\n'.join(lines))
        fig.canvas.draw_idle()

    # ── Range 표시 ───────────────────────────────────────────────────────────
    init_w = (x_max - x_min) * 0.15
    init_lb = max(x_min, ipx - init_w)
    init_ub = min(x_max, ipx + init_w)

    span = ax.axvspan(init_lb, init_ub, alpha=0.10, color='blue', zorder=0)
    vl_lb = ax.axvline(init_lb, color='blue', ls='--', lw=1, alpha=0.6)
    vl_ub = ax.axvline(init_ub, color='blue', ls='--', lw=1, alpha=0.6)
    range_state = {'lb': init_lb, 'ub': init_ub}

    range_text = ax.text(
        0.98, 0.95, '', transform=ax.transAxes, fontsize=10,
        verticalalignment='top', horizontalalignment='right',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='wheat', alpha=0.8)
    )

    def update_range_display(lb, ub):
        range_state['lb'], range_state['ub'] = lb, ub
        xy = span.get_xy(); xy[:, 0] = [lb, lb, ub, ub, lb]; span.set_xy(xy)
        vl_lb.set_xdata([lb]); vl_ub.set_xdata([ub])
        range_text.set_text(f'Range: [{lb:.4f}, {ub:.4f}]')
        fig.canvas.draw_idle()

    update_range_display(init_lb, init_ub)

    # ── y축 rescale ──────────────────────────────────────────────────────────
    def rescale_y():
        lo, hi = ax.get_xlim()
        mask = (x >= lo) & (x <= hi) & valid
        if not mask.any(): return
        yv = y[mask]
        if ax.get_yscale() == 'log':
            yp = yv[yv > 0]
            if len(yp) == 0: return
            lmin, lmax = np.log10(yp.min()), np.log10(yp.max())
            lr = lmax - lmin if lmax > lmin else 1.0
            ax.set_ylim(10 ** (lmin - lr * 0.2), 10 ** (lmax + lr * 0.2))
        else:
            ymn, ymx = yv.min(), yv.max()
            sp = ymx - ymn if ymx > ymn else abs(ymx) * 0.1 or 1.0
            ax.set_ylim(ymn - sp * 0.2, ymx + sp * 0.2)
        fig.canvas.draw_idle()

    # ── 클릭으로 peak 추가 ──────────────────────────────────────────────────
    def on_click(event):
        if event.inaxes != ax or event.button != 1: return
        px, py = event.xdata, event.ydata
        state['peaks'].append((px, py))
        mk, = ax.plot(px, py, 'rv', markersize=10, zorder=10)
        state['markers'].append(mk)
        lbl = ax.annotate(f'{len(state["peaks"])}', (px, py),
                          textcoords="offset points", xytext=(6, 8),
                          fontsize=9, color='red', fontweight='bold', zorder=10)
        state['labels'].append(lbl)
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect('button_press_event', on_click)

    # ── RangeSlider ──────────────────────────────────────────────────────────
    slider_h = 0.025
    slider_y = 0.36 - slider_h
    ax_slider = fig.add_axes([ax_left, slider_y, ax_width, slider_h])

    # 커스텀 핸들 마커
    handle_verts = [(-0.35,-0.8),(0.35,-0.8),(0.35,0.25),(0.0,0.9),(-0.35,0.25),(-0.35,-0.8)]
    handle_codes = [MplPath.MOVETO, MplPath.LINETO, MplPath.LINETO,
                    MplPath.LINETO, MplPath.LINETO, MplPath.CLOSEPOLY]
    handle_marker = MplPath(handle_verts, handle_codes)

    slider = RangeSlider(ax_slider, '', x_min, x_max,
                         valinit=(init_lb, init_ub), valstep=(x_max-x_min)/1000)
    try:
        for h in slider._handles: h.set_visible(False)
    except AttributeError:
        pass

    h_lb, = ax_slider.plot(init_lb, 0.5, marker=handle_marker, markersize=14,
                           color='#4A90D9', markeredgecolor='#2C5F8A', markeredgewidth=1, zorder=10)
    h_ub, = ax_slider.plot(init_ub, 0.5, marker=handle_marker, markersize=14,
                           color='#4A90D9', markeredgecolor='#2C5F8A', markeredgewidth=1, zorder=10)

    def on_slider(val):
        update_range_display(val[0], val[1])
        h_lb.set_xdata([val[0]]); h_ub.set_xdata([val[1]])
    slider.on_changed(on_slider)

    # ── 라벨, 타이틀 ────────────────────────────────────────────────────────
    xlabel_y = slider_y - 0.04
    fig.text(0.5, xlabel_y, 'q (Å⁻¹)', ha='center', fontsize=12)
    title_y = xlabel_y - 0.05
    fig.text(0.5, title_y, f'{sheet_title} — Region {region_idx+1}/{n_regions}  '
             f'[Left-click: add peak | Slider: range]',
             ha='center', fontsize=11, fontweight='bold')

    # ── 버튼 (최하단) ───────────────────────────────────────────────────────
    btn_y, btn_h = 0.02, 0.04
    bw = 0.09  # button width

    ax_sp = fig.add_axes([0.04, btn_y, 0.11, btn_h])
    btn_sp = Button(ax_sp, 'Show Peaks', hovercolor='#e8f5e9')
    btn_sp.on_clicked(lambda e: update_list_text())

    ax_ca = fig.add_axes([0.17, btn_y, 0.10, btn_h])
    btn_ca = Button(ax_ca, 'Clear All', hovercolor='#ffebee')
    def on_clear(event):
        for mk in state['markers']: mk.remove()
        for lb in state['labels']: lb.remove()
        state['peaks'].clear(); state['markers'].clear(); state['labels'].clear()
        list_text.set_text(''); fig.canvas.draw_idle()
    btn_ca.on_clicked(on_clear)

    ax_rs = fig.add_axes([0.30, btn_y, bw, btn_h])
    btn_rs = Button(ax_rs, 'Rescale', hovercolor='#c8e6c9')
    def on_rescale(event):
        ax.set_xlim(range_state['lb'], range_state['ub']); rescale_y()
    btn_rs.on_clicked(on_rescale)

    ax_fl = fig.add_axes([0.41, btn_y, 0.07, btn_h])
    btn_fl = Button(ax_fl, 'Full', hovercolor='#bbdefb')
    def on_full(event):
        ax.set_xlim(x_min, x_max); rescale_y()
    btn_fl.on_clicked(on_full)

    ax_lg = fig.add_axes([0.50, btn_y, bw, btn_h])
    btn_lg = Button(ax_lg, 'Log scale', hovercolor='lightgray')
    def on_log(event):
        if ax.get_yscale() == 'linear':
            ax.set_yscale('log'); btn_lg.label.set_text('Linear')
        else:
            ax.set_yscale('linear'); btn_lg.label.set_text('Log scale')
        rescale_y()
    btn_lg.on_clicked(on_log)

    ax_cfm = fig.add_axes([0.84, btn_y, 0.12, btn_h])
    btn_cfm = Button(ax_cfm, 'Confirm', hovercolor='#fff3e0')
    result = {'confirmed': False}
    def on_confirm(event):
        result['confirmed'] = True; plt.close(fig)
    btn_cfm.on_clicked(on_confirm)

    print(f"\n  → Region {region_idx+1}/{n_regions}: peak 추가/범위 조정 → [Confirm]")
    plt.show(block=True)

    if result['confirmed'] and state['peaks']:
        lb, ub = range_state['lb'], range_state['ub']
        print(f"  → Region {region_idx+1} 확정: {len(state['peaks'])} peak(s), "
              f"range=[{lb:.4f}, {ub:.4f}]")
        return (lb, ub), state['peaks']
    return None, None


# =============================================================================
# Initial guess 생성 (복수 peak)
# =============================================================================

def generate_region_ig(x, y, peak_positions):
    """
    복수 peak에 대한 initial guess.
    Returns: bkg_ig, peak_ig_list
    """
    valid = np.isfinite(y) & (y != 0)
    yv = y[valid] if valid.any() else y

    # bkg ig: a, b, c — 모두 >= 0 보장 (bounds가 [0,0,0] ~ [inf,20,inf])
    a_ig = max(float(np.median(yv)), 1e-6)
    b_ig = 2.0
    c_ig = max(float(np.min(yv)), 0.0)
    bkg_ig = (a_ig, b_ig, c_ig)

    peak_ig_list = []
    x_range = x.max() - x.min()

    for (px, py) in peak_positions:
        amplitude = max(float(py - c_ig), 1e-6)
        peak_ig_list.append((amplitude, float(px), x_range * 0.05))

    return bkg_ig, peak_ig_list


# =============================================================================
# 전체 시트 순회
# =============================================================================

def pick_all(data_dict):
    """
    Returns:
        sheet_region_info: {
            sheet_name: [
                {
                    'range': (lb, ub),
                    'x': x_cropped, 'y': y_cropped,
                    'peak_positions': [(px,py), ...],
                    'bkg_ig': (a,b,c),
                    'peak_ig_list': [(A,μ,FWHM), ...],
                },
                ...
            ]
        }
    """
    sheet_region_info = {}

    for name, (x, y) in data_dict.items():
        print(f"\n{'='*60}")
        print(f"  Sheet: {name}")
        print(f"{'='*60}")

        rough_peaks = pick_peaks_interactive(x, y, title=name)
        if not rough_peaks:
            print(f"  ⚠ {name}: peak 미지정. 스킵.")
            continue

        regions = []
        n_regions = len(rough_peaks)

        for i, rp in enumerate(rough_peaks):
            rng, peaks = pick_region_detail(
                x, y, rp, region_idx=i, n_regions=n_regions, sheet_title=name)

            if rng is None:
                print(f"  ⚠ Region {i+1}: 취소. 스킵.")
                continue

            plb, pub = rng
            mask = (x >= plb) & (x <= pub)
            x_fit, y_fit = x[mask], y[mask]

            if len(x_fit) < 5:
                print(f"  ⚠ Region {i+1}: 데이터 부족. 스킵.")
                continue

            bkg_ig, peak_ig_list = generate_region_ig(x_fit, y_fit, peaks)
            regions.append({
                'range': (plb, pub),
                'x': x_fit, 'y': y_fit,
                'peak_positions': peaks,
                'bkg_ig': bkg_ig,
                'peak_ig_list': peak_ig_list,
            })

        if regions:
            sheet_region_info[name] = regions

    return sheet_region_info
