% ============================================================
%  param_PV.m  —  Pseudo-Voigt 피팅용 파라미터 설정
%  피팅 루프 돌기 전에 run('param_PV.m') 또는 param_PV 로 호출.
%  값만 여기서 바꾸고 다시 부르면 되므로 전체 재실행 불필요.
%
%  피크 파라미터: [Amplitude, Mean, FWHM, eta]  (eta 0=Gauss, 1=Lorentz)
% ============================================================

BGSF = 0.1; % * BG_ScalingFactor
Peak_ScalingFactor = 0.001;

% [pB]      expScale        slope       linearBG
pB =        [0.15 * BGSF,   25 * BGSF,        0.04 ];
lb_bkg =    [pB(1)*0.1,     pB(2)*0.6,       pB(3)*0.1   ];
ub_bkg =    [pB(1)*1.1,     pB(2)*1.2,       pB(3)*5   ];

% [pG]      Amplitude   Mean        FWHM        eta   (0=Gauss, 1=Lorentz)
pG1 = [     50,         0.55,       0.08,       0.5     ];
pG2 = [     10,         0.75,       0.20,       0.5     ];
pG3 = [     50,         1.28,       0.23,       0.5     ];
pG4 = [     80,         1.8,       0.23,       0.5     ];
pG_arr = [pG1, pG2, pG3, pG4];
pG_arr(1:4:end) = pG_arr(1:4:end) * Peak_ScalingFactor;
nPeak  = numel(pG_arr)/4;             % 피크 개수 자동 산출 (피크당 4param)
pG_mat = reshape(pG_arr, 4, []).';    % nPeak×4 행렬: 각 행 = [amp, mean, FWHM, eta]

% 피크별 하한/상한
lbG1 = [pG1(1)*0.5,     pG1(2)-0.05,    pG1(3)-0.012 ,    0];
lbG2 = [pG2(1)*0.001,   pG2(2)-0.12,    pG2(3)-0.1,     0];
lbG3 = [pG3(1)*0.001,   pG3(2)-0.05,    pG3(3)-0.3,     0.3];
lbG4 = [pG4(1)*0.001,   pG4(2)-0.12,    pG4(3)-0.1,     0.3];
lbG_arr = [lbG1, lbG2, lbG3, lbG4];

lbG_arr(1:4:end) = lbG_arr(1:4:end) * Peak_ScalingFactor;


ubG1 = [pG1(1)*1e3,     pG1(2)+0.02,    pG1(3)+0.02 ,    0.8];
ubG2 = [pG2(1)*5,       pG2(2)+0.1,     pG2(3)+0.2 ,    1];
ubG3 = [pG3(1)*100,     pG3(2)+0.05,    pG3(3)+0.2 ,    1];
ubG4 = [pG4(1)*100,     pG4(2)+0.025,    pG4(3)+0.3 ,    1];
ubG_arr = [ubG1, ubG2, ubG3, ubG4];

ubG_arr(1:4:end) = ubG_arr(1:4:end) * Peak_ScalingFactor;

% Background용 pGB — eta=0 고정(순수 Gaussian). lb=ub=0 으로 자유도 제거
% pGB 여러 개 가능: pGB1, pGB2, ... 를 pGB_arr로 묶어 관리
% [pGB]     Amplitude   Mean    FWHM    eta(고정 0)
pGB1 = [    20,        0.75,    0.7,   0   ];
pGB2 = [    30,       1.66,    0.90,   0   ];
pGB_arr = [pGB1, pGB2];
pGB_arr(1:4:end) = pGB_arr(1:4:end) * Peak_ScalingFactor;
nPGB    = numel(pGB_arr)/4;            % pGB 개수 자동 산출

lbGB1 = [pGB1(1)*0.1, pGB1(2)-0.2, pGB1(3)-0.5, 0];
lbGB2 = [pGB2(1)*0.8, pGB2(2)-0.02, pGB2(3)-0.3, 0];
lbGB_arr = [lbGB1, lbGB2];
lbGB_arr(1:4:end) = lbGB_arr(1:4:end) * Peak_ScalingFactor;

ubGB1 = [pGB1(1)*10,   pGB1(2)+0.02, pGB1(3)+0.5, 0];
ubGB2 = [pGB2(1)*100,   pGB2(2)+0.1, pGB2(3)+1.0, 0];
ubGB_arr = [ubGB1, ubGB2];
ubGB_arr(1:4:end) = ubGB_arr(1:4:end) * Peak_ScalingFactor;

% --------------------------------------- %
% ---- 0인 값과 너무 낮은 이상치 마스킹 ---- %
% ----- n: 윈도우의 반경 -> 한쪽 길이 ------%
n = 50; 
window_size = 2*n + 1; 

% ------- 초기 Gaussian 마스킹 ------- %
% ----- Gaussian의 exp 흡수 방지 ------%
NOISE_MASK_FACTOR = 1.2;   % 피크 마스킹 범위 : ±NOISE_MASK_FACTOR × FWHM
BKG_MARGIN        = 0.001;  % StepB(2) 배경 파라미터 허용 범위 (±15%)
ForcedUnmask_head = 0.42;  
ForcedUnmask_tail = 2.2; 
weight_region_ratio = 0.7; % Step2 피크영역 가중치 폭 (FWHM 기준 배율)
