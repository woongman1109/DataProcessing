
% file load
clear
clc

dataName = "PEDOT_3_1Dplotstack_qz_forfit";
load PEDOT_3_1Dplotstack_qz_forfit.csv
q = PEDOT_3_1Dplotstack_qz_forfit(:,1);
I = PEDOT_3_1Dplotstack_qz_forfit(:,2:end);
clear PEDOT_3_1Dplotstack_qz_forfit
N = size(I,2);
%% accumulation
accum = 2;
exp_time = 6;
Na = N/accum;
Ia = zeros(length(q),Na);
Itemp = zeros(length(q),accum);
for ii = 1:Na
    for jj = 1:accum
        temp = I(:,((ii-1)*accum)+jj);
        Itemp(:,jj) = temp;
        disp(((ii-1)*accum)+jj);
    end
    Ia(:,ii) = median(Itemp,2,'omitnan');
end
   
%% plot
figure;
plot(q,Ia(:,1000));
%% q del
qdel = find(q>0.35 & q<0.93);
qs = q(qdel);
Is = Ia(qdel,:);

figure;
plot(qs,Is);

%%
targ = 378;
x = qs;
y = Is(:,targ);

p1 = 1.3e1; % exp Scale
p2 = 3.8; % slope
p3 = 140; % linear background

p4 = 2E2; % Gaussian Amplitude
p5 = 0.55; % Mean
p6 = 0.15; % FWHM

p7 = 0.5E2; % Gaussian Amplitude
p8 = 0.75; % Mean
p9 = 0.08; % FWHM

exb = expBKG(x,p1,p2,p3);
gb = Gaussian(x,p4,p5,p6,p7,p8,p9);

G = exb + gb;

figure(11);
plot(x,y,'-ok'); hold on
plot(x,exb); hold on
plot(x,gb); hold on
plot(x,G); hold off

%%
% ---- 0인 값과 너무 낮은 이상치 마스킹 ---- %
% ----- n: 윈도우의 반경 -> 한쪽 길이 ------%
n = 50; 
window_size = 2*n + 1; 

% ------- 초기 Gaussian 마스킹 ------- %
% ----- Gaussian의 exp 흡수 방지 ------%
FWHM_MASK_FACTOR = 1.2;   % 피크 마스킹 범위 : ±FWHM_MASK_FACTOR × FWHM
BKG_MARGIN       = 0.001;  % Step2 배경 파라미터 허용 범위 (±15%)
ForcedUnmask     = 0.02;  % 데이터 양끝 각 비율만큼은 마스킹 무시하고 배경 피팅에 강제 포함

