# pyView.py
"""
Fitting 결과 시각화 — Tkinter + matplotlib 하이브리드.
시트 단위로 호출. region별 피팅 타입 독립 선택.
"""

import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from FitFn_GaussExp import (model_func, unpack_params, refit_region,
                             _make_peak_mask, PEAK_TYPES, _npp)

EQ_GAUSSIAN = (
    r'$y = F_{\mathrm{bkg}}(x) + \sum_i G_i(x),$'
    r'$\quad F_{\mathrm{bkg}} = a \cdot x^{-b}+c,$'
    r'$\quad G = A\exp\!\left[-\frac{(x-x_c)^2}{2\sigma^2}\right],$'
    r'$\;\sigma=\frac{w}{2\sqrt{2\ln 2}}$'
)
EQ_LORENTZIAN = (
    r'$y = F_{\mathrm{bkg}}(x) + \sum_i L_i(x),$'
    r'$\quad F_{\mathrm{bkg}} = a \cdot x^{-b}+c,$'
    r'$\quad L = \frac{A}{1+\left(\frac{x-x_c}{w/2}\right)^2}$'
)
EQ_PSEUDO_VOIGT = (
    r'$y = F_{\mathrm{bkg}}(x) + \sum_i PV_i(x),$'
    r'$\quad F_{\mathrm{bkg}} = a \cdot x^{-b}+c,$'
    r'$\quad PV = \eta L + (1-\eta)G,\;\eta\in[0,1]$'
)
EQ_LIST = [EQ_GAUSSIAN, EQ_LORENTZIAN, EQ_PSEUDO_VOIGT]
TYPE_LABELS = {'gaussian': 'Gaussian', 'lorentzian': 'Lorentzian',
               'pseudo_voigt': 'Pseudo-Voigt'}
TYPE_CYCLE = list(PEAK_TYPES)
TYPE_COLORS = {'gaussian': '#e8f5e9', 'lorentzian': '#fce4ec',
               'pseudo_voigt': '#e3f2fd'}

def _valid_mask(y):
    return np.isfinite(y) & (y != 0)

def _compute_stats(x, y, params, peak_type):
    valid = _valid_mask(y)
    if not valid.any():
        return None, None
    y_v, t_v = y[valid], model_func(x, params, peak_type)[0][valid]
    dof = max(len(y_v) - len(params), 1)
    ss_res = np.sum((y_v - t_v) ** 2)
    ss_tot = np.sum((y_v - np.mean(y_v)) ** 2)
    return (1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0), ss_res / dof

def _draw_region(ax, x, y, params, peak_type, n_peaks,
                 peak_ig_list=None, mask_factor=None, all_type_results=None):
    ax.cla()
    total, bkg, peaks = model_func(x, params, peak_type)
    valid = _valid_mask(y)
    if peak_ig_list is not None:
        pmask = _make_peak_mask(x, peak_ig_list, factor=mask_factor)
        in_mask, sx = False, None
        for i in range(len(x)):
            if pmask[i] and not in_mask:
                sx, in_mask = x[i], True
            elif not pmask[i] and in_mask:
                ax.axvspan(sx, x[i-1], alpha=0.10, color='gray', zorder=0)
                in_mask = False
        if in_mask:
            ax.axvspan(sx, x[-1], alpha=0.10, color='gray', zorder=0)
    ax.plot(x[valid], y[valid], 'k-', lw=1, alpha=0.8, label='Data')
    ax.plot(x, bkg, '--', color='gray', lw=1, alpha=0.7, label='Bkg')
    colors = plt.cm.tab10(np.linspace(0, 1, max(n_peaks, 1)))
    for j, pk in enumerate(peaks):
        ax.plot(x, pk + bkg, '-', color=colors[j], lw=1, alpha=0.7, label=f'Pk{j+1}')
    ax.plot(x, total, '-', color='red', lw=1.5, label='Fit')
    if valid.any():
        ax.fill_between(x[valid], 0, y[valid] - total[valid], color='blue', alpha=0.08)
    # Stats table
    if all_type_results and valid.any():
        headers = ['', 'Gau', 'Lor', 'PV']
        rows = []
        for sn in ['R²', 'χ²ᵥ']:
            row = [sn]
            for pt in TYPE_CYCLE:
                res = all_type_results.get(pt)
                if res and res.get('params') is not None:
                    r2, chi2 = _compute_stats(x, y, res['params'], pt)
                    row.append(f'{r2:.4f}' if sn == 'R²' else f'{chi2:.2e}')
                else:
                    row.append('—')
            rows.append(row)
        cw_ratio = [1/7, 2/7, 2/7, 2/7]
        tbl = ax.table(cellText=rows, colLabels=headers, loc='upper right',
                       cellLoc='center', bbox=[0.52, 0.68, 0.47, 0.30], colWidths=cw_ratio)
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(6.5)
        sel_col = TYPE_CYCLE.index(peak_type) + 1
        for (ri, ci), cell in tbl.get_celld().items():
            cell.set_linewidth(0); cell.set_edgecolor('none'); cell.PAD = 0.02
            cell.set_facecolor('white'); cell.set_alpha(0.88)
            if ri == 0:
                cell.visible_edges = 'B'; cell.set_linewidth(0.5)
                cell.set_edgecolor('#ccc')
                cell.set_text_props(fontweight='bold' if ci == sel_col else 'normal',
                    color='black' if ci == sel_col else '#b0b0b0', fontsize=6.5)
            else:
                cell.visible_edges = ''
                if ci == 0:
                    cell.set_text_props(fontsize=6.5, color='black', fontweight='bold')
                elif ci == sel_col:
                    cell.set_text_props(fontweight='bold', color='black', fontsize=6.5)
                else:
                    cell.set_text_props(color='#b0b0b0', fontsize=6.5)
    ax.grid(alpha=0.2)

