function y = Gaussian_varargin(x, varargin)
% Gaussian_varargin  가변 개수의 Gaussian 피크 합을 계산
%
%   y = Gaussian_varargin(x, pG1, pG2, ...)      % 피크별 배열 나열
%   y = Gaussian_varargin(x, [pG1, pG2, ...])    % 이미 합친 벡터 하나
%   y = Gaussian_varargin(x, a1,b1,c1, a2,b2,c2) % 기존 스칼라 나열 방식
%
%   각 피크는 [amplitude, mean, FWHM] 3원소로 구성.
%   입력 형태(배열 여러 개 / 합친 벡터 / 스칼라 나열)에 상관없이
%   내부에서 하나의 벡터로 평탄화한 뒤 3개씩 끊어 처리한다.
%
%   피크 정의는 기존 Gaussian.m 과 동일 (FWHM 버전):
%       a*exp( -((x-b)^2) / (sqrt(2)*(c/(2*sqrt(2*log(2)))))^2 )

    % 들어온 인자들을 하나의 행벡터로 평탄화
    p = [varargin{:}];
    p = p(:).';

    if isempty(p)
        y = zeros(size(x));
        return;
    end

    if mod(numel(p), 3) ~= 0
        error('Gaussian_varargin:badInput', ...
            '파라미터 개수가 3의 배수가 아닙니다 (현재 %d개). 각 피크는 [amp, mean, FWHM] 3개여야 합니다.', ...
            numel(p));
    end

    nPeak = numel(p) / 3;

    y = zeros(size(x));
    for k = 1:nPeak
        a = p(3*k-2);   % amplitude
        b = p(3*k-1);   % mean
        c = p(3*k  );   % FWHM
        y = y + a.*exp(-(((x-b).^2) ./ (sqrt(2)*(c/(2*sqrt(2*log(2))))).^2));
    end
end