for ii = 1006:1006
    y     = Is(:,ii);
    y_log = log(y);

    % --- 마스킹(Masking) 조건 설정 ---
    mask1 = (y == 0);                               % 1. 데이터가 0인 점 
    y_temp = y;                                     % 2. ----------------
    y_temp(mask1) = NaN;                            % 2-1. 0인 점들을 임시로 NaN 처리
    y_bridge = fillmissing(y_temp, 'linear');       % 2-2. 0으로 뻥 뚫린 구간을 양옆 정상 데이터 기준으로 직선을 그어 메꿈 (가상의 다리)
                                                    % 이렇게 하면 중간에 툭 튀는 점도 가상 기준선(약 400 근처)과 비교당하게 됩니다.
    local_ref = movmedian(y_bridge, window_size);   % 3. 메꿔진 가상의 궤도를 바탕으로 이동 중간값 계산 (omitnan 필요 없음)   
    mask2 = (y <= 0.9 * local_ref);                 % 4. 실제 데이터(y)가 정상 궤도(local_ref) 대비 90% 이하면 제외
    
    % 최종적으로 피팅에서 제외할 인덱스
    exclude_idx = mask1 | mask2 | (y <= 0) | ~isfinite(y_log);
    % --------------------------------

    % =========================================================
    %  Step 1 : 피크 영역을 가린 채 배경(expBKG)만 피팅
    % =========================================================

    % 현재 프레임의 초기 피크 위치·폭을 이용해 피크 구역 마스킹
    %   1번 피크: 중심 p5, FWHM p6
    %   2번 피크: 중심 p8, FWHM p9
    if ii == 1
        peak_centers = [p5, p8];
        peak_fwhms   = [p6, p9];
    else
        peak_centers = [parameter(ii-1, 5), parameter(ii-1, 8)];
        peak_fwhms   = [parameter(ii-1, 6), parameter(ii-1, 9)];
    end

    peak_mask = false(size(x));
    for pk_idx = 1:numel(peak_centers)
        half_range = peak_fwhms(pk_idx) * FWHM_MASK_FACTOR;
        peak_mask  = peak_mask | ...
            (x >= peak_centers(pk_idx) - half_range & ...
             x <= peak_centers(pk_idx) + half_range);
    end

    bkg_fit_mask = ~peak_mask & ~exclude_idx;

    % ── ForcedUnmask: 데이터 양끝 일정 비율은 강제로 배경 피팅에 포함 ──
    % (단, exclude_idx로 걸린 진짜 불량점은 여전히 제외)
    n_pts      = numel(x);
    n_edge     = round(n_pts * ForcedUnmask);
    forced_idx = false(n_pts, 1);
    forced_idx(1:n_edge)         = true;   % 앞쪽(낮은 q) 끝
    forced_idx(end-n_edge+1:end) = true;   % 뒤쪽(높은 q) tail
    bkg_fit_mask = (bkg_fit_mask | forced_idx) & ~exclude_idx;
    % ───────────────────────────────────────────────

    if sum(bkg_fit_mask) < 5          % 배경 포인트 부족하면 exclude만 적용
        bkg_fit_mask = ~exclude_idx;
    end

    x_bkg     = x(bkg_fit_mask);
    y_bkg     = y(bkg_fit_mask);
    y_bkg_log = log(y_bkg);

    % 3-파라미터 배경 전용 fittype
    EqnBkg = fittype(@(p1,p2,p3,x) log(expBKG(x,p1,p2,p3)), ...
        'independent', 'x', ...
        'coefficients', {'p1','p2','p3'});

    lb_bkg = [p1*0.001, p2*0.001, p3*0.1];
    ub_bkg = [p1*1000, p2*1000, p3*1.1];
    ig_bkg = [p1,     p2,     p3    ];

    % 로그 도메인 뒤쪽 꼬리 편향 보정: 큰 값(앞쪽)에 가중치 부여
    w_bkg = power(y_bkg / max(y_bkg),2);

    try
        FitBkg = fit(x_bkg, y_bkg_log, EqnBkg, ...
            'Start', ig_bkg, ...
            'Lower', lb_bkg, 'Upper', ub_bkg, ...
            'Robust', 'LAR', ...
            'Weights', w_bkg);
        bp = coeffvalues(FitBkg);
        p1f = bp(1);  p2f = bp(2);  p3f = bp(3);
    catch ME_bkg
        warning('Frame %d Step1 failed (%s). Using initial params.', ii, ME_bkg.message);
        p1f = p1;  p2f = p2;  p3f = p3;
    end

    % =========================================================
    %  Step 2 : 배경 파라미터 tight bounds → Gaussian 피팅
    % =========================================================
    m = BKG_MARGIN;

    % 음수 파라미터(b처럼 지수에 음수가 올 수 있음)를 고려한 bounds 계산
    bkg_vals  = [p1f, p2f, p3f];
    lb2_bkg   = zeros(1,3);
    ub2_bkg   = zeros(1,3);
    for bi = 1:3
        v = bkg_vals(bi);
        if v > 0
            lb2_bkg(bi) = v * (1 - m);
            ub2_bkg(bi) = v * (1 + m);
        elseif v < 0
            lb2_bkg(bi) = v * (1 + m);   % 더 음수 쪽
            ub2_bkg(bi) = v * (1 - m);   % 덜 음수 쪽
        else
            lb2_bkg(bi) = -0.01;
            ub2_bkg(bi) =  0.01;
        end
    end


    initialparam2 = [p1f, p2f, p3f, p4, p5, p6, p7, p8, p9];
    lb2 = [lb2_bkg, p4*0.001, p5 - 0.2, p6 - 0.2, p7*0.001, p8 - 0.05, p9 - 0.03 ];
    ub2 = [ub2_bkg, p4*1000, p5 + 0.2, p6 + 0.2, p7*100, p8 + 0.02, p9 + 0.1  ];

    Eqn = fittype(@(p1,p2,p3,p4,p5,p6,p7,p8,p9,x) ...
        log(GFt1exB(x,p1,p2,p3,p4,p5,p6,p7,p8,p9)), ...
        'independent', 'x', ...
        'coefficients', {'p1','p2','p3','p4','p5','p6','p7','p8','p9'});

    % 가우시안 피크 영역 가중치 (기존 그대로)
    weights = ones(size(x));
    gauss_region = (x > 0.42 & x < 0.62);
    weights(gauss_region) = 10;

    try
        IS = fit(x, y_log, Eqn, ...
            'Start', initialparam2, ...
            'Lower', lb2, 'Upper', ub2, ...
            'Robust', 'LAR', ...
            'Exclude', exclude_idx, ...
            'Weights', weights);

    catch ME_full
        % Step2 실패 시 배경 tight bounds 없이 폴백
        warning('Frame %d Step2 failed (%s). Falling back to single-step.', ii, ME_full.message);
        lb_fb = [lb_bkg, lb2(4:9)];
        ub_fb = [ub_bkg, ub2(4:9)];
        IS = fit(x, y_log, Eqn, ...
            'Start', [p1,p2,p3,p4,p5,p6,p7,p8,p9], ...
            'Lower', lb_fb, 'Upper', ub_fb, ...
            'Robust', 'LAR', ...
            'Exclude', exclude_idx, ...
            'Weights', weights);
    end

    ISp = coeffvalues(IS);
    parameter(ii,:) = ISp';

    % ---- 시각화 (기존 그대로) ----
    exb = expBKG(x, ISp(1), ISp(2), ISp(3));
    gb  = Gaussian(x, ISp(4), ISp(5), ISp(6), ISp(7), ISp(8), ISp(9));
    G   = exb + gb;

    figure(12);
    y_plot = y;
    y_plot(mask1) = NaN;
    plot(x, y_plot, '-k'); hold on
    y_lim_patch = [min(y(~exclude_idx))*0.5, max(y(~exclude_idx))*2];
    for pk_idx = 1:numel(peak_centers)
        half_range = peak_fwhms(pk_idx) * FWHM_MASK_FACTOR;
        x_lo = peak_centers(pk_idx) - half_range;
        x_hi = peak_centers(pk_idx) + half_range;
        patch([x_lo x_hi x_hi x_lo], ...
              [y_lim_patch(1) y_lim_patch(1) y_lim_patch(2) y_lim_patch(2)], ...
              [0.8 0.8 1.0], ...        % 연한 파란색
              'FaceAlpha', 0.25, ...
              'EdgeColor', 'none');
    end
    
    plot(x(~exclude_idx), y(~exclude_idx), 'ok', 'MarkerFaceColor', 'k');
    plot(x(exclude_idx),  y(exclude_idx),  'xr', 'MarkerSize', 8, 'LineWidth', 1.5);
    plot(x(bkg_fit_mask), y(bkg_fit_mask), 'b.', 'MarkerSize', 20);  % 배경 피팅에 실제 사용된 점
    exb_step1 = expBKG(x, p1f, p2f, p3f);
    plot(x, exb_step1, '--', 'Color', [1 0.5 0], 'LineWidth', 1.2);  % Step1 배경
    plot(x, exb);
    plot(x, gb);
    plot(x, G); hold off
    title(num2str(ii));
