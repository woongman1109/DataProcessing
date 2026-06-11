import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from Handler import OriginWrapper
from Handler.OriginWrapper import init_Project
from Handler.LabelFinder import Tr
import originpro as op
import numpy as np
import xlrd

opj_path = r"C:\Users\woong\Dropbox\==== SKKU-SAINT ====\==== SAINT-OSL ====\1. Research tmp\2024_PBFDO"
opj_name = "PBFDO_OECT.opju"
data_path = r"C:\Users\woong\Dropbox\==== SKKU-SAINT ====\==== SAINT-OSL ====\1. Research tmp\2024_PBFDO\VPS\260420_TLM"

# 필요한 설정값 이름을 상수로 정의
REQUIRED_SETTINGS = {"Device Terminal", "Name", "Forcing Function", "Number of Points"}


def getData(folder_path: str):
    """
    Reads all .xls files in the given folder path. For each .xls file:
      1) It collects sheets named 'Data' or starting with 'Append',
         forms a dictionary where each key is a column name (from row 1),
         and the corresponding values are lists containing the subsequent row values.
      2) It reads the 'Settings' sheet (always present), but only extracts rows whose
         first column is in REQUIRED_SETTINGS.
         In particular, if 'Forcing Function' contains 'Sweep' in any row, we store
         the corresponding 'Number of Points' in a single dict: {"nPoints": <...>}.

    :param folder_path: Path to the folder containing .xls files.
    :return: A nested dictionary, e.g.
      {
          "파일명": {
              "Data": {...},
              "Append...": {...},
              "Settings": {
                  "nPoints": 123
              }
          },
          ...
      }
    """

    results = {}

    for filename in os.listdir(folder_path):
        # .xls 파일만 처리
        if filename.lower().endswith(".xls"):
            filepath = os.path.join(folder_path, filename)
            workbook = xlrd.open_workbook(filepath, on_demand=True)

            file_key = os.path.splitext(filename)[0]
            file_dict = {}

            # 1) Read ALL sheets
            sheet_names = workbook.sheet_names()
            for sheet_name in sheet_names:
                sheet = workbook.sheet_by_name(sheet_name)
                if sheet.nrows == 0:
                    continue

                # 첫 번째 행을 헤더로
                headers = [str(sheet.cell_value(0, col_idx)) for col_idx in range(sheet.ncols)]
                data_dict = {header: [] for header in headers}

                # 2행부터 실제 데이터
                for row_idx in range(1, sheet.nrows):
                    for col_idx in range(sheet.ncols):
                        cell_value = sheet.cell_value(row_idx, col_idx)
                        header = headers[col_idx]
                        data_dict[header].append(cell_value)

                file_dict[sheet_name] = data_dict

            # 2) Settings 시트에서 nPoints 추출 (별도 메타 키로 저장)
            if "Settings" in sheet_names:
                settings_sheet = workbook.sheet_by_name("Settings")
                settings_temp = {}

                for row_idx in range(settings_sheet.nrows):
                    row_values = settings_sheet.row_values(row_idx)
                    if not row_values or not row_values[0]:
                        continue
                    setting_name = str(row_values[0]).strip()
                    if setting_name in REQUIRED_SETTINGS:
                        settings_temp[setting_name] = row_values[1:]

                n_points_value = None
                ff_list = settings_temp.get("Forcing Function", [])
                np_list = settings_temp.get("Number of Points", [])

                for ff, np_val in zip(ff_list, np_list):
                    if "Sweep" in str(ff):
                        n_points_value = int(float(np_val))
                        break

                if n_points_value is not None:
                    file_dict["_meta"] = {"nPoints": n_points_value}

            if file_dict:
                results[file_key] = file_dict

    return results


