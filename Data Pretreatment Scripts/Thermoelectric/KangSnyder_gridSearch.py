import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from Handler.OriginWrapper import init_Project, wrapBookFinder, wrapSheetFinder, genBookName

from scipy.integrate import quad
import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from dataAssign import opj_path, opj_name, \
    KangSnyder_wb_name as KangSnyder_wb_LN, func_ws_name as func_ws_LN, \
    data_wb_name as data_wb_LN, data_ws_name as data_ws_LN, \
    fit_range as fit_range_raw


# 상수 및 s값 정의
kB = 1.380649e-23  # Boltzmann constant [J/K]
e = 1.60217663e-19  # elementary charge [C]
s_values = [1, 3]  # Kang-Snyder 지수

def compute_fermi_dirac_dataframe(df, i, eta_column):
    df_result = df.copy()
    df_result[f'F_{i}'] = df_result[eta_column].apply(lambda eta: fermi_dirac(i, eta))
    return df_result

# Fermi-Dirac 적분 정의
def fermi_dirac(i, eta):
    integrand = lambda eps: eps**i / (1 + np.exp(eps - eta))
    result, _ = quad(integrand, 0, np.inf)
    return result

# Kang-Snyder에서 S 계산식만 따로 정의
def calc_S_from_eta(eta, s, eps=1e-10):
    F_s = np.array([fermi_dirac(s, x) for x in eta])
    F_s_1 = np.array([fermi_dirac(s - 1, x) for x in eta])
    denominator = s * F_s_1
    denominator_safe = np.where(np.abs(denominator) < eps, eps, denominator)
    with np.errstate(divide='ignore', invalid='ignore'):
        S = (kB / e) * ((s + 1) * F_s / denominator_safe - eta)
    return S



# sigma와 S 모델 함수
def kang_snyder_model(eta, sigma_E0, s, eps=1e-10):
    F_s = np.array([fermi_dirac(s, x) for x in eta])
    F_s_1 = np.array([fermi_dirac(s - 1, x) for x in eta])
    denominator = s * F_s_1
    denominator_safe = np.where(np.abs(denominator) < eps, eps, denominator)
    with np.errstate(divide='ignore', invalid='ignore'):
        S = (kB / e) * ((s + 1) * F_s / denominator_safe - eta)
    sigma = sigma_E0 * s * F_s_1
    return sigma, S




