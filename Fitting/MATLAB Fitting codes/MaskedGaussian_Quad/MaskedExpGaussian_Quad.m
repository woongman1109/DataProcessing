% ---- 경로 설정 ----
addpath('..');
addpath('C:\Users\...\Fitting\MATLAB Fitting codes');
% -------------------

%%
% file load
clear
clc

dataName = "PEDOT_300mN_1_1Dplotstack";

fileName = sprintf('%s.csv', dataName);
data = readmatrix(fileName);
q = data(:,1);
I = data(:,2:end);
clear data;
N = size(I,2);
%% accumulation
accum = 10;
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
figure(1);
plot(q,Ia(:,Na));
%% q del
qdel = find(q>0.35 & q<2.5);
qs = q(qdel);
Is = Ia(qdel,:);

figure(1);
plot(qs,Is(:,Na));

%%
targ = 20;
x = qs;
y = Is(:,targ);

% parameter 파일 불러오기
param_PV;
strip_eta;

% 파라미터 배경 전용 fittype
EqnBkg = makeGaussExpFittype(0);          % 배경만
Eqn    = makeGaussExpFittype(nPeak + 1);  % 진짜 피크 + pGB 1개

% 가우시안 피크 영역 가중치 (모든 피크 주변 부스트)
weights = ones(size(x));
gauss_region = false(size(x));
for k = 1:nPeak
    gauss_region = gauss_region | ...
        (x > pG_mat(k,2) - weight_region_ratio*pG_mat(k,3) & x < pG_mat(k,2) + weight_region_ratio*pG_mat(k,3));
end
weights(gauss_region) = 10;

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
exb = expBKG(x,pB(1),pB(2),pB(3));
gb  = Gaussian_varargin(x, pG_arr);
gb_pGB = Gaussian_varargin(x, pGB);
G = exb + gb + gb_pGB;

figure(1);
plot(x,y,'-ok'); hold on
plot(x,exb); hold on
plot(x,gb); hold on
plot(x,G); hold off

%%
% ------ y축 범위 고정 ----- %
y_max_all = max(Is(Is > 0), [], 'omitnan');

% 파라미터 파일 재확인 (수동 피팅용)
param_PV;
strip_eta;

