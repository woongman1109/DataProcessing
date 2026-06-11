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
    fit_range, sigma_E0_init

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
    
    # 3) Data 가져오기

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

    # 4) Fitting 수행
    
    eta_fit_ranges_idx = []

    for i, s_value in enumerate(s_values):
        eta_fit_LB, eta_fit_UB = [0,0]
        for j, Seebeck in enumerate(df_S[i]):
            if Seebeck < S_data.max():
                if j-60 < 0:
                    eta_fit_LB = 1
                else:
                    eta_fit_LB = j - 60
                break
            
        for j, Seebeck in enumerate(df_S[i]):
            if Seebeck < S_data.min():
                if j + 500 > 1999:
                    eta_fit_UB = 1999
                else:
                    eta_fit_UB = j + 500
                break
            
        eta_fit_ranges_idx.append([eta_fit_LB, eta_fit_UB])

    sigma_E0_fit = []
    r2_fit = []
    df_fit_results = {}

    for i, s_value in enumerate(s_values):
        start_idx, end_idx = eta_fit_ranges_idx[i]
        eta_fit = df_eta.iloc[start_idx:end_idx].to_numpy()
        S_model_ref = df_S[i].iloc[start_idx:end_idx].to_numpy()
        F_s = df_Fn[f"F\\-({s_value})(\\i(η))"].iloc[start_idx:end_idx].to_numpy()
        F_s_1 = df_Fn[f"F\\-({s_value-1})(\\i(η))"].iloc[start_idx:end_idx].to_numpy()

        # residual 함수 정의
        def residuals(sigma_E0_array):
            sigma_E0 = sigma_E0_array[0]
            sigma_model = sigma_E0 * s_value * F_s_1
            S_model = (kB / e) * ((s_value + 1) * F_s / (s_value * F_s_1) - eta_fit)
            res_sigma = np.min((sigma_model[:, None] - sigma_data[None, :])**2, axis=0)
            res_S = np.min((S_model[:, None] - S_data[None, :])**2, axis=0)
            return np.concatenate([res_sigma, res_S])

        # least squares 최적화
        res = least_squares(residuals, x0=np.array([sigma_E0_init[i]]), bounds=(fit_range[i][0], fit_range[i][1]), method='trf', ftol=5e-16)
        sigma_E0_opt = res.x[0]
        sigma_E0_fit.append(sigma_E0_opt)

        # 최적화된 모델로 예측
        sigma_model = sigma_E0_opt * s_value * F_s_1
        S_model = (kB / e) * ((s_value + 1) * F_s / (s_value * F_s_1) - eta_fit)

        # 전체 reference target 대비 가장 가까운 예측값 선택
        sigma_pred = np.array([sigma_model[np.argmin((sigma_model - sx)**2)] for sx in sigma_data])
        S_pred = np.array([S_model[np.argmin((S_model - sy)**2)] for sy in S_data])

        # R² 계산
        r2_sigma = 1 - np.sum((sigma_data - sigma_pred)**2) / np.sum((sigma_data - np.mean(sigma_data))**2)
        r2_S = 1 - np.sum((S_data - S_pred)**2) / np.sum((S_data - np.mean(S_data))**2)
        r2_avg = (r2_sigma + r2_S) / 2
        r2_fit.append(r2_avg)

        # 결과 저장
        df_result = pd.DataFrame({
            'eta': eta_fit,
            'sigma_model': sigma_model,
            'S_model': S_model
        })
        df_fit_results[(sigma_E0_opt, r2_avg)] = df_result
    
    wb_report_LN = "KangSnyderFit_" + data_wb_LN
    wb_report = wrapBookFinder(wb_report_LN)
    ws_report_Name = "Fit-LeastSq_" + label
    ws_report = wrapSheetFinder(wb_report, ws_report_Name)
    ws_report.clear()

    for i, ((sigma_E0, r2), df_fitted) in enumerate(df_fit_results.items()):
        idx_start = i * len(df_fitted.columns)
        ws_report.from_df(df_fitted, idx_start)

        # 라벨 세팅
        ws_report.set_label(col=idx_start + 0, val=f"R²={r2:.4f}", type='C')
        ws_report.set_label(col=idx_start + 1, val=f"σ\-(Eo)={sigma_E0:.2e}", type='C')
        ws_report.set_label(col=idx_start + 2, val=f"s={s_values[i]}, σ\-(E0)={sigma_E0:.2e}", type='C')
    


    

except Exception as e:
    print("An error occurred:", e)

finally:
    # Origin 프로젝트 저장 & detach
    import originpro as op
    op.save()
    op.detach()