end


%% Value plot (4x2 배치: 왼쪽=Peak1, 오른쪽=Peak2)
% 단일 가우시안 면적 계산용 (원본의 sum(Gaussian(x,a,b,c)) 동작 보존)
singleGauss = @(x,a,b,c) a*exp(-((x-b).^2) ./ (sqrt(2)*(c/(2*sqrt(2*log(2))))).^2);

% --- Peak 1: parameter(:, 4:6),  Peak 2: parameter(:, 7:9) ---
Areaval1 = zeros(Na,1);
Areaval2 = zeros(Na,1);
for ii = 1:Na
    Areaval1(ii) = sum(singleGauss(x, parameter(ii,4), parameter(ii,5), parameter(ii,6)));
    Areaval2(ii) = sum(singleGauss(x, parameter(ii,7), parameter(ii,8), parameter(ii,9)));
end
times = (1:Na).*((exp_time*accum)/60);

Ival1 = parameter(:,4);   Ival2 = parameter(:,7);
qval1 = parameter(:,5);   qval2 = parameter(:,8);
FWHM1 = parameter(:,6);   FWHM2 = parameter(:,9);

% smoothing
Asmooth1    = smooth(times, Areaval1, 0.15, 'loess');
Asmooth2    = smooth(times, Areaval2, 0.15, 'loess');
Ismooth1    = smooth(times, Ival1,    0.15, 'loess');
Ismooth2    = smooth(times, Ival2,    0.15, 'loess');
qsmooth1    = smooth(times, qval1,    0.15, 'loess');
qsmooth2    = smooth(times, qval2,    0.15, 'loess');
FWHMsmooth1 = smooth(times, FWHM1,    0.15, 'loess');
FWHMsmooth2 = smooth(times, FWHM2,    0.15, 'loess');

