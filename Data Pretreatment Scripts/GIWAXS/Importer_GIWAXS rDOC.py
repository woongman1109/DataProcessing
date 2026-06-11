import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from Handler import OriginWrapper
from Handler.OriginWrapper import init_Project
from Handler.LabelFinder import Tr
import originpro as op
import pandas as pd
import numpy as np

opj_path = r""
opj_name = ""
data_path = r"C:\Users\woong\Dropbox\==== SKKU-SAINT ====\==== SAINT-OSL ====\1. Research tmp\2024_Operando GIWAXS\Experiments\GIWAXS\250432_3C\TWYoon\Operando\CF_2\CF_2_010_15s_0001"

# -----------------------------------------------------------------------------
# 1. CSV IMPORT HELPER
# -----------------------------------------------------------------------------

def getData(folder_path: str):
    """Load every two‑column CSV (X, Y) in *folder_path* and also
    return the *third* token when the **folder name** is split by "_".

    Example folder name  :  MC_1_004_15s_0001
    tokens              : [MC, 1, **004**, 15s, 0001]
    We return the **"004"** part as the extra value.
    """
    csv_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.csv')]
    if not csv_files:
        raise FileNotFoundError("No CSV files in folder")

    xs: list[float] | None = None
    ys: dict[str, list] = {}

    for fname in csv_files:
        fpath = os.path.join(folder_path, fname)
        df = pd.read_csv(fpath, header=None)
        if df.shape[1] < 2:
            continue
        x_col = df.iloc[:, 0].astype(float).tolist()
        y_col = df.iloc[:, 1].astype(float).tolist()

        if xs is None:
            xs = x_col
        elif len(x_col) != len(xs):
            print(f"[Skip] length mismatch in {fname}")
            continue

        ys[os.path.splitext(fname)[0]] = y_col

    if xs is None or not ys:
        raise RuntimeError("No valid CSVs with two columns were processed")

    # ── extract 3rd token of folder name ───────────────────────────────────────
    folder_tokens = os.path.basename(folder_path).split("_")
    third_token = folder_tokens[2] if len(folder_tokens) > 2 else ""

    return third_token, xs, ys

# -----------------------------------------------------------------------------
# 2. ORIGIN TRANSFER
# -----------------------------------------------------------------------------

def Transfer(token: str, x: list, ys: dict):
    """Send the assembled data to Origin worksheet in the structure:

    A (0) : common X
    B (1) : F(x) = sin(x/180*pi - pi/2)
    C..   : each CSV's Y column (order by dict key)
    Sum   : Σ(C..)
    Prod  : B * each C.. (one column per CSV)
    """
    bname = "rDOCCF2"
    wbook = OriginWrapper.wrapBookFinder(bname)

    wks = OriginWrapper.wrapSheetFinder(wbook, token + "azimuthal")

    # A column (X)
    wks.from_list(col=0, data=x, lname='X', units='')
    
    # B column: sin(x/180*pi - pi/2)
    rad = np.radians(np.array(x)) - np.pi/2
    f_col = np.sin(rad)
    wks.from_list(col=1, data=f_col.tolist(), lname='F(x)=sin', units='', comments='sin(x)')
    
    # C.. : Y columns
    start_y_idx = 2
    sorted_keys = sorted(ys.keys())
    for i, key in enumerate(sorted_keys):
        col_idx = start_y_idx + i
        wks.from_list(col=col_idx, data=ys[key], lname=key.split("_")[6], units='', comments='CSV Y')
        
    # Sum column
    y_matrix = np.array([ys[k] for k in sorted_keys], dtype=float)
    y_sum = np.sum(y_matrix, axis=0)
    sum_col_idx = start_y_idx + len(sorted_keys)
    wks.from_list(col=sum_col_idx, data=y_sum.tolist(), lname='ΣY', units='', comments='sum')

    # Product columns B*C..
    prod_start = sum_col_idx + 2  # leave one blank column as in spec
    wks._check_add_cols(needecols=sum_col_idx*2+1)
    for i, key in enumerate(sorted_keys):
        col_idx = prod_start + i
        wks.set_formula(col=col_idx, formula=f'B*col({col_idx-sum_col_idx+1})')
        wks.set_label(col=col_idx, val=f'F*{key.split("_")[6]}', type='L')

# -----------------------------------------------------------------------------

# 아래는 테스트 / 메인 로직 예시
try:
    # 0) Origin 프로젝트 초기화
    init_Project(opj_path, opj_name)
    ai, x_data, y_dict = getData(data_path)
    Transfer(ai, x_data, y_dict)

except Exception as e:
    print("An error occurred:", e)

finally:
    # Origin 프로젝트 저장 & detach
    op.save()
    op.detach()
