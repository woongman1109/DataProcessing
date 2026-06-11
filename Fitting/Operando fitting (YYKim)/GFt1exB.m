function y = GFt1exB(x,p1,p2,p3,p4,p5,p6)
% x : x axis
% p : parameter

% for Gaussian distribution + exponential background

TGF1= Gaussian(x,p4,p5,p6);

BKG = expBKG(x,p1,p2,p3);

y = BKG+TGF1 ;

end