figure('Name', 'Value Analysis');
t1 = tiledlayout(4, 2, 'TileSpacing', 'compact', 'Padding', 'compact');

% Row 1: Area (Peak1 | Peak2)
nexttile;
plot(times', Areaval1); hold on; plot(times', Asmooth1); hold off
axis tight; xlabel('time, min'); ylabel('A_{smooth}'); title('Area — Peak 1');

nexttile;
plot(times', Areaval2); hold on; plot(times', Asmooth2); hold off
axis tight; xlabel('time, min'); ylabel('A_{smooth}'); title('Area — Peak 2');

% Row 2: Peak Intensity
nexttile;
plot(times', Ival1); hold on; plot(times', Ismooth1); hold off
axis tight; xlabel('time, min'); ylabel('I_{smooth}'); title('Peak Intensity — Peak 1');

nexttile;
plot(times', Ival2); hold on; plot(times', Ismooth2); hold off
axis tight; xlabel('time, min'); ylabel('I_{smooth}'); title('Peak Intensity — Peak 2');

% Row 3: Q Position
nexttile;
plot(times', qval1); hold on; plot(times', qsmooth1); hold off
axis tight; xlabel('time, min'); ylabel('q_{smooth}, A^{-1}'); title('Q Position — Peak 1');

nexttile;
plot(times', qval2); hold on; plot(times', qsmooth2); hold off
axis tight; xlabel('time, min'); ylabel('q_{smooth}, A^{-1}'); title('Q Position — Peak 2');

% Row 4: FWHM
nexttile;
plot(times', FWHM1); hold on; plot(times', FWHMsmooth1); hold off
axis tight; xlabel('time, min'); ylabel('FWHM_{smooth}, A^{-1}'); title('FWHM — Peak 1');

nexttile;
plot(times', FWHM2); hold on; plot(times', FWHMsmooth2); hold off
axis tight; xlabel('time, min'); ylabel('FWHM_{smooth}, A^{-1}'); title('FWHM — Peak 2');

title(t1, 'Calculated Values (Raw vs Smooth)');

%% Percent calculation (4x2 배치: 왼쪽=Peak1, 오른쪽=Peak2)
% 퍼센트 변화
Aper1    = ((Areaval1./Areaval1(1)-1).*100);
Aper2    = ((Areaval2./Areaval2(1)-1).*100);
Iper1    = ((Ival1   ./Ival1(1)   -1).*100);
Iper2    = ((Ival2   ./Ival2(1)   -1).*100);
qper1    = ((qval1   ./qval1(1)   -1).*100);
qper2    = ((qval2   ./qval2(1)   -1).*100);
FWHMper1 = ((FWHM1   ./FWHM1(1)   -1).*100);
FWHMper2 = ((FWHM2   ./FWHM2(1)   -1).*100);

Apersmooth1    = smooth(times, Aper1,    0.15, 'loess');
Apersmooth2    = smooth(times, Aper2,    0.15, 'loess');
Ipersmooth1    = smooth(times, Iper1,    0.15, 'loess');
Ipersmooth2    = smooth(times, Iper2,    0.15, 'loess');
qpersmooth1    = smooth(times, qper1,    0.15, 'loess');
qpersmooth2    = smooth(times, qper2,    0.15, 'loess');
FWHMpersmooth1 = smooth(times, FWHMper1, 0.15, 'loess');
FWHMpersmooth2 = smooth(times, FWHMper2, 0.15, 'loess');

figure('Name', 'Percent Change Analysis');
t2 = tiledlayout(4, 2, 'TileSpacing', 'compact', 'Padding', 'compact');

% Row 1: Delta Area
nexttile;
plot(times', Aper1); hold on; plot(times', Apersmooth1); hold off
axis tight; xlabel('time, min'); ylabel('\DeltaArea, %'); title('\Delta Area — Peak 1');

