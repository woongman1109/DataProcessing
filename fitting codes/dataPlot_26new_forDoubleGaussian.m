
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
figure;
plot(q,Ia);
%% q del
qdel = find(q>0.35 & q<0.92);
qs = q(qdel);
Is = Ia(qdel,:);

figure;
plot(qs,Is);

%%
x = qs;
y = Is(:,50);

p1 = 1.3e1; % exp Scale
p2 = 3.8; % slope
p3 = 140; % linear background

p4 = 2E2; % Gaussian Amplitude
p5 = 0.52; % Mean
p6 = 0.15; % FWHM

p7 = 0.5E2; % Gaussian Amplitude
p8 = 0.75; % Mean
p9 = 0.15; % FWHM

exb = expBKG(x,p1,p2,p3);
gb = Gaussian(x,p4,p5,p6,p7,p8,p9);

G = exb + gb;

figure(11);
plot(x,y,'-ok'); hold on
plot(x,exb); hold on
plot(x,gb); hold on
plot(x,G); hold off

%%
% 좌우 n개 점 설정 (n=2일 경우 기준점 포함 총 5개 윈도우)
n = 10; 
window_size = 2*n + 1; 

for ii = 1:Na
    y = Is(:,ii);
    y_log = log(y);
    
    % --- 마스킹(Masking) 조건 설정 (알고리즘 전면 수정) ---
    % 1. 데이터가 0인 점 
    mask1 = (y == 0);
    
    % 2. 0인 점들을 임시로 NaN 처리
    y_temp = y;
    y_temp(mask1) = NaN;
    
    % [핵심] 0으로 뻥 뚫린 구간을 양옆 정상 데이터 기준으로 직선을 그어 메꿈 (가상의 다리)
    % 이렇게 하면 중간에 툭 튀는 점도 가상 기준선(약 400 근처)과 비교당하게 됩니다.
    y_bridge = fillmissing(y_temp, 'linear'); 
    
    % 3. 메꿔진 가상의 궤도를 바탕으로 이동 중간값 계산 (omitnan 필요 없음)
    local_ref = movmedian(y_bridge, window_size); 
    
    % 4. 실제 데이터(y)가 정상 궤도(local_ref) 대비 90% 이하면 제외
    mask2 = (y <= 0.9 * local_ref);
    
    % 최종적으로 피팅에서 제외할 인덱스
    exclude_idx = mask1 | mask2 | (y <= 0) | ~isfinite(y_log);
    % --------------------------------
    
    lb = [ p1*0.1, p2*0.1, p3*0.1, p4*0.001, p5 - 0.2, p6 - 0.06, p7*0.001, p8 - 0.2, p9 - 0.1 ];
    ub = [ p1*100, p2*100, p3*1.1, p4*100, p5 + 0.2, p6 + 0.2, p7*1, p8 + 0.2, p9 + 0.1  ];
    
    Eqn = fittype(@(p1,p2,p3,p4,p5,p6,p7,p8,p9,x) ...
    log(GFt1exB(x,p1,p2,p3,p4,p5,p6,p7,p8,p9)), ...
    'independent', 'x', ...
    'coefficients', {'p1','p2','p3','p4','p5','p6','p7','p8','p9'});
    
    % Gaussian peak 후보 영역에 추가 가중치
    weights = ones(size(x));
    gauss_region = (x > 0.42 & x < 0.62);   % p5 ± 적당히
    weights(gauss_region) = 10;             % 5~20 사이에서 튜닝

    % fit 함수 마지막에 'Exclude' 옵션 추가
    IS = fit(x, y_log, Eqn, ...
        'Start', initialparam, ...
        'Lower', lb, 'Upper', ub, ...
        'Robust', 'LAR', ...
        'Exclude', exclude_idx, ...
        'Weights', weights);
    
    % 카운팅 통계상 σ ~ sqrt(I), weight = 1/σ² = 1/I
    weights = 1 ./ max(y, 1);
    weights(exclude_idx) = 0;   % Exclude랑 중복돼도 안전

    ISp = coeffvalues(IS);
    parameter(ii,:) = ISp';
    
    exb = expBKG(x,ISp(1),ISp(2),ISp(3));
    gb = Gaussian(x,ISp(4),ISp(5),ISp(6),ISp(7),ISp(8),ISp(9));
    G = exb + gb;
        
    figure(12);
    % 1. 전체 데이터를 선(Line)으로만 연결
    y_plot = y; 
    y_plot(mask1) = NaN;
    plot(x, y_plot, '-k'); hold on
    
    % 2. 피팅에 포함된 정상 데이터 (검은색 O 기호)
    plot(x(~exclude_idx), y(~exclude_idx), 'ok', 'MarkerFaceColor', 'k'); 
    
    % 3. 마스킹되어 피팅에서 제외된 데이터 (빨간색 X 기호)
    plot(x(exclude_idx), y(exclude_idx), 'xr', 'MarkerSize', 8, 'LineWidth', 1.5);
    
    % 4. 피팅된 곡선들 그리기
    plot(x,exb);
    plot(x,gb);
    plot(x,G); hold off
    
    title(num2str(ii));
    %legend('Data Line', 'Included Data', 'Masked (Excluded)', 'Background', 'Gaussian', 'Total Fit', 'Location', 'best');
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