def _draw_param_table(ax_t, params, n_peaks, success, cost, max_peaks, peak_type):
    ax_t.cla(); ax_t.axis('off')
    (a, b, c), pks = unpack_params(params, peak_type)
    is_pv = peak_type == 'pseudo_voigt'
    rows = [['a', f'{a:.4e}'], ['b', f'{b:.4f}'], ['c', f'{c:.4e}']]
    for j in range(max_peaks):
        if j < len(pks):
            pk = pks[j]
            rows += [[f'A_{j+1}', f'{pk[0]:.4e}'], [f'μ_{j+1}', f'{pk[1]:.4f}'],
                     [f'w_{j+1}', f'{pk[2]:.4f}']]
            if is_pv: rows.append([f'η_{j+1}', f'{pk[3]:.4f}'])
        else:
            rows += [[f'A_{j+1}', '—'], [f'μ_{j+1}', '—'], [f'w_{j+1}', '—']]
            if is_pv: rows.append([f'η_{j+1}', '—'])
    rows += [['status', 'OK' if success else 'FAIL'],
             ['cost', f'{cost:.2e}' if cost else 'N/A']]
    tbl = ax_t.table(cellText=rows, colLabels=['Param', 'Value'],
                      colWidths=[0.4, 0.6], loc='upper center', cellLoc='left')
    tbl.auto_set_font_size(False); tbl.set_fontsize(7); tbl.scale(1, 0.9)
    for j in range(2):
        tbl[0, j].set_facecolor('#e0e0e0'); tbl[0, j].set_text_props(fontweight='bold')


# =============================================================================

