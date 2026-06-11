# pyView.py
import matplotlib.pyplot as plt

# mypyfit 모듈로부터 필요한 함수 import
from FitFn_Spano import get_singleFit_params, func

def plot(hw, fit_ranges, lambda_sq, data_dict, fit_results):
    """
    Python의 matplotlib을 사용하여 데이터를 시각화.
    hw: 전체 X축 (Photon energy)
    fit_ranges: {data_key: [LB, UB]} 형태로, 각 데이터의 fitting 범위
    lambda_sq: 선택된 Huang-Rhys factor
    data_dict: {data_key: 시리즈}
    fit_results: perform_fitting()으로 얻은 결과
    """
    positions = [
        (1, 0), # i=0, 데이터1
        (0, 1), # i=1, 데이터2
        (0, 2), # i=2, 데이터3
        (1, 1), # i=3, 데이터4
        (1, 2), # i=4, 데이터5
        (2, 1), # i=5, 데이터6
        (2, 2)  # i=6, 데이터7
    ]

    fig, axes = plt.subplots(nrows=3, ncols=3, figsize=(12, 12), sharex=True)

    for i, (name, y) in enumerate(data_dict.items()):
        if i >= len(positions):
            break
        row, col = positions[i]
        ax = axes[row, col]

        # fitting 결과에서 파라미터 추출
        optimized_params, Gm_for_this = get_singleFit_params(fit_results, name, lambda_sq)
        if optimized_params is None:
            # fitting 실패 시
            ax.plot(hw, y, 'o', label='Raw Data', markersize=5)
            ax.set_title(f'({name}) λ²={lambda_sq} - Fit Failed', fontsize=12)
            continue

        base, W, C, E00, sigma, Cpol, Epol, sigma_pol = optimized_params
        fitted_curve = func(hw, base, W, C, E00, sigma, Cpol, Epol, sigma_pol, lambda_sq, Gm_for_this)

        # fit 범위 표시
        ax.axvline(fit_ranges[name][0], color='grey', linestyle='--', linewidth=1, label='LB of fit range')
        ax.axvline(fit_ranges[name][1], color='grey', linestyle='--', linewidth=1, label='UB of fit range')

        # 실제 데이터
        ax.plot(hw, y, 'o', label='Raw Data', markersize=5)
        # Vibronic / Polaronic / Total
        ax.plot(hw, fitted_curve[2] + base, 'o', label='Vibronic Contribution', alpha=0.7, markersize=4)
        ax.plot(hw, fitted_curve[3] + base, '^', label='Polaronic Contribution', alpha=0.7, markersize=4)
        ax.plot(hw, fitted_curve[0], '-', color='black', label='Fitted Curve', linewidth=2)

        # 개별 모드별 기여도
        for j in range(5):
            ax.plot(hw, fitted_curve[1][:, j] + base, '--', label=f'0-{j} Contribution', alpha=0.7)

        # 차이(Residual)를 시각적으로 보여주는 예시
        ax.fill_between(hw, y - fitted_curve[0], 0, color='blue', alpha=0.15)

        ax.set_title(f'({name}) λ²={lambda_sq}', fontsize=12)
        ax.set_xlabel('Photon Energy (eV)', fontsize=10)
        ax.set_ylabel('Absorption (a.u.)', fontsize=10)
        ax.grid(alpha=0.3)

    # 범례: 왼쪽 위에 하나만 표시
    handles, labels = axes[0, 1].get_legend_handles_labels()
    fig.legend(handles, labels, fontsize=8, loc='upper left', bbox_to_anchor=(0, 1), bbox_transform=axes[0,0].transAxes)

    plt.tight_layout()
    plt.show()