try:
    ##================================================================================================================================================
    
    # 1) Origin 프로젝트 초기화
    init_Project(opj_path, opj_name)


    ##================================================================================================================================================

    # 2) η, F(η), S_1, S_3 가져오기
    wb_KangSnyder = wrapBookFinder(KangSnyder_wb_LN)
    wks_func = wrapSheetFinder(wb_KangSnyder, func_ws_LN)
    df_eta = wks_func.to_df(c1=0).iloc[:,0]
    df_Fn = wks_func.to_df(c1=0).iloc[:,1:5]
    df_S = [wks_func.to_df(c1=0).iloc[:,5], wks_func.to_df(c1=0).iloc[:,6]]

    
    ##================================================================================================================================================
    
    # 3) Data 가져오기 및 라벨 설정

    wb_Data = wrapBookFinder(data_wb_LN)
    wks_Data = wrapSheetFinder(wb_Data, data_ws_LN)

    # 2열 데이터 불러오기 및 numpy array로 변환
    df_data = wks_Data.to_df(cindex=0).iloc[:, 0:2]
    sigma_data = df_data.iloc[:, 0].to_numpy()
    S_data_uV = df_data.iloc[:, 1].to_numpy()
    S_data = S_data_uV * 1e-6

    # Data 라벨 설정
    label = wks_Data.get_label(1, 'C')
    
    ##================================================================================================================================================


    # 4) Fitting에 사용할 η 범위 자동 추출
    
    eta_fit_ranges_idx = []

    for i, s_value in enumerate(s_values):
        eta_fit_LB, eta_fit_UB = [0,0]
        for j, Seebeck in enumerate(df_S[i]):
            if Seebeck < S_data.max():
                eta_fit_LB = j - 100
                break
            
        for j, Seebeck in enumerate(df_S[i]):
            if Seebeck < S_data.min():
                eta_fit_UB = j + 2000
                break

        eta_fit_ranges_idx.append([eta_fit_LB, eta_fit_UB])

    ##================================================================================================================================================


    # 5) Fitting 수행

    sigma_E0_fit = []
    r2_fit = []
    df_fit_results = {}

    # grid search 정의
    fit_range = [[np.log10(fit_range_raw[0][0]),np.log10(fit_range_raw[0][1])], \
                 [np.log10(fit_range_raw[1][0]),np.log10(fit_range_raw[1][1])]]
    sigma_E0_fit = []
    min_total_error = np.inf

    for i, s_value in enumerate(s_values):
        sigma_E0_grid = np.logspace(fit_range[i][0], fit_range[i][1], 10000)
        sigma_E0_opt = 0
        
        for sigma_E0 in sigma_E0_grid:
            start_idx, end_idx = eta_fit_ranges_idx[i]
            eta_fit = df_eta.iloc[start_idx:end_idx].to_numpy()
            S_model_ref = df_S[i].iloc[start_idx:end_idx].to_numpy()
            F_s = df_Fn[f"F\\-({s_value})(\\i(η))"].iloc[start_idx:end_idx].to_numpy()
            F_s_1 = df_Fn[f"F\\-({s_value-1})(\\i(η))"].iloc[start_idx:end_idx].to_numpy()


            sigma_model = sigma_E0 * s_value * F_s_1
            S_model = (kB / e) * ((s_value + 1) * F_s / (s_value * F_s_1) - eta_fit)

            sigma_pred = np.array([sigma_model[np.argmin((sigma_model - sx)**2)] for sx in sigma_data])
            S_pred = np.array([S_model[np.argmin((S_model - sy)**2)] for sy in S_data])

            r2_sigma = 1 - np.sum((sigma_data - sigma_pred)**2) / np.sum((sigma_data - np.mean(sigma_data))**2)
            r2_S = 1 - np.sum((S_data - S_pred)**2) / np.sum((S_data - np.mean(S_data))**2)
            r2_avg = (r2_sigma + r2_S) / 2
            total_error = 1 - r2_avg

            if total_error < min_total_error:
                min_total_error = total_error
                sigma_E0_opt = sigma_E0
                best_r2 = r2_avg
                best_sigma_model = sigma_model.copy()
                best_S_model = S_model.copy()
        
        print(sigma_E0_opt)
        print(s_value)
            
        sigma_E0_fit.append(sigma_E0_opt)
        
        df_result = pd.DataFrame({
            'eta': eta_fit,
            'sigma_model': sigma_model,
            'S_model': S_model
        })
        df_fit_results[(sigma_E0_opt, r2_avg)] = df_result
    
    wb_report_LN = "KangSnyderFit_" + data_wb_LN
    wb_report = wrapBookFinder(wb_report_LN)
    ws_report_Name = "Fit-GridSrch_" + label
    ws_report = wrapSheetFinder(wb_report, ws_report_Name)
    ws_report.clear()

    for i, ((sigma_E0, r2), df_fitted) in enumerate(df_fit_results.items()):
        idx_start = i * len(df_fitted.columns)
        ws_report.from_df(df_fitted, idx_start)

        # 라벨 세팅
        ws_report.set_label(col=idx_start + 0, val=f"R²={r2:.4f}", type='C')
        ws_report.set_label(col=idx_start + 1, val=f"σ\-(E0)={sigma_E0:.2e}", type='C')
        ws_report.set_label(col=idx_start + 2, val=f"s={s_values[i]}, σ\-(E0)={sigma_E0:.2e}", type='C')
        ws_report.cols_axis('nxy', c1=idx_start, c2=idx_start+2)
    


    

except Exception as e:
    print("An error occurred:", e)

finally:
    # Origin 프로젝트 저장 & detach
    import originpro as op
    op.save()
    op.detach()