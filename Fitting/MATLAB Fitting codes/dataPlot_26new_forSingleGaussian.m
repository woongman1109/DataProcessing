
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
    
    lb = [ p1*0.1, p2*0.1, p3*0.1, p4*0.001, p5 - 0.1, p6 - 0.06, p7*0.001, p8 - 0.1, p9 - 0.1 ];
    ub = [ p1*100, p2*100, p3*1.1, p4*100, p5 + 0.1, p6 + 0.2, p7*1, p8 + 0.1, p9 + 0.1  ];
    
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

%% Value plot (한 창에 2x2 배치)
figure('Name', 'Value Analysis');
t1 = tiledlayout(2, 2, 'TileSpacing', 'compact', 'Padding', 'compact');

% 1. area calculation & plot
Areaval = zeros(Na,1);
for ii = 1:Na
    a = parameter(ii,4);
    b = parameter(ii,5);
    c = parameter(ii,6);
    Areaval(ii) = sum(Gaussian(x,a,b,c));
end
times = (1:Na).*((exp_time*accum)/60);

nexttile;
Asmooth = smooth(times,Areaval,0.15,'loess');
plot(times',Areaval); hold on
plot(times',Asmooth); hold off
axis tight; xlabel('time, min'); ylabel('A_{smooth}'); title('Area');

% 2. peak Intensity
nexttile;
Ival = parameter(:,4);
Ismooth = smooth(times,Ival,0.15,'loess');
plot(times',Ival); hold on
plot(times',Ismooth); hold off
axis tight; xlabel('time, min'); ylabel('I_{smooth}'); title('Peak Intensity');

% 3. Q position
nexttile;
qval = parameter(:,5);
qsmooth = smooth(times,qval,0.15,'loess');
plot(times',qval); hold on
plot(times',qsmooth); hold off
axis tight; xlabel('time, min'); ylabel('q_{smooth}, A^{-1}'); title('Q Position');

% 4. FWHM
nexttile;
FWHM = parameter(:,6);
FWHMsmooth = smooth(times,FWHM,0.15,'loess');
plot(times',FWHM); hold on
plot(times',FWHMsmooth); hold off
axis tight; xlabel('time, min'); ylabel('FWHM_{smooth}, A^{-1}'); title('FWHM');

title(t1, 'Calculated Values (Raw vs Smooth)'); % 전체 제목

%% Percent calculation (한 창에 2x2 배치)
figure('Name', 'Percent Change Analysis');
t2 = tiledlayout(2, 2, 'TileSpacing', 'compact', 'Padding', 'compact');

% 1. Area %
nexttile;
Aper = ((Areaval./Areaval(1)-1).*100);
Apersmooth = smooth(times,Aper,0.15,'loess');
plot(times',Aper); hold on
plot(times',Apersmooth); hold off
axis tight; xlabel('time, min'); ylabel('\DeltaArea, %'); title('\Delta Area');

% 2. Peak intensity %
nexttile;
Iper = ((Ival./Ival(1)-1).*100);
Ipersmooth = smooth(times,Iper,0.15,'loess');
plot(times',Iper); hold on
plot(times',Ipersmooth); hold off
axis tight; xlabel('time, min'); ylabel('\DeltaI, %'); title('\Delta Intensity');

% 3. q position %
nexttile;
qper = ((qval./qval(1)-1).*100);
qpersmooth = smooth(times,qper,0.15,'loess');
plot(times',qper); hold on
plot(times',qpersmooth); hold off
axis tight; xlabel('time, min'); ylabel('\DeltaQ, %'); title('\Delta Q');

% 4. FWHM %
nexttile;
FWHMper = ((FWHM./FWHM(1)-1).*100);
FWHMpersmooth = smooth(times,FWHMper,0.15,'loess');
plot(times',FWHMper); hold on
plot(times',FWHMpersmooth); hold off
axis tight; xlabel('time, min'); ylabel('\DeltaFWHM, %'); title('\Delta FWHM');

title(t2, 'Percentage Change (%) Analysis'); % 전체 제목
%%
save parameter.mat parameter

% Save total fitted data as .xlsx file
tmpFN = strcat("fitted_", dataName)
fileName = strcat(tmpFN, ".xlsx");
xlswrite(fileName, times,"Sheet2","A");

xlswrite(fileName, Areaval,"Sheet1","B");
xlswrite(fileName, Asmooth,"Sheet1","C");
xlswrite(fileName, Aper,"Sheet1","D");
xlswrite(fileName, Apersmooth,"Sheet1","E");

xlswrite(fileName, Ival,"Sheet1","F");
xlswrite(fileName, Ismooth,"Sheet1","G");
xlswrite(fileName, Iper,"Sheet1","H");
xlswrite(fileName, Ipersmooth,"Sheet1","I");

xlswrite(fileName, qval,"Sheet1","J");
xlswrite(fileName, qsmooth,"Sheet1","K");
xlswrite(fileName, qper,"Sheet1","L");
xlswrite(fileName, qpersmooth,"Sheet1","M");

xlswrite(fileName, FWHM,"Sheet1","N");
xlswrite(fileName, FWHMsmooth,"Sheet1","O");
xlswrite(fileName, FWHMper,"Sheet1","P");
xlswrite(fileName, FWHMpersmooth,"Sheet1","Q");