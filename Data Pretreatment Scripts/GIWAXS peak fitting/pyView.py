# pyView.py
"""
Fitting 결과 시각화 — PyQt6 + matplotlib 하이브리드.
네이티브 단축키(QShortcut) 지원 및 마우스 클릭 초기값(ig) 보존.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QTableWidget, QTableWidgetItem, QAbstractItemView,
                             QScrollArea, QGroupBox, QLineEdit, QDialog, QHeaderView)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QClipboard, QShortcut

from FitFn_GaussExp import (model_func, unpack_params, refit_region,
                            _make_peak_mask, PEAK_TYPES, _npp)

# ── COM-safe 클립보드 헬퍼 (Origin COM과 PyQt6 충돌 방지) ────────────
def _clipboard_set(text):
    """COM 초기화 후 클립보드에 텍스트 설정."""
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception:
        pass
    cb = QApplication.clipboard()
    cb.clear(mode=QClipboard.Mode.Clipboard)
    cb.setText(text, mode=QClipboard.Mode.Clipboard)

def _clipboard_get():
    """COM 초기화 후 클립보드에서 텍스트 읽기."""
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception:
        pass
    return QApplication.clipboard().text(mode=QClipboard.Mode.Clipboard)

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
TYPE_CYCLE = list(PEAK_TYPES)
TYPE_BTN_LABELS = {'pseudo_voigt': 'PV', 'gaussian': 'G', 'lorentzian': 'L'}

def _valid_mask(y):
    return np.isfinite(y) & (y != 0)

def _compute_stats(x, y, params, peak_type):
    valid = _valid_mask(y)
    if not valid.any(): return None, None
    y_v, t_v = y[valid], model_func(x, params, peak_type)[0][valid]
    dof = max(len(y_v) - len(params), 1)
    ss_res = np.sum((y_v - t_v) ** 2)
    ss_tot = np.sum((y_v - np.mean(y_v)) ** 2)
    return (1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0), ss_res / dof

# =============================================================================
# 커스텀 QTableWidget
# =============================================================================
class SpreadsheetTable(QTableWidget):
    def __init__(self, rows, cols):
        super().__init__(rows, cols)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().hide()
        
        self.shortcut_copy = QShortcut(QKeySequence.StandardKey.Copy, self)
        self.shortcut_copy.activated.connect(self.copy)
        
        self.shortcut_paste = QShortcut(QKeySequence.StandardKey.Paste, self)
        self.shortcut_paste.activated.connect(self.paste)

    def copy(self):
        selection = self.selectedRanges()
        if not selection: return
        r = selection[0]
        text = ""
        for i in range(r.topRow(), r.bottomRow() + 1):
            row_data = []
            for j in range(r.leftColumn(), r.rightColumn() + 1):
                item = self.item(i, j)
                if j == 2:
                    if item and (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                        state = "TRUE" if item.checkState() == Qt.CheckState.Checked else "FALSE"
                        row_data.append(state)
                    else:
                        row_data.append("—")
                else:
                    row_data.append(item.text().strip() if item else "")
            text += "\t".join(row_data) + "\n"
        
        _clipboard_set(text)
        print("  [Copied via Ctrl+C]")

    def paste(self):
        text = _clipboard_get()
        if not text: return
        
        text = text.replace('\r', '').strip('\n')
        ranges = self.selectedRanges()
        if not ranges: return
        start_row, start_col = ranges[0].topRow(), ranges[0].leftColumn()
        
        for i, line in enumerate(text.split('\n')):
            r = start_row + i
            if r >= self.rowCount(): break
            for j, val in enumerate(line.split('\t')):
                c = start_col + j
                if c >= self.columnCount(): break
                item = self.item(r, c)
                
                if not item:
                    item = QTableWidgetItem()
                    self.setItem(r, c, item)
                
                if item.flags() & Qt.ItemFlag.ItemIsEditable:
                    item.setText(val.strip())
                elif c == 2 and (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                    state = Qt.CheckState.Checked if val.strip().upper() in ('TRUE', '1', 'T') else Qt.CheckState.Unchecked
                    item.setCheckState(state)

# =============================================================================
# 메인 윈도우 클래스
# =============================================================================
class FitWindow(QMainWindow):
    def __init__(self, sheet_name, regions, data_dict):
        super().__init__()
        self.sheet_name = sheet_name
        self.regions = regions
        self.data_dict = data_dict
        self.n = len(regions)
        self.region_types = [r.get('_saved_type', 'pseudo_voigt') for r in regions]
        self.return_state = {'action': 'confirm'}
        
        self.plot_axes_main = []
        self.plot_axes_resid = []
        self.tables = []
        self.mask_inputs = []
        self.log_btns = []
        self.type_btns_dict = []

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Fitting Results — {self.sheet_name}")
        self.resize(1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        toolbar = QHBoxLayout()
        btn_eq = QPushButton("▼ Equations")
        btn_eq.clicked.connect(self.show_equations)
        toolbar.addWidget(btn_eq)

        for i in range(self.n):
            btn_log = QPushButton("Log")
            btn_log.clicked.connect(lambda checked, idx=i: self.toggle_log(idx))
            self.log_btns.append(btn_log)
            toolbar.addStretch()
            toolbar.addWidget(btn_log)
        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        fig_w, fig_h = 5.5 * self.n + 1.0, 3.0
        self.fig = plt.figure(figsize=(fig_w, fig_h))
        self.canvas = FigureCanvas(self.fig)
        main_layout.addWidget(self.canvas, stretch=3)

        MAIN_H, RESID_H, TOP_PAD = 2.2, 0.55, 0.45
        total_h = TOP_PAD + MAIN_H + RESID_H + 0.15
        
        def yf(y): return 1.0 - y / total_h
        def hf(h): return h / total_h
        xm, xg = 0.07, 0.04
        cw = (1.0 - 2 * xm - max(0, self.n - 1) * xg) / self.n
        
        for idx in range(self.n):
            x0 = xm + idx * (cw + xg)
            ax_m = self.fig.add_axes([x0, yf(TOP_PAD + MAIN_H), cw, hf(MAIN_H)])
            ax_r = self.fig.add_axes([x0, yf(TOP_PAD + MAIN_H + RESID_H), cw, hf(RESID_H)], sharex=ax_m)
            self.plot_axes_main.append(ax_m)
            self.plot_axes_resid.append(ax_r)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QHBoxLayout(scroll_content)

        for i in range(self.n):
            scroll_layout.addWidget(self.create_region_panel(i))

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, stretch=2)

        bot_layout = QHBoxLayout()
        bot_layout.addStretch()
        btn_confirm = QPushButton("Confirm")
        btn_confirm.setMinimumWidth(100)
        btn_confirm.clicked.connect(self.on_confirm)
        bot_layout.addWidget(btn_confirm)
        main_layout.addLayout(bot_layout)

        self.draw_all()

    def create_region_panel(self, i):
        group = QGroupBox()
        layout = QVBoxLayout(group)
        
        reg = self.regions[i]
        n_pk = reg['n_peaks']
        saved = reg.get('_saved_entries', {})
        
        title_lay = QHBoxLayout()
        title_lay.addWidget(QLabel(f"R{i+1} ({n_pk} peak{'s' if n_pk>1 else ''})"))
        
        def make_copy_cb(idx, table, cur_reg, btn_obj):
            def on_copy():
                lines = ["Param\tValue\tFix\tlb\tig\tub"]
                row_keys = [('a', 'a', True), ('b', 'b', True), ('c', 'c', True)]
                for j in range(cur_reg['n_peaks']):
                    row_keys.append((f'A{j}', f'A_{j+1}', True))
                    row_keys.append((f'mean{j}', f'μ_{j+1}', True))
                    row_keys.append((f'fwhm{j}', f'w_{j+1}', True))
                    row_keys.append((f'eta{j}', f'η_{j+1}', False))
                
                for r_idx, (pid, disp, has_in) in enumerate(row_keys):
                    val = table.item(r_idx, 1).text()
                    if has_in:
                        fix = 'TRUE' if table.item(r_idx, 2).checkState() == Qt.CheckState.Checked else 'FALSE'
                        lb = table.item(r_idx, 3).text()
                        ig = table.item(r_idx, 4).text()
                        ub = table.item(r_idx, 5).text()
                        lines.append(f"{disp}\t{val}\t{fix}\t{lb}\t{ig}\t{ub}")
                    else:
                        lines.append(f"{disp}\t{val}\t—\t—\t—\t—")
                
                text_to_copy = '\n'.join(lines)
                _clipboard_set(text_to_copy)
                print("  [Copied via Button]")

                btn_obj.setText("Copied!")
                QTimer.singleShot(1500, lambda: btn_obj.setText("Copy Data"))
            return on_copy
        
        btn_copy = QPushButton('Copy Data')
        title_lay.addStretch()
        title_lay.addWidget(btn_copy)
        
        btn_dict = {}
        for pt in reversed(TYPE_CYCLE):
            btn = QPushButton(TYPE_BTN_LABELS[pt])
            btn.setFixedWidth(40)
            btn.clicked.connect(lambda checked, idx=i, target=pt: self.change_type(idx, target))
            title_lay.addWidget(btn)
            btn_dict[pt] = btn
        self.type_btns_dict.append(btn_dict)
        layout.addLayout(title_lay)

        headers = ['Param', 'Value', 'Fix', 'lb', 'ig', 'ub']
        rows_count = 3 + (n_pk * 4)
        table = SpreadsheetTable(rows_count, len(headers))
        table.setHorizontalHeaderLabels(headers)
        
        btn_copy.clicked.connect(make_copy_cb(i, table, reg, btn_copy))
        
        param_list = []
        for p in ['a', 'b', 'c']: param_list.append((p, p, True))
        for j in range(n_pk):
            param_list.append((f'A{j}', f'A_{j+1}', True))
            param_list.append((f'mean{j}', f'μ_{j+1}', True))
            param_list.append((f'fwhm{j}', f'w_{j+1}', True))
            param_list.append((f'eta{j}', f'η_{j+1}', False))

        orig_bkg = reg.get('original_bkg_ig', (0, 2.0, 0))
        orig_peaks = reg.get('original_peak_ig', [])
        peak_positions = reg.get('peak_positions', [])

        for r_idx, (pid, disp, has_in) in enumerate(param_list):
            item_p = QTableWidgetItem(disp)
            item_p.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table.setItem(r_idx, 0, item_p)
            
            item_v = QTableWidgetItem("—")
            item_v.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            table.setItem(r_idx, 1, item_v)

            item_fix = QTableWidgetItem()
            if has_in:
                item_fix.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                item_fix.setCheckState(Qt.CheckState.Checked if saved.get(f'{pid}_fix') else Qt.CheckState.Unchecked)
            else:
                item_fix.setFlags(Qt.ItemFlag.ItemIsSelectable)
            table.setItem(r_idx, 2, item_fix)

            for c_idx, sfx in enumerate(['_lb', '', '_ub'], start=3):
                item_val = QTableWidgetItem(saved.get(f'{pid}{sfx}', ''))
                if has_in:
                    item_val.setFlags(Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    if not item_val.text():
                        if pid == 'a' and sfx == '': item_val.setText(f"{orig_bkg[0]:.4e}")
                        elif pid == 'b' and sfx == '': item_val.setText(f"{orig_bkg[1]:.4f}")
                        elif pid == 'c' and sfx == '': item_val.setText(f"{orig_bkg[2]:.4e}")
                        elif 'A' in pid and sfx == '':
                            j = int(pid.replace('A', ''))
                            if j < len(orig_peaks): item_val.setText(f"{orig_peaks[j][0]:.4e}")
                        elif 'mean' in pid:
                            if sfx == '_lb': item_val.setText('0.95')
                            elif sfx == '_ub': item_val.setText('1.05')
                            elif sfx == '': 
                                j = int(pid.replace('mean', ''))
                                if j < len(peak_positions): item_val.setText(f"{peak_positions[j][0]:.4f}")
                        elif 'fwhm' in pid and sfx == '':
                            j = int(pid.replace('fwhm', ''))
                            if j < len(orig_peaks): item_val.setText(f"{orig_peaks[j][2]:.4f}")
                else:
                    item_val.setFlags(Qt.ItemFlag.ItemIsSelectable)
                    item_val.setText('—')
                table.setItem(r_idx, c_idx, item_val)
                
        self.tables.append(table)
        layout.addWidget(table)

        bot_lay = QVBoxLayout()
        mask_lay = QHBoxLayout()
        mask_lay.addWidget(QLabel("mask(×FWHM):"))
        mask_input = QLineEdit(saved.get('mask', '2.5'))
        mask_input.setFixedWidth(60)
        self.mask_inputs.append(mask_input)
        mask_lay.addWidget(mask_input)
        mask_lay.addStretch()
        bot_lay.addLayout(mask_lay)

        btn_fit = QPushButton("Fit this peak again")
        btn_fit.clicked.connect(lambda checked, idx=i: self.refit_action(idx))
        bot_lay.addWidget(btn_fit)

        btn_reset = QPushButton("Reset peaks")
        btn_reset.clicked.connect(lambda checked, idx=i: self.reset_action(idx))
        bot_lay.addWidget(btn_reset)

        layout.addLayout(bot_lay)
        return group

    def draw_all(self):
        for i in range(self.n):
            self.update_type_btns(i)
            self.redraw(i)

    def redraw(self, idx):
        ax_m, ax_r = self.plot_axes_main[idx], self.plot_axes_resid[idx]
        reg = self.regions[idx]
        pt = self.region_types[idx]
        res = reg[pt]
        
        ax_m.cla(); ax_r.cla()
        total, bkg, peaks = model_func(reg['x'], res['params'], pt)
        valid = _valid_mask(reg['y'])

        pig = reg.get('original_peak_ig')
        mf = reg.get('_last_mask_factor')
        if pig is not None:
            pmask = _make_peak_mask(reg['x'], pig, factor=mf)
            in_mask, sx = False, None
            for j in range(len(reg['x'])):
                if pmask[j] and not in_mask:
                    sx, in_mask = reg['x'][j], True
                elif not pmask[j] and in_mask:
                    ax_m.axvspan(sx, reg['x'][j-1], alpha=0.10, color='gray', zorder=0)
                    in_mask = False
            if in_mask: ax_m.axvspan(sx, reg['x'][-1], alpha=0.10, color='gray', zorder=0)

        ax_m.plot(reg['x'][valid], reg['y'][valid], 'k-', lw=1, alpha=0.8, label='Data')
        ax_m.plot(reg['x'], bkg, '--', color='gray', lw=1, alpha=0.7, label='Bkg')
        colors = plt.cm.tab10(np.linspace(0, 1, max(reg['n_peaks'], 1)))
        for j, pk in enumerate(peaks):
            ax_m.plot(reg['x'], pk + bkg, '-', color=colors[j], lw=1, alpha=0.7, label=f'Pk{j+1}')
        ax_m.plot(reg['x'], total, '-', color='red', lw=1.5, label='Fit')
        ax_m.tick_params(labelbottom=False)

        if valid.any():
            resid = reg['y'][valid] - total[valid]
            ax_r.plot(reg['x'][valid], resid, '-', color='steelblue', lw=0.8, alpha=0.8)
            ax_r.axhline(0, color='gray', lw=0.5, ls='--')
            ax_r.set_ylabel('Residual', fontsize=8)

        handles, labels = ax_m.get_legend_handles_labels()
        if handles:
            ax_r.legend(handles, labels, loc='lower center', fontsize=7,
                        framealpha=0.7, ncol=len(labels), borderpad=0.3,
                        handlelength=1.2, columnspacing=0.8)

        ax_m.grid(alpha=0.2); ax_r.grid(alpha=0.2)
        ax_m.relim(); ax_m.autoscale_view()
        ax_r.relim(); ax_r.autoscale_view()

        s = "OK" if res['success'] else "FAIL"
        c = f"cost={res['cost']:.2e}" if res['cost'] else ""
        ax_m.text(0.0, 1.01, f"R{idx+1} [{s}] {c}", transform=ax_m.transAxes, fontsize=9, fontweight='bold')

        # ─── 복구된 통계 지표 (R^2, chi^2) 표시 코드 ───
        STATS_FS = 8
        abbr = {'gaussian': 'G', 'lorentzian': 'L', 'pseudo_voigt': 'PV'}
        lines = []
        for stat_name in ['R²', 'χ²ᵥ']:
            parts = [f'{stat_name}']
            for t in TYPE_CYCLE:
                r = reg.get(t)
                ab = abbr[t]
                if r and r.get('params') is not None:
                    r2, chi2 = _compute_stats(reg['x'], reg['y'], r['params'], t)
                    v = f'{r2:.4f}' if stat_name == 'R²' else f'{chi2:.1e}'
                    parts.append(f'[{ab}:{v}]' if t == pt else f'{ab}:{v}')
                else:
                    parts.append(f'{ab}:—')
            lines.append('  '.join(parts))
        stats_text = '\n'.join(lines)
        ax_m.text(1.0, 1.01, stats_text, transform=ax_m.transAxes, fontsize=STATS_FS, ha='right', va='bottom', fontfamily='monospace', color='#444444')
        # ──────────────────────────────────────────────

        self.update_table_values(idx, res['params'], reg['n_peaks'], pt)
        self.canvas.draw()

    def update_table_values(self, idx, params, n_peaks, peak_type):
        (a, b, c), pks = unpack_params(params, peak_type)
        table = self.tables[idx]
        cur_fit = {'a': a, 'b': b, 'c': c}
        
        table.item(0, 1).setText(f'{a:.4e}')
        table.item(1, 1).setText(f'{b:.4f}')
        table.item(2, 1).setText(f'{c:.4e}')

        for j in range(n_peaks):
            base_r = 3 + (j * 4)
            if j < len(pks):
                pk = pks[j]
                cur_fit[f'A{j}'] = pk[0]; cur_fit[f'mean{j}'] = pk[1]; cur_fit[f'fwhm{j}'] = pk[2]
                table.item(base_r, 1).setText(f'{pk[0]:.4e}')
                table.item(base_r+1, 1).setText(f'{pk[1]:.4f}')
                table.item(base_r+2, 1).setText(f'{pk[2]:.4f}')
                if peak_type == 'pseudo_voigt' and len(pk) > 3:
                    table.item(base_r+3, 1).setText(f'{pk[3]:.4f}')
                    cur_fit[f'eta{j}'] = pk[3]
                else:
                    table.item(base_r+3, 1).setText('—')
            else:
                for off in range(4): table.item(base_r+off, 1).setText('—')

        self.regions[idx]['_current_fit_dict'] = cur_fit

    def update_type_btns(self, i):
        cur = self.region_types[i]
        for pt, btn in self.type_btns_dict[i].items():
            btn.setText(f'◆ {TYPE_BTN_LABELS[pt]}' if pt == cur else TYPE_BTN_LABELS[pt])
            font = btn.font()
            font.setBold(pt == cur)
            btn.setFont(font)

    def change_type(self, idx, target_type):
        if self.region_types[idx] == target_type: return
        stale = self.regions[idx].get('_stale', set())
        if target_type in stale:
            prev = self.regions[idx][self.region_types[idx]]['params']
            res = refit_region(
                self.regions[idx]['x'], self.regions[idx]['y'], prev, self.regions[idx]['peak_positions'],
                peak_type=target_type, original_peak_ig=self.regions[idx].get('original_peak_ig'),
                mask_factor=self.regions[idx].get('_last_mask_factor'))
            self.regions[idx][target_type] = res[target_type]
            stale.discard(target_type)
        self.region_types[idx] = target_type
        self.update_type_btns(idx); self.redraw(idx)

    def toggle_log(self, i):
        ax = self.plot_axes_main[i]
        new_sc = 'log' if ax.get_yscale() == 'linear' else 'linear'
        ax.set_yscale(new_sc)
        ax.relim(); ax.autoscale_view()
        self.log_btns[i].setText('Linear' if new_sc == 'log' else 'Log')
        self.canvas.draw()

    def refit_action(self, idx):
        reg = self.regions[idx]
        pt = self.region_types[idx]
        prev_params = reg[pt]['params']
        table = self.tables[idx]
        cur_fit = reg.get('_current_fit_dict', {})

        def parse(txt):
            try: return float(txt) if txt.strip() else None
            except: return None

        bkg_ov = [None, None, None]
        bkg_margins = [None, None, None]

        keys = ['a', 'b', 'c']
        for i, k in enumerate(keys):
            if table.item(i, 2).checkState() == Qt.CheckState.Checked:
                bkg_ov[i] = cur_fit.get(k)
                bkg_margins[i] = (bkg_ov[i], bkg_ov[i])
            else:
                bkg_ov[i] = parse(table.item(i, 4).text())
                lb, ub = parse(table.item(i, 3).text()), parse(table.item(i, 5).text())
                if lb is not None or ub is not None: bkg_margins[i] = (lb, ub)

        bkg_ov = tuple(bkg_ov)
        if all(m is None for m in bkg_margins): bkg_margins = None

        mask_f = parse(self.mask_inputs[idx].text())

        amp_ov, mean_ov, fwhm_ov = [], [], []
        for j in range(reg['n_peaks']):
            base = 3 + (j * 4)
            
            if table.item(base, 2).checkState() == Qt.CheckState.Checked:
                v = cur_fit.get(f'A{j}')
                amp_ov.append((v, v, v))
            else:
                v = parse(table.item(base, 4).text())
                l, u = parse(table.item(base, 3).text()), parse(table.item(base, 5).text())
                if v is not None or l is not None or u is not None: amp_ov.append((v, l, u))
                else: amp_ov.append(None)

            if table.item(base+1, 2).checkState() == Qt.CheckState.Checked:
                v = cur_fit.get(f'mean{j}')
                mean_ov.append((v, v, v, False))
            else:
                v = parse(table.item(base+1, 4).text())
                l, u = parse(table.item(base+1, 3).text()), parse(table.item(base+1, 5).text())
                if v is not None or l is not None or u is not None: mean_ov.append((v, l, u, False))
                else: mean_ov.append(None)

            if table.item(base+2, 2).checkState() == Qt.CheckState.Checked:
                v = cur_fit.get(f'fwhm{j}')
                fwhm_ov.append((v, v, v))
            else:
                v = parse(table.item(base+2, 4).text())
                l, u = parse(table.item(base+2, 3).text()), parse(table.item(base+2, 5).text())
                if v is not None or l is not None or u is not None: fwhm_ov.append((v, l, u))
                else: fwhm_ov.append(None)

        if all(a is None for a in amp_ov): amp_ov = None
        if all(m is None for m in mean_ov): mean_ov = None
        if all(f is None for f in fwhm_ov): fwhm_ov = None

        print(f"  Re-fit R{idx+1} ({pt})")
        new_res = refit_region(
            reg['x'], reg['y'], prev_params, reg['peak_positions'], bkg_ov, bkg_margins,
            peak_type=pt, original_peak_ig=reg.get('original_peak_ig'),
            mask_factor=mask_f, mean_overrides=mean_ov, fwhm_overrides=fwhm_ov, amp_overrides=amp_ov)

        reg[pt] = new_res[pt]
        reg['n_peaks'] = new_res['n_peaks']
        for o in TYPE_CYCLE:
            if o != pt: reg.setdefault('_stale', set()).add(o)
        reg['_last_mask_factor'] = mask_f
        self.redraw(idx)

    def save_entries(self):
        for idx in range(self.n):
            reg = self.regions[idx]
            table = self.tables[idx]
            saved = {'mask': self.mask_inputs[idx].text()}
            
            keys = [('a', 0), ('b', 1), ('c', 2)]
            for j in range(reg['n_peaks']):
                base = 3 + (j * 4)
                keys.append((f'A{j}', base))
                keys.append((f'mean{j}', base+1))
                keys.append((f'fwhm{j}', base+2))

            for pid, row in keys:
                saved[f'{pid}_fix'] = (table.item(row, 2).checkState() == Qt.CheckState.Checked)
                saved[f'{pid}_lb'] = table.item(row, 3).text()
                saved[f'{pid}'] = table.item(row, 4).text()
                saved[f'{pid}_ub'] = table.item(row, 5).text()
                
            reg['_saved_entries'] = saved
            reg['_saved_type'] = self.region_types[idx]

    def reset_action(self, idx):
        self.save_entries()
        self.regions[idx]['_saved_type'] = self.region_types[idx]
        self.return_state.update({'action': 'reset', 'region_ri': idx, 'sheet_name': self.sheet_name})
        self.close()

    def on_confirm(self):
        self.save_entries()
        self.return_state['action'] = 'confirm'
        self.close()

    def show_equations(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Fitting Equations")
        lay = QVBoxLayout(dlg)
        fig_eq, axes = plt.subplots(3, 1, figsize=(6, 1.5))
        for i, ax in enumerate(axes):
            ax.axis('off')
            ax.text(0.5, 0.5, EQ_LIST[i], transform=ax.transAxes, fontsize=10, ha='center', va='center')
        fig_eq.subplots_adjust(hspace=0.1, top=0.95, bottom=0.05)
        canvas_eq = FigureCanvas(fig_eq)
        lay.addWidget(canvas_eq)
        dlg.exec()

# =============================================================================
# 외부 호출 함수
# =============================================================================
# pyView.py 하단 plot_and_select 함수 부분만 수정

def plot_and_select(sheet_name, regions, data_dict=None):
    if len(regions) == 0:
        return {'action': 'confirm', 'results': [], 'region_types': []}

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        
    window = FitWindow(sheet_name, regions, data_dict)
    window.show()
    
    app.exec()
    
    state = window.return_state
    if state.get('action') == 'reset':
        return state

    results = []
    for i, reg in enumerate(regions):
        pt = window.region_types[i]
        sel = reg[pt].copy()
        sel.update({
            'selected_type': pt, 'n_peaks': reg['n_peaks'], 'range': reg['range'],
            'x': reg['x'], 'y': reg['y'], 'peak_positions': reg['peak_positions']
        })
        results.append(sel)

    return {'action': 'confirm', 'results': results, 'region_types': window.region_types}