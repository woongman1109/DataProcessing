% ============================================================
%  param_PV.m  —  Pseudo-Voigt 피팅용 파라미터 설정
%  피팅 루프 돌기 전에 run('param_PV.m') 또는 param_PV 로 호출.
%  값만 여기서 바꾸고 다시 부르면 되므로 전체 재실행 불필요.
%
%  피크 파라미터: [Amplitude, Mean, FWHM, eta]  (eta 0=Gauss, 1=Lorentz)
% ============================================================
% [pB]      expScale        slope       linearBG
pB =        [7.3,          4.2,        80          ];
lb_bkg =    [pB(1)*0.1,     3.5,        pB(3)*0.1   ];
ub_bkg =    [pB(1)*1.1,     8.0,        82   ];

% [pG]      Amplitude   Mean        FWHM        eta   (0=Gauss, 1=Lorentz)
pG1 = [     100,        0.555,       0.14,       0.5     ];
pG2 = [     80,         0.72,       0.21,       0.5     ];
pG3 = [     70,         1.29,       0.23,       0.5     ];
pG4 = [     120,         1.86,       0.25,       0.5     ];
pG_arr = [pG1, pG2, pG3, pG4];
nPeak  = numel(pG_arr)/4;             % 피크 개수 자동 산출 (피크당 4param)
pG_mat = reshape(pG_arr, 4, []).';    % nPeak×4 행렬: 각 행 = [amp, mean, FWHM, eta]

% 피크별 하한/상한 (★ 첫 프레임/고정 기준용 절대값 — 그대로 유지)
lbG1 = [pG1(1)*0.5,     pG1(2)-0.02,    pG1(3)-0.012 ,    0];
lbG2 = [pG2(1)*0.001,   pG2(2)-0.15,    pG2(3)-0.03,     0];
lbG3 = [pG3(1)*0.001,   pG3(2)-0.1,    pG3(3)-0.04,     0.3];
lbG4 = [pG4(1)*0.7,   pG4(2)-0.008,    pG4(3)-0.1,     0.3];
lbG_arr = [lbG1, lbG2, lbG3, lbG4];

ubG1 = [pG1(1)*1e3,     pG1(2)+0.02,    pG1(3)+0.03 ,    0.8];
ubG2 = [pG2(1)*100,       pG2(2)+0.1,     pG2(3)+0.03 ,    1];
ubG3 = [pG3(1)*100,     pG3(2)+0.05,    pG3(3)+0.2 ,    1];
ubG4 = [pG4(1)*1.5,     pG4(2)+0.2,    pG4(3)+0.3 ,    1];
ubG_arr = [ubG1, ubG2, ubG3, ubG4];

% ── ★ 위 값들에서 margin(배율/오프셋)만 자동으로 뽑아냄 ──
% amplitude: 배율(ratio), mean/FWHM: 오프셋(delta), eta: 절대범위 그대로 고정
pG_ampLBratio  = [lbG1(1)/pG1(1), lbG2(1)/pG2(1), lbG3(1)/pG3(1), lbG4(1)/pG4(1)];
pG_ampUBratio  = [ubG1(1)/pG1(1), ubG2(1)/pG2(1), ubG3(1)/pG3(1), ubG4(1)/pG4(1)];
pG_meanLBdelta = [lbG1(2)-pG1(2), lbG2(2)-pG2(2), lbG3(2)-pG3(2), lbG4(2)-pG4(2)];
pG_meanUBdelta = [ubG1(2)-pG1(2), ubG2(2)-pG2(2), ubG3(2)-pG3(2), ubG4(2)-pG4(2)];
pG_fwhmLBdelta = [lbG1(3)-pG1(3), lbG2(3)-pG2(3), lbG3(3)-pG3(3), lbG4(3)-pG4(3)];
pG_fwhmUBdelta = [ubG1(3)-pG1(3), ubG2(3)-pG2(3), ubG3(3)-pG3(3), ubG4(3)-pG4(3)];
pG_etaLB       = [lbG1(4), lbG2(4), lbG3(4), lbG4(4)];
pG_etaUB       = [ubG1(4), ubG2(4), ubG3(4), ubG4(4)];

% Background용 pGB — eta=0 고정(순수 Gaussian). lb=ub=0 으로 자유도 제거
% pGB 여러 개 가능: pGB1, pGB2, ... 를 pGB_arr로 묶어 관리
% [pGB]     Amplitude   Mean    FWHM    eta(고정 0)
pGB1 = [    15,        0.9,    0.9,   0   ];
pGB2 = [    40,       1.6,    0.9,   0   ];
pGB_arr = [pGB1, pGB2];
nPGB    = numel(pGB_arr)/4;            % pGB 개수 자동 산출

lbGB1 = [pGB1(1)*0.1, pGB1(2)-0.05, pGB1(3)-0.01, 0];
lbGB2 = [pGB2(1)*0.8, pGB2(2)-0.02, pGB2(3)-0.3, 0];
lbGB_arr = [lbGB1, lbGB2];

ubGB1 = [pGB1(1)*10,   pGB1(2)+0.055, pGB1(3)+0.11, 0];
ubGB2 = [pGB2(1)*1.1,   pGB2(2)+0.01, pGB2(3)+1.0, 0];
ubGB_arr = [ubGB1, ubGB2];

% ── ★ pGB도 동일하게 margin 추출 ──
pGB_ampLBratio  = [lbGB1(1)/pGB1(1), lbGB2(1)/pGB2(1)];
pGB_ampUBratio  = [ubGB1(1)/pGB1(1), ubGB2(1)/pGB2(1)];
pGB_meanLBdelta = [lbGB1(2)-pGB1(2), lbGB2(2)-pGB2(2)];
pGB_meanUBdelta = [ubGB1(2)-pGB1(2), ubGB2(2)-pGB2(2)];
pGB_fwhmLBdelta = [lbGB1(3)-pGB1(3), lbGB2(3)-pGB2(3)];
pGB_fwhmUBdelta = [ubGB1(3)-pGB1(3), ubGB2(3)-pGB2(3)];
pGB_etaLB       = [lbGB1(4), lbGB2(4)];
pGB_etaUB       = [ubGB1(4), ubGB2(4)];

% --------------------------------------- %
% ---- 0인 값과 너무 낮은 이상치 마스킹 ---- %
% ----- n: 윈도우의 반경 -> 한쪽 길이 ------%
n = 50;
window_size = 2*n + 1;
% ------- 초기 Gaussian 마스킹 ------- %
% ----- Gaussian의 exp 흡수 방지 ------%
NOISE_MASK_FACTOR = 1.2;   % 피크 마스킹 범위 : ±NOISE_MASK_FACTOR × FWHM
BKG_MARGIN       = 0.001;  % StepB(2) 배경 파라미터 허용 범위 (±15%)
ForcedUnmask_head = 0.42;
ForcedUnmask_tail = 2.2;
weight_region_ratio = 0.7; % Step2 피크영역 가중치 폭 (FWHM 기준 배율)