frame_start = 1;
for ii = frame_start:40:Na
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
    
    % %{
    peak_centers = pG_mat(:,2).';
    peak_fwhms   = pG_mat(:,3).';
    %}

    %{
    if ii == frame_start
        peak_centers = pG_mat(:,2).';                    % 모든 피크의 초기 중심
        peak_fwhms   = pG_mat(:,3).';                    % 모든 피크의 초기 FWHM
    else
        % parameter 열: [b1 b2 b3, a1 m1 w1 e1, a2 m2 w2 e2, ...]
        % k번째 피크 mean = 4k+1, FWHM = 4k+2
        peak_centers = parameter(ii-1, 4*(1:nPeak)+1);   % 이전 프레임 중심들 (5,9,13,17열)
        peak_fwhms   = parameter(ii-1, 4*(1:nPeak)+2);   % 이전 프레임 FWHM들 (6,10,14,18열)
    end
    %}

    peak_mask = false(size(x));
    for pk_idx = 1:numel(peak_centers)
        half_range = peak_fwhms(pk_idx) * NOISE_MASK_FACTOR;
        peak_mask  = peak_mask | ...
            (x >= peak_centers(pk_idx) - half_range & ...
             x <= peak_centers(pk_idx) + half_range);
    end

    bkg_fit_mask = ~peak_mask & ~exclude_idx;

    % ── ForcedUnmask: 데이터 양끝 일정 비율은 강제로 배경 피팅에 포함 ──
    % (단, exclude_idx로 걸린 진짜 불량점은 여전히 제외)
    forced_idx = (x <= ForcedUnmask_head) | (x >= ForcedUnmask_tail);
    bkg_fit_mask = (bkg_fit_mask | forced_idx) & ~exclude_idx;
    % ───────────────────────────────────────────────

    if sum(bkg_fit_mask) < 5          % 배경 포인트 부족하면 exclude만 적용
        bkg_fit_mask = ~exclude_idx;
    end

    x_bkg     = x(bkg_fit_mask);
    y_bkg     = y(bkg_fit_mask);
    y_bkg_log = log(y_bkg);



    % 로그 도메인 뒤쪽 꼬리 편향 보정: 큰 값(앞쪽)에 가중치 부여
    w_bkg = power(y_bkg / max(y_bkg),2);

    try
        FitBkg = fit(x_bkg, y_bkg_log, EqnBkg, ...
            'Start', pB, ...
            'Lower', lb_bkg, 'Upper', ub_bkg, ...
            'Robust', 'LAR', ...
            'Weights', w_bkg);
        pBf = coeffvalues(FitBkg);
    catch ME_bkg
        warning('Frame %d StepB(1) failed (%s). Using initial params.', ii, ME_bkg.message);
        pBf = pB; 
    end

    % =========================================================
    %  Step 2 : 배경 파라미터 tight bounds → Gaussian 피팅
    % =========================================================
    m = BKG_MARGIN;

    % 음수 파라미터(b처럼 지수에 음수가 올 수 있음)를 고려한 bounds 계산
    bkg_vals  = pBf;
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

    % Step1 이후 생성된 pBf 및 bound 업데이트
    initialparam2 = [pBf, pG_arr, pGB];
    lb2 = [lb2_bkg, lbG_arr, lbGB];
    ub2 = [ub2_bkg, ubG_arr, ubGB];

    try
        IS = fit(x, y_log, Eqn, ...
            'Start', initialparam2, ...
            'Lower', lb2, 'Upper', ub2, ...
            'Robust', 'LAR', ...
            'Exclude', exclude_idx, ...
            'Weights', weights);

    catch ME_full
         % StepB(2) 실패 시 배경 tight bounds 없이 폴백
        warning('Frame %d StepB(2) failed (%s). Falling back to single-step.', ii, ME_full.message);
        lb_fb = [lb_bkg, lbG_arr, lbGB];
        ub_fb = [ub_bkg, ubG_arr, ubGB];
        IS = fit(x, y_log, Eqn, ...
            'Start', [pB, pG_arr, pGB], ...
            'Lower', lb_fb, 'Upper', ub_fb, ...
            'Robust', 'LAR', ...
            'Exclude', exclude_idx, ...
            'Weights', weights);
    end

    ISp = coeffvalues(IS);
    parameter(ii,:) = ISp';

    % ---- 시각화 ----
    exb    = expBKG(x, ISp(1), ISp(2), ISp(3));
    gb_pG  = Gaussian_varargin(x, ISp(4 : 3+3*nPeak));   % 진짜 피크만 (pGB 제외)
    gb_pGB = Gaussian_varargin(x, ISp(end-2:end));       % pGB 단독
    gb     = gb_pG + gb_pGB;                             % 전체 Gaussian 합
    G      = exb + gb;                                   % 최종 (배경+전체)

    figure(2);
    y_plot = y;
    y_plot(mask1) = NaN;
    plot(x, y_plot, '-k'); hold on
    y_lim_patch = [0, y_max_all*1.1];
    for pk_idx = 1:numel(peak_centers)
        half_range = peak_fwhms(pk_idx) * NOISE_MASK_FACTOR;
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
    exb_step1 = expBKG(x, pBf(1), pBf(2), pBf(3));
    plot(x, exb_step1, '--', 'Color', [1 0.5 0], 'LineWidth', 1.2);  % Step1 배경
    plot(x, exb);
    plot(x, gb_pG,  'Color', [0 0.6 0], 'LineWidth', 1.5);          % pG만 합성 (초록)
    plot(x, gb_pGB, ':', 'Color', [0.5 0 0.5], 'LineWidth', 1.2);   % pGB 단독 (보라 점선)
    plot(x, gb, '--', 'Color', [0 0.2 0.7], 'LineWidth', 1.5);      % gb 단독
    plot(x, G, 'LineWidth', 1.5); hold off
    ylim([0, y_max_all*1.02]);
    title(num2str(ii));

    % ── pB 피팅 결과 + 경계를 표로 표시 (오른쪽 위 모서리 정렬) ──
    delete(findall(gcf, 'Tag', 'pBtable'));
    ax = gca;
    pB_labels = {'expScale', 'slope', 'linearBG'};
    txt = sprintf('%-9s %9s %9s %9s\n', 'Param', 'lb', 'value', 'ub');
    txt = [txt sprintf('%s\n', repmat('-', 1, 39))];
    for pp = 1:3
        val = ISp(pp);  lo = lb_bkg(pp);  hi = ub_bkg(pp);
        span = hi - lo;  flag = '';
        if abs(val-lo) <= 0.01*span || abs(val-hi) <= 0.01*span
            flag = ' *';
        end
        txt = [txt sprintf('%-9s %9.4g %9.4g %9.4g%s\n', pB_labels{pp}, lo, val, hi, flag)];
    end
    text(ax, 0.98, 0.98, txt, ...
        'Units', 'normalized', ...              % 축 기준 0~1 좌표
        'HorizontalAlignment', 'right', ...     % 오른쪽 모서리 기준
        'VerticalAlignment', 'top', ...         % 위 모서리 기준
        'FontName', 'Courier New', ...
        'FontSize', 11, ...                     % 이제 키워도 안 넘침
        'BackgroundColor', 'w', ...
        'EdgeColor', 'k', ...
        'Margin', 4, ...
        'Tag', 'pBtable');

    % ── 피크 파라미터(pG + pGB) 표 표시 (왼쪽 위 모서리 정렬) ──
    delete(findall(gcf, 'Tag', 'pGtable'));
    % ISp 배치: [b1 b2 b3, a1 m1 w1, a2 m2 w2, ...]
    %   마지막 피크(nPeak+1번째)가 pGB
    nTotalPk = nPeak + 1;
    txtP = sprintf('%-5s %8s %7s %7s\n', 'Peak', 'Amp', 'q', 'FWHM');
    txtP = [txtP sprintf('%s\n', repmat('-', 1, 37))];
    for pk = 1:nTotalPk
        base = 3 + 3*(pk-1);          % 이 피크의 첫 파라미터 위치
        A   = ISp(base+1);
        mu  = ISp(base+2);
        fw  = ISp(base+3);
        if pk <= nPeak
            name = sprintf('pG%d', pk);
        else
            name = 'pGB';             % 마지막은 배경 보조
        end
        txtP = [txtP sprintf('%-5s %8.3g %7.4f %7.4f\n', name, A, mu, fw)];
    end
    text(gca, 0.02, 0.98, txtP, ...
        'Units', 'normalized', ...
        'HorizontalAlignment', 'left', ...      % 왼쪽 모서리 기준
        'VerticalAlignment', 'top', ...         % 위 모서리 기준
        'FontName', 'Courier New', ...
        'FontSize', 10, ...
        'BackgroundColor', 'w', ...
        'EdgeColor', 'k', ...
        'Margin', 4, ...
        'Tag', 'pGtable');
