# Fermi-Dirac 적분 정의
from scipy.integrate import quad
def fermi_dirac(i, eta):
    integrand = lambda eps: eps**i / (1 + np.exp(eps - eta))
    result, _ = quad(integrand, 0, np.inf)
    return result

def compute_fermi_dirac_dataframe(df, i, eta_column):
    df_result = df.copy()
    df_result[f'F_{i}'] = df_result[eta_column].apply(lambda eta: fermi_dirac(i, eta))
    return df_result



# 2) η 입력
wb_KangSnyder = wrapBookFinder(KangSnyder_wb_LN)
wks_eta = wrapSheetFinder(wb_KangSnyder, etaF_ws_LN)
eta_arr = np.arange(*eta_range)
eta_label = "\i(η)"
df_etaF = pd.DataFrame({ eta_label : eta_arr })


print("=================η Transferred Successfully=================")


################################################################################################################################
################################################################################################################################

##================================================================================================================================================

# 3) F(η) 계산

i_val = np.array([0,1,2,3])
for j in i_val:
    label_F_i = f"F\-({j})(\i(η))"
    df_etaF[label_F_i] = compute_fermi_dirac_dataframe(df_etaF, j, eta_label)[f"F_{j}"]

wks_eta.from_df(df_etaF)
