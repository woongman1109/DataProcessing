function y = Gaussian(x,a,b,c)
% x : x axis
% a: amplitude
% b: mean
% c : FWHM

y = a*exp(-(((x-b).^2) ./ (sqrt(2)*(c/(2*sqrt(2*log(2))))).^2)); % FWHM version

% y = a*exp(-(((x-b).^2) ./ (sqrt(2)*c).^2)); % simga version
end