function y = PV_varargin(x, varargin)
% PV_varargin  가변 개수의 Pseudo-Voigt 피크 합을 계산
%
%   y = PV_varargin(x, pG1, pG2, ...)          % 피크별 배열 나열
%   y = PV_varargin(x, [pG1, pG2, ...])        % 이미 합친 벡터 하나
%   y = PV_varargin(x, a1,m1,w1,e1, a2,...)    % 스칼라 나열 방식
%
%   각 피크는 [amplitude, mean, FWHM, eta] 4원소로 구성.
%   입력 형태(배열 여러 개 / 합친 벡터 / 스칼라 나열)에 상관없이
%   내부에서 하나의 벡터로 평탄화한 뒤 4개씩 끊어 처리한다.
%
%   Pseudo-Voigt 정의 (파이썬 FitFn_GaussExp.py 와 동일):
%       PV = eta*L + (1-eta)*G
%       G  = a*exp( -((x-m)^2) / (sqrt(2)*(w/(2*sqrt(2*log(2)))))^2 )   (FWHM 버전)
%       L  = a / ( 1 + ((x-m)/(w/2))^2 )
%     eta = 0 → 순수 Gaussian,  eta = 1 → 순수 Lorentzian

    % 들어온 인자들을 하나의 행벡터로 평탄화
    p = [varargin{:}];
    p = p(:).';

    if isempty(p)
        y = zeros(size(x));
        return;
    end

    if mod(numel(p), 4) ~= 0
        error('PV_varargin:badInput', ...
            '파라미터 개수가 4의 배수가 아닙니다 (현재 %d개). 각 피크는 [amp, mean, FWHM, eta] 4개여야 합니다.', ...
            numel(p));
    end

    nPeak = numel(p) / 4;

    y = zeros(size(x));
    for k = 1:nPeak
        a   = p(4*k-3);   % amplitude
        m   = p(4*k-2);   % mean
        w   = p(4*k-1);   % FWHM
        eta = p(4*k  );   % 혼합비

        % Gaussian 성분 (FWHM 버전)
        g = a.*exp(-(((x-m).^2) ./ (sqrt(2)*(w/(2*sqrt(2*log(2))))).^2));
        % Lorentzian 성분 (HWHM = w/2)
        L = a ./ (1 + ((x-m)./(w/2)).^2);
        % 선형 혼합
        y = y + eta.*L + (1-eta).*g;
    end
end
