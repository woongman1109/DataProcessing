function y = ExpAssocDelay2(x, Yb, A1, D1, t1, A2, D2, t2)
    y = piecewise(Yb, x<D1, Yb + A1*(1-exp(-(x-D1)/t1)), D1<=x<D2, Yb + A1*(1-exp(-(x-D1)/t1)) + A2*(1-exp(-(x-D2)/t2)), x>=D2);
end