def Transfer(data):
    """
    data: getData()의 결과물.

    - "Data"로 시작하는 시트: Tr 라벨 매칭 + 컬럼 재배치 + gradient 계산
    - "_meta": 내부용 메타데이터, 시트 생성 안 함
    - 나머지 시트 (Calc, Settings, Append 등): 그대로 raw copy
    """
    for file_key, sheet_dict in data.items():
        bname = file_key + "_py"
        wbook = OriginWrapper.wrapBookFinder(bname)
        if not wbook:
            continue

        for sheet_name, table in sheet_dict.items():
            # 내부 메타데이터는 건너뛰기
            if sheet_name == "_meta":
                continue

            wks = OriginWrapper.wrapSheetFinder(wbook, sheet_name)
            if not wks:
                continue

            headers = list(table.keys())

            # ===== Data 시트: Tr 로직 + gradient =====
            if sheet_name.startswith("Data"):
                for col_idx, header in enumerate(headers):
                    col_data = table[header]

                    if header in Tr:
                        label_obj = Tr[header]
                        ln = label_obj.lname
                        un = label_obj.unit
                        cmt = label_obj.comments or ""
                        ax = label_obj.axis
                    else:
                        ln = header
                        un = ""
                        cmt = ""
                        ax = 'N'  # Neither (기본값)

                    wks.from_list(
                        col=col_idx,
                        data=col_data,
                        lname=ln,
                        units=un,
                        comments=cmt,
                        axis=ax
                    )

                # 컬럼 재배치 (시트에 존재하는 컬럼만)
                col_order = [
                    ("GateV",  0),
                    ("DrainI", 1),
                    ("GateI",  2),
                ]
                for tr_key, target_pos in col_order:
                    if tr_key in headers:
                        OriginWrapper.move_col_by_longname(wks, Tr[tr_key].lname, target_pos)

                # DrainI 뒤 컬럼들을 gm 삽입 자리 확보용으로 이동
                if wks.cols > 3:
                    wks.move_cols(1, wks.cols - 2, 2)

                x_data = wks.to_list(0)
                y_data = wks.to_list(1)

                if len(x_data) >= 2 and len(y_data) >= 2:
                    arr_x = np.array(x_data, dtype=float)
                    arr_y = np.array(y_data, dtype=float)

                    with np.errstate(divide='ignore', invalid='ignore'):
                        dy_dx = np.gradient(arr_y, arr_x)
                    dy_dx = np.nan_to_num(dy_dx, nan=0.0, posinf=0.0, neginf=0.0)

                    wks.from_list(
                        col=2,
                        data=dy_dx.tolist(),
                        lname=r"\i(\b(g))\-(m)",
                        units='mS',
                        comments="numpy derivative of B",
                        axis='Y'
                    )

            # ===== 나머지 시트 (Calc, Settings 등): raw copy =====
            else:
                for col_idx, header in enumerate(headers):
                    col_data = table[header]
                    wks.from_list(
                        col=col_idx,
                        data=col_data,
                        lname=header,
                        axis='N'
                    )



# 아래는 테스트 / 메인 로직 예시
try:
    # 0) Origin 프로젝트 초기화
    init_Project(opj_path, opj_name)
    folder_path = data_path
    data = getData(folder_path)

    # Print the resulting dictionary (optional for debugging)
    for file, sheet_data in data.items():
        print(f"\n--- File: {file} ---")
        for sheet_name, table in sheet_data.items():
            if sheet_name == "_meta":
                print(f"  >> Meta: nPoints={table.get('nPoints')}")
                continue
            print(f"  >> Sheet: {sheet_name} ({'DATA' if sheet_name.startswith('Data') else 'RAW'})")
            for label, values in table.items():
                if sheet_name.startswith("Data") and label in Tr:
                    print(f"    {label} => {Tr[label].lname}")
                else:
                    preview = values[:3] if isinstance(values, list) else values
                    print(f"    {label}: {preview}...")

    # 실제 Origin으로 Transfer
    Transfer(data)

except Exception as e:
    print("An error occurred:", e)

finally:
    # Origin 프로젝트 저장 & detach
    op.save()
    op.detach()