nexttile;
plot(times', Aper2); hold on; plot(times', Apersmooth2); hold off
axis tight; xlabel('time, min'); ylabel('\DeltaArea, %'); title('\Delta Area — Peak 2');

% Row 2: Delta Intensity
nexttile;
plot(times', Iper1); hold on; plot(times', Ipersmooth1); hold off
axis tight; xlabel('time, min'); ylabel('\DeltaI, %'); title('\Delta Intensity — Peak 1');

nexttile;
plot(times', Iper2); hold on; plot(times', Ipersmooth2); hold off
axis tight; xlabel('time, min'); ylabel('\DeltaI, %'); title('\Delta Intensity — Peak 2');

% Row 3: Delta Q
nexttile;
plot(times', qper1); hold on; plot(times', qpersmooth1); hold off
axis tight; xlabel('time, min'); ylabel('\DeltaQ, %'); title('\Delta Q — Peak 1');

nexttile;
plot(times', qper2); hold on; plot(times', qpersmooth2); hold off
axis tight; xlabel('time, min'); ylabel('\DeltaQ, %'); title('\Delta Q — Peak 2');

% Row 4: Delta FWHM
nexttile;
plot(times', FWHMper1); hold on; plot(times', FWHMpersmooth1); hold off
axis tight; xlabel('time, min'); ylabel('\DeltaFWHM, %'); title('\Delta FWHM — Peak 1');

nexttile;
plot(times', FWHMper2); hold on; plot(times', FWHMpersmooth2); hold off
axis tight; xlabel('time, min'); ylabel('\DeltaFWHM, %'); title('\Delta FWHM — Peak 2');

title(t2, 'Percentage Change (%) Analysis');

%%
save parameter.mat parameter

% Save total fitted data as .xlsx file
tmpFN = strcat("fitted_", dataName);
fileName = strcat(tmpFN, ".xlsx");
xlswrite(fileName, times, "Sheet2", "A");

% --- Peak 1 (B ~ Q, 원본과 동일) ---
xlswrite(fileName, Areaval1,       "Sheet1", "B");
xlswrite(fileName, Asmooth1,       "Sheet1", "C");
xlswrite(fileName, Aper1,          "Sheet1", "D");
xlswrite(fileName, Apersmooth1,    "Sheet1", "E");

xlswrite(fileName, Ival1,          "Sheet1", "F");
xlswrite(fileName, Ismooth1,       "Sheet1", "G");
xlswrite(fileName, Iper1,          "Sheet1", "H");
xlswrite(fileName, Ipersmooth1,    "Sheet1", "I");

xlswrite(fileName, qval1,          "Sheet1", "J");
xlswrite(fileName, qsmooth1,       "Sheet1", "K");
xlswrite(fileName, qper1,          "Sheet1", "L");
xlswrite(fileName, qpersmooth1,    "Sheet1", "M");

xlswrite(fileName, FWHM1,          "Sheet1", "N");
xlswrite(fileName, FWHMsmooth1,    "Sheet1", "O");
xlswrite(fileName, FWHMper1,       "Sheet1", "P");
xlswrite(fileName, FWHMpersmooth1, "Sheet1", "Q");

% --- Peak 2 (R ~ AG, 동일한 순서로 이어서) ---
xlswrite(fileName, Areaval2,       "Sheet1", "R");
xlswrite(fileName, Asmooth2,       "Sheet1", "S");
xlswrite(fileName, Aper2,          "Sheet1", "T");
xlswrite(fileName, Apersmooth2,    "Sheet1", "U");

xlswrite(fileName, Ival2,          "Sheet1", "V");
xlswrite(fileName, Ismooth2,       "Sheet1", "W");
xlswrite(fileName, Iper2,          "Sheet1", "X");
xlswrite(fileName, Ipersmooth2,    "Sheet1", "Y");

xlswrite(fileName, qval2,          "Sheet1", "Z");
xlswrite(fileName, qsmooth2,       "Sheet1", "AA");
xlswrite(fileName, qper2,          "Sheet1", "AB");
xlswrite(fileName, qpersmooth2,    "Sheet1", "AC");

xlswrite(fileName, FWHM2,          "Sheet1", "AD");
xlswrite(fileName, FWHMsmooth2,    "Sheet1", "AE");
xlswrite(fileName, FWHMper2,       "Sheet1", "AF");
xlswrite(fileName, FWHMpersmooth2, "Sheet1", "AG");