end


%% Value plot (4x nPeak 배치: 행=지표, 열=피크)
% parameter 열: [b1 b2 b3, a1 m1 w1, a2 m2 w2, ...]  (Gaussian, 피크당 3param)
%   k번째 피크: amp=3k+1, mean=3k+2, FWHM=3k+3
times = (1:Na).*((exp_time*accum)/60);
times = times(:);
 
% --- 각 피크별 지표를 행렬로 추출 (열 = 피크) ---
Areaval = zeros(Na, nPeak);
Ival    = zeros(Na, nPeak);
qval    = zeros(Na, nPeak);
FWHMval = zeros(Na, nPeak);
for k = 1:nPeak
    base = 3*k + 1;                     % k번째 피크 amp 위치
    for ii = 1:Na
        Areaval(ii,k) = sum(Gaussian_varargin(x, parameter(ii, base:base+2)));
    end
    Ival(:,k)    = parameter(:, base);      % amplitude
    qval(:,k)    = parameter(:, base+1);    % mean
    FWHMval(:,k) = parameter(:, base+2);    % FWHM
end
 
% --- smoothing (지표별로 피크 전체를 한 번에) ---
Asmooth    = zeros(Na, nPeak);
Ismooth    = zeros(Na, nPeak);
qsmooth    = zeros(Na, nPeak);
FWHMsmooth = zeros(Na, nPeak);
for k = 1:nPeak
    Asmooth(:,k)    = smooth(times, Areaval(:,k), 0.15, 'loess');
    Ismooth(:,k)    = smooth(times, Ival(:,k),    0.15, 'loess');
    qsmooth(:,k)    = smooth(times, qval(:,k),    0.15, 'loess');
    FWHMsmooth(:,k) = smooth(times, FWHMval(:,k), 0.15, 'loess');
