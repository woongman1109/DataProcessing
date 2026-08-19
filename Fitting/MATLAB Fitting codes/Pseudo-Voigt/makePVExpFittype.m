function ft = makePVExpFittype(nPeak)
% makePVExpFittype  nPeak개의 Pseudo-Voigt + expBKG(3param)을
%                   로그 도메인으로 피팅하는 fittype을 생성
%
%   ft = makePVExpFittype(nPeak)
%
%   계수 순서: [b1, b2, b3,  a1, m1, w1, e1,  a2, m2, w2, e2,  ...]
%     b1 : exp scale     (expBKG의 a)
%     b2 : slope         (expBKG의 b)
%     b3 : linear BG     (expBKG의 c)
%     ak : k번째 피크 amplitude
%     mk : k번째 피크 mean
%     wk : k번째 피크 FWHM
%     ek : k번째 피크 eta (혼합비, 0=순수 Gaussian, 1=순수 Lorentzian)
%
%   nPeak = 0 이면 배경(expBKG)만 있는 fittype을 만든다 (Step 1용).
%   nPeak >= 1 이면 배경 + Pseudo-Voigt N개 (Step 2용).
%
%   ※ Pseudo-Voigt 정의 (파이썬 FitFn_GaussExp.py 와 동일):
%       PV = eta*L + (1-eta)*G
%       G  = a*exp( -((x-m)^2) / (sqrt(2)*(w/(2*sqrt(2*log(2)))))^2 )   (FWHM 버전)
%       L  = a / ( 1 + ((x-m)/(w/2))^2 )
%     G와 L은 같은 a, m, w를 공유하며 eta로 선형 혼합.

    % --- 계수 이름 조립: 배경 3개 + 피크당 4개 ---
    coeffs = {'b1','b2','b3'};
    for k = 1:nPeak
        coeffs{end+1} = sprintf('a%d', k); %#ok<AGROW>
        coeffs{end+1} = sprintf('m%d', k); %#ok<AGROW>
        coeffs{end+1} = sprintf('w%d', k); %#ok<AGROW>
        coeffs{end+1} = sprintf('e%d', k); %#ok<AGROW>
    end

    % --- Pseudo-Voigt 항 문자열 동적 생성 ---
    pvTerms = cell(1, nPeak);
    for k = 1:nPeak
        ak = sprintf('a%d', k);
        mk = sprintf('m%d', k);
        wk = sprintf('w%d', k);
        ek = sprintf('e%d', k);
        % Gaussian 성분 (FWHM 버전, Gaussian.m과 동일한 분모 형태)
        gStr = sprintf('%s.*exp(-(((x-%s).^2) ./ (sqrt(2)*(%s/(2*sqrt(2*log(2))))).^2))', ...
            ak, mk, wk);
        % Lorentzian 성분 (HWHM = w/2)
        lStr = sprintf('%s ./ (1 + ((x-%s)./(%s/2)).^2)', ak, mk, wk);
        % PV = e*L + (1-e)*G
        pvTerms{k} = sprintf('( %s.*(%s) + (1-%s).*(%s) )', ek, lStr, ek, gStr);
    end

    % --- 전체 모델 문자열: 배경 + (피크 있으면) 피크합 ---
    bkgStr = 'b1.*(x.^(-b2))+b3';
    if nPeak > 0
        model = sprintf('log( %s + %s )', bkgStr, strjoin(pvTerms, ' + '));
    else
        model = sprintf('log( %s )', bkgStr);   % Step 1: 배경만
    end

    % --- 익명함수 핸들로 변환 후 fittype 생성 ---
    argList = strjoin([coeffs, {'x'}], ',');
    fh = str2func( sprintf('@(%s) %s', argList, model) );

    ft = fittype(fh, 'independent', 'x', 'coefficients', coeffs);
end
