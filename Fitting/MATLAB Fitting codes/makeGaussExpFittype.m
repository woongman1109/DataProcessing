function ft = makeGaussExpFittype(nPeak)
% makeGaussExpFittype  nPeak개의 Gaussian + expBKG(3param)을
%                      로그 도메인으로 피팅하는 fittype을 생성
%
%   ft = makeGaussExpFittype(nPeak)
%
%   계수 순서: [b1, b2, b3,  a1, m1, w1,  a2, m2, w2,  ...]
%     b1 : exp scale     (expBKG의 a)
%     b2 : slope         (expBKG의 b)
%     b3 : linear BG     (expBKG의 c)
%     ak : k번째 피크 amplitude
%     mk : k번째 피크 mean
%     wk : k번째 피크 FWHM
%
%   nPeak = 0 이면 배경(expBKG)만 있는 fittype을 만든다 (Step 1용).
%   nPeak >= 1 이면 배경 + Gaussian N개 (Step 2용).
%
%   ※ Gaussian 항의 정의는 Gaussian.m 과 동일 (FWHM 버전):
%       a*exp( -((x-m)^2) / (sqrt(2)*(w/(2*sqrt(2*log(2)))))^2 )

    % --- 계수 이름 조립: 배경 3개 + 피크당 3개 ---
    coeffs = {'b1','b2','b3'};
    for k = 1:nPeak
        coeffs{end+1} = sprintf('a%d', k); %#ok<AGROW>
        coeffs{end+1} = sprintf('m%d', k); %#ok<AGROW>
        coeffs{end+1} = sprintf('w%d', k); %#ok<AGROW>
    end

    % --- Gaussian 항 문자열 동적 생성 ---
    gaussTerms = cell(1, nPeak);
    for k = 1:nPeak
        ak = sprintf('a%d', k);
        mk = sprintf('m%d', k);
        wk = sprintf('w%d', k);
        gaussTerms{k} = sprintf( ...
            '%s.*exp(-(((x-%s).^2) ./ (sqrt(2)*(%s/(2*sqrt(2*log(2))))).^2))', ...
            ak, mk, wk);
    end

    % --- 전체 모델 문자열: 배경 + (피크 있으면) 피크합 ---
    bkgStr = 'b1.*(x.^(-b2))+b3';
    if nPeak > 0
        model = sprintf('log( %s + %s )', bkgStr, strjoin(gaussTerms, ' + '));
    else
        model = sprintf('log( %s )', bkgStr);   % Step 1: 배경만
    end

    % --- 익명함수 핸들로 변환 후 fittype 생성 ---
    argList = strjoin([coeffs, {'x'}], ',');
    fh = str2func( sprintf('@(%s) %s', argList, model) );

    ft = fittype(fh, 'independent', 'x', 'coefficients', coeffs);
end