end
 
figure('Name', 'Value Analysis');
t1 = tiledlayout(4, nPeak, 'TileSpacing', 'compact', 'Padding', 'compact');
 
% Row 1: Area
for k = 1:nPeak
    nexttile;
    plot(times, Areaval(:,k)); hold on; plot(times, Asmooth(:,k)); hold off
    axis tight; xlabel('time, min'); ylabel('Area'); title(sprintf('Area — Peak %d', k));
end
% Row 2: Peak Intensity
for k = 1:nPeak
    nexttile;
    plot(times, Ival(:,k)); hold on; plot(times, Ismooth(:,k)); hold off
    axis tight; xlabel('time, min'); ylabel('I'); title(sprintf('Peak Intensity — Peak %d', k));
end
% Row 3: Q Position
for k = 1:nPeak
    nexttile;
    plot(times, qval(:,k)); hold on; plot(times, qsmooth(:,k)); hold off
    axis tight; xlabel('time, min'); ylabel('q, A^{-1}'); title(sprintf('Q Position — Peak %d', k));
end
% Row 4: FWHM
for k = 1:nPeak
    nexttile;
    plot(times, FWHMval(:,k)); hold on; plot(times, FWHMsmooth(:,k)); hold off
    axis tight; xlabel('time, min'); ylabel('FWHM, A^{-1}'); title(sprintf('FWHM — Peak %d', k));
end
 
title(t1, 'Calculated Values (Raw vs Smooth)');
 
%%
save parameter.mat parameter
 
% Save total fitted data as .xlsx file
tmpFN = strcat("fitted_", dataName);
fileName = strcat(tmpFN, ".xlsx");
 
% 시간축 (Sheet2)
xlswrite(fileName, times, "Sheet2", "A");
 
% --- 출력 행렬 조립: 피크별 [Area Asm I Ism q qsm FWHM FWHMsm] 8열, 피크 순서로 ---
outMat = [];
header  = {};
for k = 1:nPeak
    outMat = [outMat, ...
        Areaval(:,k),    Asmooth(:,k), ...
        Ival(:,k),       Ismooth(:,k), ...
        qval(:,k),       qsmooth(:,k), ...
        FWHMval(:,k),    FWHMsmooth(:,k)];
    header = [header, ...
        {sprintf('Area_P%d',k),  sprintf('Area_sm_P%d',k), ...
         sprintf('I_P%d',k),     sprintf('I_sm_P%d',k), ...
         sprintf('q_P%d',k),     sprintf('q_sm_P%d',k), ...
         sprintf('FWHM_P%d',k),  sprintf('FWHM_sm_P%d',k)}];
end
 
% 헤더(1행) + 데이터(2행부터) 한 번에 기록
xlswrite(fileName, header, "Sheet1", "A1");
xlswrite(fileName, outMat, "Sheet1", "A2");