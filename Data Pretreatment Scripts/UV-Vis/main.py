import sys, os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from dataAssign import opj_path, opj_name, Huang_Rhys_index, \
    lambda_wb_name as lambda_wb_LN, lambda_ws_name as lambda_ws_LN, \
    data_wb_name as data_wb_LN, data_ws_name as data_ws_LN

from Handler.OriginWrapper import init_Project, wrapBookFinder, wrapSheetFinder
from OriginInterface import get_report_book, originTransfer
from FitFn_Spano import perform_fitting, get_singleFit_params, calculate_Gm
from pyView import plot


try:
    ##================================================================================================================================================
    
    # 1) Origin 프로젝트 초기화
    init_Project(opj_path, opj_name)


    ##================================================================================================================================================

    # 2) Huang-Rhys factor 등 읽어들이기
    wb_lambda = wrapBookFinder(lambda_wb_LN)
    wks_lambda = wrapSheetFinder(wb_lambda, lambda_ws_LN)
    lambda_squared_values = [float(cmt) for cmt in wks_lambda.get_labels('C')[1:]]
    lambda_squared_to_show = lambda_squared_values[Huang_Rhys_index]
    # print([float(comments) for comments in wks_lambda.get_labels('C')[1:]])

    # Calculate Gm for m = 0, 1, 2, 3, 4
    m_values = wks_lambda.to_df(c1=0, numcols=1).iloc[:, 0]
    GmVals = {
        lam_sq: [calculate_Gm(lam_sq, m) for m in m_values]
        for lam_sq in lambda_squared_values
    }


    ##================================================================================================================================================
    
    # 3) Get data for fitting (in [nm])
    wb_data = wrapBookFinder(data_wb_LN)
    wks_data = wrapSheetFinder(wb_data, data_ws_LN)
    df_data = wks_data.to_df()

    # Get X-axis values
    x_nm = df_data.iloc[:, 0].values
    hw = 1240 / x_nm  # eV

    # Get Y-axis values
    data_cols = wks_data.get_labels()[2:wks_data.cols]  # 각 컬럼의 Label
    data_dict = df_data.iloc[:, 2:wks_data.cols].to_dict(orient='series')  # {label: series}
    
    print("=================Data Transferred Successfully=================")


    ##================================================================================================================================================
    
    # 4) 초기값(initial guess, ig) / Bounds / Fit 범위
    # ig for fitting
    ig_wb_name = data_wb_LN
    ig_ws_name = data_cols
    wb_ig = wrapBookFinder(ig_wb_name)
    wksArr_ig = [wrapSheetFinder(wb_ig, __wksName_ig) for __wksName_ig in ig_ws_name]


    # 데이터 범위 제한 (fitting 범위)
    fit_range_masks = {}
    ig_values = {}
    bounds = {}
    fit_ranges = {}

    for __wks_ig in wksArr_ig:
        __ig_key = __wks_ig.name
        fit_range_masks[__ig_key] = (hw >= float(__wks_ig.get_labels('C')[1])) & (hw <= float(__wks_ig.get_labels('C')[3]))
        fit_ranges[__ig_key] = [float(__wks_ig.get_labels('C')[1]), float(__wks_ig.get_labels('C')[3])]

        __lb = __wks_ig.to_df().iloc[:,1]
        __ig_val = __wks_ig.to_df().iloc[:,2]
        __ub = __wks_ig.to_df().iloc[:,3]
        ig_values[__ig_key] = __ig_val
        bounds[__ig_key] = (__lb, __ub)

    print("=================Parameters Transferred Successfully=================")

    # 5) Fitting 수행
    fit_results = perform_fitting(
        data_dict=data_dict,
        hw=hw,
        fit_range_masks=fit_range_masks,
        ig_values=ig_values,
        GmVals=GmVals,
        lambda_squared_values=lambda_squared_values,
        bounds=bounds
    )

    lambda_squared_to_show = lambda_squared_values[0]

    '''
    # 6) Python에서 그래프 표시
    plot(hw, fit_ranges, lambda_squared_to_show, data_dict, fit_results)
    '''
    
    ##================================================================================================================================================
    
    # 7) Origin으로 fitting 결과 전송
    wb_report = get_report_book(data_wb_LN)
    wb_params = wb_data  # 예시로 동일 Book에 파라미터 sheet가 있다고 가정

    for label, y in data_dict.items():
        optimized_params, Gm_for_this = get_singleFit_params(fit_results, label, lambda_squared_to_show)
        if optimized_params is not None:
            originTransfer(
                range_lb=hw[0],
                range_ub=hw[-1],
                nPoints=500,
                __reportWBook=wb_report,
                __paramWBook=wb_params,
                __SName=label,
                base=optimized_params[0],
                W=optimized_params[1],
                C=optimized_params[2],
                E00=optimized_params[3],
                sigma=optimized_params[4],
                Cpol=optimized_params[5],
                Epol=optimized_params[6],
                sigma_pol=optimized_params[7],
                lambda_squared=lambda_squared_to_show,
                Gm_vals=Gm_for_this
            )

except Exception as e:
    print("An error occurred:", e)

finally:
    # Origin 프로젝트 저장 & detach
    import originpro as op
    op.save()
    op.detach()