def plot_and_select(sheet_name, regions, data_dict=None):
    """시트 1개의 결과 표시. Returns action dict."""
    plt.close('all')

    n = len(regions)
    if n == 0:
        return {'action': 'confirm', 'results': [], 'region_types': []}

    max_peaks = max(r['n_peaks'] for r in regions)
    region_types = [r.get('_saved_type', 'gaussian') for r in regions]

    # ── Figure ──────────────────────────────────────────────────────────
    EQ_H, GRAPH_H = 0.8, 2.8
    n_tbl_rows = 3 + max_peaks * 4 + 2 + 1
    TABLE_H = max(1.0, n_tbl_rows * 0.15)
    EQ_FIG_GAP = 0.05
    FIG_T_GAP = 0.25
    fig_h = EQ_H + EQ_FIG_GAP + GRAPH_H + FIG_T_GAP + TABLE_H + 0.1
    fig_w = 5.5 * n + 1.0
    fig = plt.figure(figsize=(fig_w, fig_h))

    def yf(y): return 1.0 - y / fig_h
    def hf(h): return h / fig_h
    xm, xg = 0.07, 0.04
    cw = (1.0 - 2 * xm - max(0, n - 1) * xg) / n
    def cx(c): return xm + c * (cw + xg)

    # Equations (reference, all 3)
    eq_top = 0.1
    erh = EQ_H / 3.3
    for i in range(3):
        ax_eq = fig.add_axes([0.02, yf(eq_top + (i + 0.8) * erh), 0.96, hf(erh * 0.9)])
        ax_eq.axis('off')
        ax_eq.text(0.5, 0.5, EQ_LIST[i], transform=ax_eq.transAxes,
                    fontsize=9, ha='center', va='center', alpha=0.5)

    # Per-region axes
    plot_axes, table_axes = [], []
    for idx in range(n):
        row_top = eq_top + EQ_H + EQ_FIG_GAP
        x0 = cx(idx)
        ax_p = fig.add_axes([x0, yf(row_top + GRAPH_H), cw, hf(GRAPH_H)])
        plot_axes.append(ax_p)
        t_top = row_top + GRAPH_H + FIG_T_GAP
        ax_t = fig.add_axes([x0 + 0.005, yf(t_top + TABLE_H), cw - 0.01, hf(TABLE_H)])
        ax_t.axis('off')
        table_axes.append(ax_t)

    # ── Draw helpers ──────────────────────────────────────────────────
    def redraw(idx, canvas):
        reg = regions[idx]
        pt = region_types[idx]
        res = reg[pt]
        pig = reg.get('original_peak_ig')
        mf = reg.get('_last_mask_factor')
        atr = {t: reg.get(t) for t in TYPE_CYCLE}
        _draw_region(plot_axes[idx], reg['x'], reg['y'], res['params'], pt,
                     reg['n_peaks'], peak_ig_list=pig, mask_factor=mf,
                     all_type_results=atr)
        s = "OK" if res['success'] else "FAIL"
        c = f"cost={res['cost']:.2e}" if res['cost'] else ""
        plot_axes[idx].set_title(f"R{idx+1} [{s}] {c}", fontsize=9)
        _draw_param_table(table_axes[idx], res['params'], reg['n_peaks'],
                           res['success'], res['cost'],
                           max(r['n_peaks'] for r in regions), peak_type=pt)
        canvas.draw()

    def draw_all(canvas):
        for idx in range(n):
            redraw(idx, canvas)

    # ══════════════════════════════════════════════════════════════════
    # Tkinter
    # ══════════════════════════════════════════════════════════════════
    root = tk.Tk()
    root.title(f"Fitting Results — {sheet_name}")
    return_state = {'action': None}

    canvas_frame = ttk.Frame(root)
    canvas_frame.pack(fill=tk.BOTH, expand=True)
    mpl_canvas = FigureCanvasTkAgg(fig, master=canvas_frame)
    mpl_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    draw_all(mpl_canvas)

    # ── Per-region input frames (Scrollable) ─────────────────────────
    # 스크롤바와 캔버스를 담을 컨테이너 프레임
    scroll_container = ttk.Frame(root)
    scroll_container.pack(fill=tk.X, expand=False, padx=5, pady=5)

    # 입력 영역의 고정 높이 지정 (원하는 픽셀 값으로 조절하세요)
    INPUT_AREA_HEIGHT = 220 
    
    input_canvas = tk.Canvas(scroll_container, height=INPUT_AREA_HEIGHT, highlightthickness=0)
    input_scrollbar = ttk.Scrollbar(scroll_container, orient="vertical", command=input_canvas.yview)
    
    # 실제 파라미터 입력 위젯들이 담길 프레임
    input_outer = ttk.Frame(input_canvas)
    
    # 내부 프레임의 크기가 변할 때마다 캔버스의 스크롤 가능 영역(scrollregion) 갱신
    input_outer.bind(
        "<Configure>",
        lambda e: input_canvas.configure(scrollregion=input_canvas.bbox("all"))
    )
    
    # 캔버스 내부에 input_outer 프레임을 윈도우 형태로 삽입
    input_canvas.create_window((0, 0), window=input_outer, anchor="nw")
    input_canvas.configure(yscrollcommand=input_scrollbar.set)
    
    input_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    input_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # 마우스 휠 스크롤 연동 (마우스가 입력 영역 위에 있을 때만 작동)
    def _on_mousewheel(event):
        # 내부 프레임 높이가 캔버스 고정 높이보다 클 때만 스크롤 작동
        if input_outer.winfo_height() > INPUT_AREA_HEIGHT:
            input_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    input_canvas.bind('<Enter>', lambda e: root.bind_all("<MouseWheel>", _on_mousewheel))
    input_canvas.bind('<Leave>', lambda e: root.unbind_all("<MouseWheel>"))

    all_entries = []  # [{field_name: widget, ...}, ...]

    for idx in range(n):
        reg = regions[idx]
        saved = reg.get('_saved_entries', {})
        n_pk = reg['n_peaks']

        frm = ttk.LabelFrame(input_outer, text=f"R{idx+1} ({n_pk} peak{'s' if n_pk>1 else ''})",
                               padding=4)
        frm.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3)
        cell = {}

        # ── Type toggle + Log ────────────────────────────────────────
        ctrl = ttk.Frame(frm)
        ctrl.grid(row=0, column=0, columnspan=6, sticky='ew', pady=(0, 4))

        cur_pt = region_types[idx]
        next_pt = TYPE_CYCLE[(TYPE_CYCLE.index(cur_pt) + 1) % len(TYPE_CYCLE)]
        type_var = tk.StringVar(value=cur_pt)
        cell['type_var'] = type_var

        status_lbl = ttk.Label(ctrl, text=TYPE_LABELS[cur_pt],
                                font=('', 9, 'bold'))
        status_lbl.pack(side=tk.LEFT, padx=3)
        cell['status_lbl'] = status_lbl

        def make_toggle_cb(i):
            def on_toggle():
                cur = region_types[i]
                ni = (TYPE_CYCLE.index(cur) + 1) % len(TYPE_CYCLE)
                new_t = TYPE_CYCLE[ni]
                # lazy refit if stale
                stale = regions[i].get('_stale', set())
                if new_t in stale:
                    prev = regions[i][cur]['params']
                    res = refit_region(
                        regions[i]['x'], regions[i]['y'], prev,
                        regions[i]['peak_positions'],
                        peak_type=new_t,
                        original_peak_ig=regions[i].get('original_peak_ig'),
                        mask_factor=regions[i].get('_last_mask_factor'))
                    regions[i][new_t] = res[new_t]
                    stale.discard(new_t)
                region_types[i] = new_t
                nxt = TYPE_CYCLE[(ni + 1) % len(TYPE_CYCLE)]
                all_entries[i]['toggle_btn'].configure(
                    text=f'→ {TYPE_LABELS[nxt]}')
                all_entries[i]['status_lbl'].configure(text=TYPE_LABELS[new_t])
                redraw(i, mpl_canvas)
            return on_toggle

        toggle_btn = ttk.Button(ctrl, text=f'→ {TYPE_LABELS[next_pt]}',
                                 command=make_toggle_cb(idx), width=14)
        toggle_btn.pack(side=tk.LEFT, padx=3)
        cell['toggle_btn'] = toggle_btn

        def make_log_cb(i):
            def on_log():
                cur = plot_axes[i].get_yscale()
                new_sc = 'log' if cur == 'linear' else 'linear'
                plot_axes[i].set_yscale(new_sc)
                all_entries[i]['log_btn'].configure(
                    text='Linear' if new_sc == 'log' else 'Log')
                mpl_canvas.draw()
            return on_log

        log_btn = ttk.Button(ctrl, text='Log', command=make_log_cb(idx), width=6)
        log_btn.pack(side=tk.LEFT, padx=3)
        cell['log_btn'] = log_btn

        # ── Header ───────────────────────────────────────────────────
        row = 1
        for ci, lbl in enumerate(['', 'from', 'value', 'to']):
            ttk.Label(frm, text=lbl, foreground='gray',
                       font=('', 8)).grid(row=row, column=ci, padx=2)

        # ── a, b, c 입력 ────────────────────────────────────────────
        for pi, pname in enumerate(['a', 'b', 'c']):
            r = row + 1 + pi
            ttk.Label(frm, text=pname, font=('', 9, 'bold')).grid(
                row=r, column=0, padx=2, sticky='e')
            for ci, sfx in enumerate(['_lb', '', '_ub']):
                key = f'{pname}{sfx}'
                e = ttk.Entry(frm, width=10, justify='center')
                e.grid(row=r, column=ci + 1, padx=2, pady=1)
                if key in saved:
                    e.insert(0, saved[key])
                cell[key] = e

        # ── mean 입력 (peak별) ───────────────────────────────────────
        mean_row_start = row + 4
        ttk.Separator(frm, orient='horizontal').grid(
            row=mean_row_start, column=0, columnspan=6, sticky='ew', pady=3)

        for j in range(n_pk):
            r = mean_row_start + 1 + j
            ttk.Label(frm, text=f'μ{j+1}', font=('', 9, 'bold')).grid(
                row=r, column=0, padx=2, sticky='e')

            fix_var = tk.BooleanVar(value=saved.get(f'mean{j}_fix', False))
            cell[f'mean{j}_fix_var'] = fix_var

            mean_entries = {}
            for ci, sfx in enumerate(['_lb', '', '_ub']):
                key = f'mean{j}{sfx}'
                e = ttk.Entry(frm, width=10, justify='center')
                e.grid(row=r, column=ci + 1, padx=2, pady=1)
                if key in saved:
                    e.insert(0, saved[key])
                cell[key] = e
                mean_entries[sfx] = e

            def make_fix_cb(entries_dict, var):
                def on_fix():
                    fixed = var.get()
                    st = 'disabled' if fixed else 'normal'
                    entries_dict['_lb'].configure(state=st)
                    entries_dict['_ub'].configure(state=st)
                return on_fix

            cb = ttk.Checkbutton(frm, text='fix', variable=fix_var,
                                  command=make_fix_cb(mean_entries, fix_var))
            cb.grid(row=r, column=4, padx=2)
            cell[f'mean{j}_fix_cb'] = cb

            # 초기 상태 반영
            if fix_var.get():
                mean_entries['_lb'].configure(state='disabled')
                mean_entries['_ub'].configure(state='disabled')

        # ── mask 입력 ────────────────────────────────────────────────
        mask_row = mean_row_start + 1 + n_pk
        ttk.Label(frm, text='mask(×FWHM)', foreground='gray',
                   font=('', 8)).grid(row=mask_row, column=0, columnspan=2, padx=2)
        e_mask = ttk.Entry(frm, width=8, justify='center')
        e_mask.insert(0, saved.get('mask', '2.5'))
        e_mask.grid(row=mask_row, column=2, padx=2, pady=1)
        cell['mask'] = e_mask

        # ── Buttons ──────────────────────────────────────────────────
        btn_row = mask_row + 1

        def make_refit_cb(i):
            def on_refit():
                reg_r = regions[i]
                pt = region_types[i]
                prev_params = reg_r[pt]['params']
                cl = all_entries[i]

                def parse(entry):
                    if isinstance(entry, ttk.Entry):
                        txt = entry.get().strip()
                    else:
                        txt = str(entry).strip()
                    if txt == '': return None
                    try: return float(txt)
                    except ValueError: return None

                bkg_ov = tuple(parse(cl[p]) for p in ['a', 'b', 'c'])
                bkg_margins = []
                for pn in ['a', 'b', 'c']:
                    lb_m, ub_m = parse(cl[f'{pn}_lb']), parse(cl[f'{pn}_ub'])
                    bkg_margins.append((lb_m, ub_m) if lb_m is not None or ub_m is not None else None)
                if all(m is None for m in bkg_margins):
                    bkg_margins = None

                mask_f = parse(cl['mask'])

                # mean overrides
                mean_ov = []
                for j in range(reg_r['n_peaks']):
                    val = parse(cl.get(f'mean{j}'))
                    lb_f = parse(cl.get(f'mean{j}_lb'))
                    ub_f = parse(cl.get(f'mean{j}_ub'))
                    fixed = cl.get(f'mean{j}_fix_var', tk.BooleanVar()).get()
                    if val is not None or lb_f is not None or ub_f is not None or fixed:
                        mean_ov.append((val, lb_f, ub_f, fixed))
                    else:
                        mean_ov.append(None)
                if all(m is None for m in mean_ov):
                    mean_ov = None

                print(f"  Re-fit R{i+1} ({pt})")
                new_result = refit_region(
                    reg_r['x'], reg_r['y'], prev_params,
                    reg_r['peak_positions'], bkg_ov, bkg_margins,
                    peak_type=pt,
                    original_peak_ig=reg_r.get('original_peak_ig'),
                    mask_factor=mask_f,
                    mean_overrides=mean_ov)

                reg_r[pt] = new_result[pt]
                reg_r['n_peaks'] = new_result['n_peaks']
                for o in TYPE_CYCLE:
                    if o != pt:
                        reg_r.setdefault('_stale', set()).add(o)
                reg_r['_last_mask_factor'] = mask_f
                redraw(i, mpl_canvas)
            return on_refit

        ttk.Button(frm, text='Fit this peak again',
                    command=make_refit_cb(idx)).grid(
            row=btn_row, column=0, columnspan=5, padx=2, pady=2, sticky='ew')

        def make_reset_cb(i):
            def on_reset():
                _save_all_entries()
                regions[i]['_saved_type'] = region_types[i]
                return_state['action'] = 'reset'
                return_state['region_ri'] = i
                return_state['sheet_name'] = sheet_name
                plt.close(fig)
                root.destroy()
            return on_reset

        ttk.Button(frm, text='Reset peaks',
                    command=make_reset_cb(idx)).grid(
            row=btn_row + 1, column=0, columnspan=5, padx=2, pady=(0, 2), sticky='ew')

        all_entries.append(cell)

    # ── Save entries helper ──────────────────────────────────────────
    def _save_all_entries():
        for i in range(n):
            cl = all_entries[i]
            saved = {}
            for key in ['a_lb', 'a', 'a_ub', 'b_lb', 'b', 'b_ub',
                         'c_lb', 'c', 'c_ub', 'mask']:
                w = cl.get(key)
                if w and isinstance(w, ttk.Entry):
                    saved[key] = w.get()
            for j in range(regions[i]['n_peaks']):
                for sfx in ['_lb', '', '_ub']:
                    k = f'mean{j}{sfx}'
                    w = cl.get(k)
                    if w and isinstance(w, ttk.Entry):
                        saved[k] = w.get()
                fv = cl.get(f'mean{j}_fix_var')
                if fv:
                    saved[f'mean{j}_fix'] = fv.get()
            regions[i]['_saved_entries'] = saved
            regions[i]['_saved_type'] = region_types[i]

    # ── Bottom bar ───────────────────────────────────────────────────
    bottom = ttk.Frame(root, padding=5)
    bottom.pack(fill=tk.X)

    def on_confirm():
        _save_all_entries()
        return_state['action'] = 'confirm'
        plt.close(fig)
        root.destroy()

    def on_close():
        _save_all_entries()
        return_state['action'] = 'confirm'
        plt.close(fig)
        root.destroy()

    ttk.Button(bottom, text='Confirm', command=on_confirm).pack(
        side=tk.RIGHT, padx=5)
    
    root.update_idletasks()  # 배치된 요소들의 필요 크기 계산
    
    # 창 테두리와 타이틀 바를 고려하여 너비와 높이에 여유 공간(Buffer) 추가
    req_width = root.winfo_reqwidth() + 20
    req_height = root.winfo_reqheight() + 40 
    
    # 사용자의 모니터 해상도 가져오기
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # 창 크기가 모니터 해상도를 넘지 않도록 방어 (윈도우 작업표시줄 등을 고려해 높이는 90%로 제한)
    win_width = min(req_width, int(screen_width * 0.95))
    win_height = min(req_height, int(screen_height * 0.90))
    
    # 화면 중앙에 창을 띄우기 위한 x, y 좌표 계산
    pos_x = int((screen_width - win_width) / 2)
    pos_y = int((screen_height - win_height) / 2)
    
    # 혹시라도 창이 모니터보다 커서 y좌표가 음수가 되면 상단 타이틀 바가 위로 숨어버리므로 방지
    pos_y = max(0, pos_y) 
    
    # 크기와 위치를 동시에 지정 (형식: "너비x높이+x좌표+y좌표")
    root.geometry(f"{win_width}x{win_height}+{pos_x}+{pos_y}")
    root.minsize(win_width, win_height)
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

    # ── Return ───────────────────────────────────────────────────────
    action = return_state.get('action', 'confirm')
    if action == 'reset':
        return return_state

    # confirm → assemble per-region results
    results = []
    for i, reg in enumerate(regions):
        pt = region_types[i]
        sel = reg[pt].copy()
        sel['selected_type'] = pt
        sel['n_peaks'] = reg['n_peaks']
        sel['range'] = reg['range']
        sel['x'] = reg['x']
        sel['y'] = reg['y']
        sel['peak_positions'] = reg['peak_positions']
        results.append(sel)

    return {'action': 'confirm', 'results': results,
            'region_types': region_types}
