# launcher.py
"""
시작 UI — .opju 파일 선택 + Workbook 이름 입력.
dataAssign.py를 대체하며, 파이썬 버전 호환성도 확인합니다.
"""

import sys
import os

# ── 파이썬 버전 체크 (3.11.x 권장 — Origin 2024/2025 기준) ──────────
REQUIRED_MAJOR = 3
REQUIRED_MINOR = 11  # Origin 2024+는 3.11 기반

def check_python_version():
    """
    실행 중인 Python 버전이 Origin과 호환되는지 확인.
    PyInstaller로 빌드한 exe는 빌드 시 Python이 내장되므로 이 체크를 건너뜀.
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller exe — 내장 Python이므로 빌드 시 이미 맞춰짐
        return True, ""

    v = sys.version_info
    if v.major != REQUIRED_MAJOR or v.minor != REQUIRED_MINOR:
        msg = (
            f"Python 버전 불일치!\n\n"
            f"현재 버전: Python {v.major}.{v.minor}.{v.micro}\n"
            f"필요 버전: Python {REQUIRED_MAJOR}.{REQUIRED_MINOR}.x\n\n"
            f"Origin 2024/2025는 Python {REQUIRED_MAJOR}.{REQUIRED_MINOR} 기반입니다.\n"
            f"버전이 다르면 Origin 연동 시 오류가 발생할 수 있습니다.\n\n"
            f"Python {REQUIRED_MAJOR}.{REQUIRED_MINOR}을 설치한 뒤 다시 실행하세요."
        )
        return False, msg
    return True, ""


# ── 조기 버전 체크 (GUI 없이도 동작) ─────────────────────────────────
_ver_ok, _ver_msg = check_python_version()
if not _ver_ok:
    # GUI가 아직 없을 수 있으므로 먼저 콘솔에 출력
    print(_ver_msg)
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        _app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "Python 버전 불일치", _ver_msg)
    except Exception:
        pass
    sys.exit(1)


# ── 여기부터는 버전 OK일 때만 실행 ────────────────────────────────────
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QGroupBox,
    QComboBox, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon

# 최근 사용 설정 저장 경로
_SETTINGS_FILE = Path.home() / ".giwaxs_fitter" / "last_session.json"


def _load_settings():
    try:
        return json.loads(_SETTINGS_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}

def _save_settings(d):
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')


class LauncherDialog(QDialog):
    """시작 설정 다이얼로그."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result_data = None
        self._wb_names = []      # Origin에서 읽어올 Workbook 목록
        self.init_ui()
        self.load_last()

    def init_ui(self):
        self.setWindowTitle("GIWAXS 1D Profile Fitter")
        self.setMinimumWidth(560)
        self.setFixedHeight(320)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── 제목 ─────────────────────────────────────────────────
        title = QLabel("GIWAXS 1D Profile Fitting")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Origin 프로젝트를 선택하고 피팅할 데이터 Workbook을 지정하세요.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #ddd;")
        layout.addWidget(sep)

        # ── .opju 파일 선택 ──────────────────────────────────────
        grp_file = QGroupBox("Origin 프로젝트 (.opju)")
        file_lay = QHBoxLayout(grp_file)
        self.txt_opju = QLineEdit()
        self.txt_opju.setPlaceholderText("파일 경로를 입력하거나 [찾아보기]를 클릭하세요")
        self.txt_opju.setReadOnly(False)
        file_lay.addWidget(self.txt_opju, stretch=1)

        btn_browse = QPushButton("찾아보기…")
        btn_browse.setFixedWidth(100)
        btn_browse.clicked.connect(self.browse_opju)
        file_lay.addWidget(btn_browse)
        layout.addWidget(grp_file)

        # ── Workbook 이름 ────────────────────────────────────────
        grp_wb = QGroupBox("데이터 Workbook 이름")
        wb_lay = QHBoxLayout(grp_wb)
        self.txt_wb = QComboBox()
        self.txt_wb.setEditable(True)
        self.txt_wb.setPlaceholderText("예: GZ_12-17_qz")
        self.txt_wb.setMinimumWidth(250)
        wb_lay.addWidget(self.txt_wb, stretch=1)

        btn_scan = QPushButton("Origin에서 스캔")
        btn_scan.setFixedWidth(120)
        btn_scan.setToolTip("현재 열려 있는 Origin 프로젝트에서 Workbook 목록을 가져옵니다")
        btn_scan.clicked.connect(self.scan_workbooks)
        wb_lay.addWidget(btn_scan)
        layout.addWidget(grp_wb)

        layout.addStretch()

        # ── 하단 버튼 ────────────────────────────────────────────
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()

        btn_cancel = QPushButton("취소")
        btn_cancel.setFixedWidth(90)
        btn_cancel.clicked.connect(self.reject)
        btn_lay.addWidget(btn_cancel)

        btn_run = QPushButton("▶  시작")
        btn_run.setFixedWidth(120)
        btn_run.setDefault(True)
        btn_run.setStyleSheet(
            "QPushButton { background-color: #2962FF; color: white; "
            "font-weight: bold; padding: 6px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #1E88E5; }"
        )
        btn_run.clicked.connect(self.accept_action)
        btn_lay.addWidget(btn_run)
        layout.addLayout(btn_lay)

    # ── 파일 선택 ────────────────────────────────────────────────
    def browse_opju(self):
        start_dir = str(Path(self.txt_opju.text()).parent) if self.txt_opju.text() else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Origin 프로젝트 선택", start_dir,
            "Origin Project (*.opju *.opj);;All Files (*)"
        )
        if path:
            self.txt_opju.setText(path)

    # ── Origin Workbook 스캔 ─────────────────────────────────────
    def scan_workbooks(self):
        """Origin COM을 통해 현재 프로젝트의 Workbook 목록을 가져옵니다."""
        try:
            import originpro as op
            op.attach()
            names = []
            # 폴더 탐색하여 Workbook 이름 수집
            folder = op.pe.root
            self._collect_wb_names(names)
            if names:
                self.txt_wb.clear()
                self.txt_wb.addItems(sorted(set(names)))
                self.txt_wb.showPopup()
            else:
                QMessageBox.information(self, "스캔 결과", "열려 있는 Workbook이 없습니다.")
        except Exception as e:
            QMessageBox.warning(
                self, "Origin 연결 실패",
                f"Origin에 연결할 수 없습니다.\n먼저 Origin을 실행하고 프로젝트를 열어주세요.\n\n{e}"
            )

    @staticmethod
    def _collect_wb_names(names):
        """originpro를 사용하여 Workbook 이름들을 수집."""
        import originpro as op
        idx = 0
        while True:
            try:
                wb = op.find_book(type='w')
                # find_book은 단일 결과만 반환하므로 workaround 사용
                break
            except:
                break
        # LabTalk 방식으로 모든 Workbook 이름 수집
        try:
            page_names = op.get_lt_str('System.Pages.Name$')
            if page_names:
                for name in page_names.split('|'):
                    name = name.strip()
                    if name:
                        names.append(name)
        except:
            pass

    # ── 최근 설정 저장/로드 ──────────────────────────────────────
    def load_last(self):
        s = _load_settings()
        if 'opju_path' in s:
            self.txt_opju.setText(s['opju_path'])
        if 'wb_name' in s:
            self.txt_wb.setCurrentText(s['wb_name'])

    def save_current(self):
        _save_settings({
            'opju_path': self.txt_opju.text().strip(),
            'wb_name': self.txt_wb.currentText().strip(),
        })

    # ── 확인 ─────────────────────────────────────────────────────
    def accept_action(self):
        opju = self.txt_opju.text().strip()
        wb = self.txt_wb.currentText().strip()

        if not opju:
            QMessageBox.warning(self, "입력 필요", ".opju 파일 경로를 지정하세요.")
            return
        if not os.path.isfile(opju):
            QMessageBox.warning(self, "파일 없음", f"파일을 찾을 수 없습니다:\n{opju}")
            return
        if not wb:
            QMessageBox.warning(self, "입력 필요", "데이터 Workbook 이름을 입력하세요.")
            return

        opju_path = str(Path(opju).parent)
        opju_name = Path(opju).name

        self.result_data = {
            'opju_path': opju_path,
            'opju_name': opju_name,
            'data_wb_name': wb,
        }
        self.save_current()
        self.accept()


def run_launcher():
    """
    런처를 실행하고 사용자 입력을 반환합니다.
    취소 시 None 반환.
    """
    app = QApplication.instance()
    created = False
    if app is None:
        app = QApplication(sys.argv)
        created = True

    dlg = LauncherDialog()
    if dlg.exec() == QDialog.DialogCode.Accepted:
        return dlg.result_data
    return None


# 직접 테스트용
if __name__ == '__main__':
    result = run_launcher()
    if result:
        print("Settings:", result)
    else:
        print("Cancelled.")
