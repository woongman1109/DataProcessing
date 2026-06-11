# dataAssign.py
import sys, os, json, gc
from pathlib import Path

_SETTINGS_FILE = Path.home() / ".giwaxs_fitter" / "last_session.json"

def _load():
    try: return json.loads(_SETTINGS_FILE.read_text(encoding='utf-8'))
    except: return {}

def _save(d):
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')

def _run_launcher():
    from PyQt6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout,
                                  QLabel, QLineEdit, QPushButton, QFileDialog,
                                  QMessageBox, QGroupBox)
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont

    # Fresh QApplication — will be destroyed after dialog
    app = QApplication(sys.argv)

    prev = _load()

    dlg = QDialog()
    dlg.setWindowTitle("GIWAXS 1D Profile Fitter")
    dlg.setMinimumWidth(540)
    dlg.setFixedHeight(280)
    layout = QVBoxLayout(dlg)
    layout.setSpacing(10)

    lbl_title = QLabel("GIWAXS 1D Profile Fitting")
    lbl_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
    lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(lbl_title)

    lbl_sub = QLabel("Select Origin project and specify data workbook.")
    lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl_sub.setStyleSheet("color: #666;")
    layout.addWidget(lbl_sub)

    grp1 = QGroupBox("Origin Project (.opju)")
    g1_lay = QHBoxLayout(grp1)
    txt_opju = QLineEdit()
    txt_opju.setPlaceholderText("Browse or type path...")
    if prev.get('opju_full'):
        txt_opju.setText(prev['opju_full'])
    g1_lay.addWidget(txt_opju, stretch=1)

    def browse():
        start = str(Path(txt_opju.text()).parent) if txt_opju.text() else ""
        path, _ = QFileDialog.getOpenFileName(
            dlg, "Select Origin Project", start,
            "Origin Project (*.opju *.opj);;All Files (*)")
        if path:
            txt_opju.setText(path)

    btn_browse = QPushButton("Browse...")
    btn_browse.setFixedWidth(90)
    btn_browse.clicked.connect(browse)
    g1_lay.addWidget(btn_browse)
    layout.addWidget(grp1)

    grp2 = QGroupBox("Data Workbook Name")
    g2_lay = QHBoxLayout(grp2)
    txt_wb = QLineEdit()
    txt_wb.setPlaceholderText("e.g. GZ_12-17_qz")
    if prev.get('wb_name'):
        txt_wb.setText(prev['wb_name'])
    g2_lay.addWidget(txt_wb)
    layout.addWidget(grp2)

    layout.addStretch()

    btn_lay = QHBoxLayout()
    btn_lay.addStretch()

    btn_cancel = QPushButton("Cancel")
    btn_cancel.setFixedWidth(80)
    btn_cancel.clicked.connect(dlg.reject)
    btn_lay.addWidget(btn_cancel)

    btn_start = QPushButton("Start")
    btn_start.setFixedWidth(100)
    btn_start.setDefault(True)
    btn_start.setStyleSheet(
        "QPushButton{background:#2962FF;color:white;font-weight:bold;"
        "padding:6px;border-radius:4px;}"
        "QPushButton:hover{background:#1E88E5;}")
    btn_lay.addWidget(btn_start)
    layout.addLayout(btn_lay)

    result = {}

    def on_start():
        opju = txt_opju.text().strip()
        wb = txt_wb.text().strip()
        if not opju:
            QMessageBox.warning(dlg, "Input Required", "Select an .opju file.")
            return
        if not os.path.isfile(opju):
            QMessageBox.warning(dlg, "File Not Found", f"Cannot find:\n{opju}")
            return
        if not wb:
            QMessageBox.warning(dlg, "Input Required", "Enter a workbook name.")
            return
        result['opj_path'] = str(Path(opju).parent)
        result['opj_name'] = Path(opju).name
        result['data_wb_name'] = wb
        _save({'opju_full': opju, 'wb_name': wb})
        dlg.accept()

    btn_start.clicked.connect(on_start)

    accepted = dlg.exec() == QDialog.DialogCode.Accepted

    # ── Completely destroy QApplication ──────────────────────────
    # So main.py creates a brand new one with zero residual state.
    dlg.deleteLater()
    app.processEvents()
    app.quit()
    app.processEvents()
    del dlg
    del app
    gc.collect()
    # ─────────────────────────────────────────────────────────────

    if not accepted or not result:
        print("Cancelled.")
        sys.exit(0)

    return result

_s = _run_launcher()
opj_path = _s['opj_path']
opj_name = _s['opj_name']
data_wb_name = _s['data_wb_name']
