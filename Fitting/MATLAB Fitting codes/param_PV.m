% ============================================================
%  param_PV.m  —  Pseudo-Voigt 피팅용 파라미터 설정
%  피팅 루프 돌기 전에 run('param_PV.m') 또는 param_PV 로 호출.
%  값만 여기서 바꾸고 다시 부르면 되므로 전체 재실행 불필요.
%
%  피크 파라미터: [Amplitude, Mean, FWHM, eta]  (eta 0=Gauss, 1=Lorentz)
% ============================================================

% [pB]      expScale        slope       linearBG
pB =        [   1.3e1,      3.8,        80          ];
lb_bkg =    [pB(1)*0.001,   3.5,        pB(3)*0.1   ];
ub_bkg =    [pB(1)*1000,    pB(2)*1E3,  pB(3)*1.1   ];

% [pG]      Amplitude   Mean        FWHM        eta   (0=Gauss, 1=Lorentz)
pG1 = [     2E2,        0.525,       0.15,       0.5     ];
pG2 = [     0.5E2,      0.75,       0.08,       0.5     ];
pG3 = [     50,         1.29,       0.23,       0.5     ];
pG4 = [     80,         1.83,       0.23,       0.5     ];
pG_arr = [pG1, pG2, pG3, pG4];
nPeak  = numel(pG_arr)/4;             % 피크 개수 자동 산출 (피크당 4param)
pG_mat = reshape(pG_arr, 4, []).';    % nPeak×4 행렬: 각 행 = [amp, mean, FWHM, eta]

% 피크별 하한/상한 (eta는 [0,1] 범위)
lbG1 = [pG1(1)*0.001, pG1(2)-0.1,  pG1(3)-0.2 , 0];
lbG2 = [pG2(1)*0.001, pG2(2)-0.1, pG2(3)-0.1, 0];
lbG3 = [pG3(1)*0.001, pG3(2)-0.05, pG3(3)-0.1, 0];
lbG4 = [pG4(1)*0.001, pG4(2)-0.02, pG4(3)-0.1, 0];
lbG_arr = [lbG1, lbG2, lbG3, lbG4];

ubG1 = [pG1(1)*1000, pG1(2)+0.1,  pG1(3)+0.3 , 1];
ubG2 = [pG2(1)*100,  pG2(2)+0.1, pG2(3)+0.2 , 1];
ubG3 = [pG3(1)*100,  pG3(2)+0.02, pG3(3)+0.2 , 0.1];
ubG4 = [pG4(1)*100,  pG4(2)+0.03, pG4(3)+0.2 , 1];
ubG_arr = [ubG1, ubG2, ubG3, ubG4];

% Background용 pGB — eta=0 고정(순수 Gaussian). lb=ub=0 으로 자유도 제거
pGB =  [     100,        1.4,        0.90,       0    ];
lbGB = [pGB(1)*0.001, pGB(2)-0.3, pGB(3)-0.5, 0];
ubGB = [pGB(1)*100,   pGB(2)+0.15, pGB(3)+1.0, 0];


% --------------------------------------- %
% ---- 0인 값과 너무 낮은 이상치 마스킹 ---- %
% ----- n: 윈도우의 반경 -> 한쪽 길이 ------%
n = 50; 
window_size = 2*n + 1; 

% ------- 초기 Gaussian 마스킹 ------- %
% ----- Gaussian의 exp 흡수 방지 ------%
NOISE_MASK_FACTOR = 1.2;   % 피크 마스킹 범위 : ±NOISE_MASK_FACTOR × FWHM
BKG_MARGIN       = 0.001;  % StepB(2) 배경 파라미터 허용 범위 (±15%)
ForcedUnmask_head = 0.41;  
ForcedUnmask_tail = 2.2; 
weight_region_ratio = 0.7; % Step2 피크영역 가중치 폭 (FWHM 기준 배율)
