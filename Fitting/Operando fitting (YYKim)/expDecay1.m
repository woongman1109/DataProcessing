function y = expDecay1(x,a,b,c)
% exponential background
% a: scale factor
% b: decline ratio
% c: linear background
    y = a.*(x.^(-b))+c;

end
