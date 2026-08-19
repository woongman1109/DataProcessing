% ============================================================
%  strip_eta.m
%  param_PV.m 가 만든 4-param(PV) 변수에서 eta를 제거해
%  Gaussian용 3-param 변수로 덮어쓴다.
%
%  사용법 (Gaussian 피팅 파일):
%      param_PV;      % 4-param 로드
%      strip_eta;     % eta 제거 → 3-param
%
%  ※ param_PV 를 다시 부르면 변수가 4-param으로 리셋되므로,
%    param_PV 호출 직후에는 항상 strip_eta 를 짝지어 호출할 것.
% ============================================================

% --- 피크 초기값: eta 열(4번째) 제거 ---
pG_mat = pG_mat(:, 1:3);                  % nPeak×4 → nPeak×3
pG_arr = reshape(pG_mat.', 1, []);        % 다시 평탄화 [A μ FWHM, A μ FWHM, ...]
nPeak  = size(pG_mat, 1);                 % (개수는 그대로지만 명시적으로 갱신)

% --- 피크 경계: 4개씩 끊어 eta(4번째) 제거 후 재조립 ---
lbG_mat = reshape(lbG_arr, 4, []).';      % nPeak×4
ubG_mat = reshape(ubG_arr, 4, []).';
lbG_arr = reshape(lbG_mat(:, 1:3).', 1, []);   % eta 열 제거 후 평탄화
ubG_arr = reshape(ubG_mat(:, 1:3).', 1, []);

% --- pGB: eta(4번째) 제거 ---
pGB  = pGB(1:3);
lbGB = lbGB(1:3);
ubGB = ubGB(1:3);

% --- fittype 재생성: Gaussian 버전으로 ---
EqnBkg = makeGaussExpFittype(0);          % 배경만
Eqn    = makeGaussExpFittype(nPeak + 1);  % 진짜 피크 + pGB 1개

% 정리
clear lbG_mat ubG_mat
