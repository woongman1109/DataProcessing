function y = Gaussian(x,a1,b1,c1,a2,b2,c2)
% x : x axis
% a: amplitude
% b: mean
% c : FWHM

y = a1*exp(-(((x-b1).^2) ./ (sqrt(2)*(c1/(2*sqrt(2*log(2))))).^2)) + ...
    a2*exp(-(((x-b2).^2) ./ (sqrt(2)*(c2/(2*sqrt(2*log(2))))).^2)); % FWHM version

% y = a*exp(-(((x-b).^2) ./ (sqrt(2)*c).^2)); % simga version
end