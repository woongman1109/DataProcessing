
% file load
clear
clc

dataName = "CF2_1_ai018_DOP2mV_DE2V_4cycle_90degree_ENDNORM_1dplotstack";
load CF2_1_ai018_DOP2mV_DE2V_4cycle_90degree_ENDNORM_1dplotstack.csv
q = CF2_1_ai018_DOP2mV_DE2V_4cycle_90degree_ENDNORM_1dplotstack(:,1);
I = CF2_1_ai018_DOP2mV_DE2V_4cycle_90degree_ENDNORM_1dplotstack(:,2:end);
clear CF2_1_ai018_DOP2mV_DE2V_4cycle_90degree_ENDNORM_1dplotstack

N = size(I,2);
%% accumulation
accum = 1;
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
qdel = find(q>0.17 & q<0.42);
qs = q(qdel);
Is = Ia(qdel,:);

figure;
plot(qs,Is);

%%
x = qs;
y = Is(:,1);

p1 = 9e-7; % exp Scale
p2 = 8e+0; % slope
p3 = 7e-1; % linear background

p4 = 1.2e+0; % Gaussian Amplitude
p5 = 0.26; % Mean
p6 = 0.077; % FWHM

exb = expDecay1(x,p1,p2,p3);
gb = Gaussian(x,p4,p5,p6);

G = exb + gb;

figure(11);
plot(x,y,'-ok'); hold on
plot(x,exb); hold on
plot(x,gb); hold on
plot(x,G); hold off

%%
parameter = zeros(Na,6);
initialparam = [p1, p2, p3 ,p4, p5,p6];
for ii = 1:Na
    y = Is(:,ii);

    lb = [ 5e-7,  5,   1e-1,    1e-1,  0.20,    0];
    ub = [inf,  10, 1e+0, inf, 0.35, 0.1];

    Eqn = fittype('GFt1exB(x,p1,p2,p3,p4,p5,p6)',...
    'independent',{'x'},...
    'coefficients',{'p1','p2','p3','p4','p5','p6'});
    
    IS = fit(x,y,Eqn,'Start',initialparam,'Lower',lb,'Upper',ub,'Robust','LAR');
    ISp = coeffvalues(IS);

    parameter(ii,:) = ISp;

    exb = expDecay1(x,ISp(1),ISp(2),ISp(3));
    gb = Gaussian(x,ISp(4),ISp(5),ISp(6));

    G = exb + gb;

    figure(11);
    plot(x,y,'-ok'); hold on
    plot(x,exb); hold on
    plot(x,gb); hold on
    plot(x,G); hold off
    title(num2str(ii));

end
%% area calculation
Areaval = zeros(Na,1);
for ii = 1:Na
    a = parameter(ii,4);
    b = parameter(ii,5);
    c = parameter(ii,6);
    Areaval(ii) = sum(Gaussian(x,a,b,c));
end

% area plot and smooth
times = (1:Na).*((10*accum)/60);
Asmooth = smooth(times,Areaval,0.15,'loess');
figure(12);
plot(times',Areaval); hold on
plot(times',Asmooth); hold off
axis tight
xlabel('time, min');
ylabel('A_{smooth}');

% area percent calcualtion
Aper = ((Areaval./Areaval(1)-1).*100);
Apersmooth = smooth(times,Aper,0.15,'loess');
figure(13);
plot(times',Aper); hold on
plot(times',Apersmooth); hold off
axis tight
xlabel('time, min');
ylabel('\DeltaArea, %');

%% peak Intensity & smooth
Ival = parameter(:,4);
Ismooth = smooth(times,Ival,0.15,'loess');
figure(14);
plot(times',Ival); hold on
plot(times',Ismooth); hold off
axis tight
xlabel('time, min');
ylabel('I_{smooth}');

% Peak intensity percent
Iper = ((Ival./Ival(1)-1).*100);
Ipersmooth = smooth(times,Iper,0.15,'loess');
figure(15);
plot(times',Iper); hold on
plot(times',Ipersmooth); hold off
axis tight
xlabel('time, min');
ylabel('\DeltaI, %');

%% Q position & smooth
qval = parameter(:,5);
qsmooth = smooth(times,qval,0.15,'loess');
figure(16);
plot(times',qval); hold on
plot(times',qsmooth); hold off
axis tight
xlabel('time, min');
ylabel('q_{smooth}, A^{-1}');

% Q position percent
Qper = ((qval./qval(1)-1).*100);
Qpersmooth = smooth(times,Qper,0.15,'loess');
figure(17);
plot(times',Qper); hold on
plot(times',Qpersmooth); hold off
axis tight
xlabel('time, min');
ylabel('\DeltaQ, %');

%% FWHM & smooth
FWHM = parameter(:,6);
FWHMsmooth = smooth(times,FWHM,0.15,'loess');
figure(18);
plot(times',FWHM); hold on
plot(times',FWHMsmooth); hold off
axis tight
xlabel('time, min');
ylabel('FWHM_{smooth}, A^{-1}');

% FWHM percent
FWHMper = ((FWHM./FWHM(1)-1).*100);
FWHMpersmooth = smooth(times,FWHMper,0.15,'loess');
figure(19);
plot(times',FWHMper); hold on
plot(times',FWHMpersmooth); hold off
axis tight
xlabel('time, min');
ylabel('\DeltaFWHM, %');

%%
save parameter.mat parameter

% Save total fitted data as .xlsx file
tmpFN = strcat("fitted_", dataName);
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
xlswrite(fileName, Qper,"Sheet1","L");
xlswrite(fileName, Qpersmooth,"Sheet1","M");

xlswrite(fileName, FWHM,"Sheet1","N");
xlswrite(fileName, FWHMsmooth,"Sheet1","O");
xlswrite(fileName, FWHMper,"Sheet1","P");
xlswrite(fileName, FWHMpersmooth,"Sheet1","Q");