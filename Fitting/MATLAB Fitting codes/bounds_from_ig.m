function [lb_arr, ub_arr] = bounds_from_ig(ig_mat, ampLBr, ampUBr, meanLBd, meanUBd, fwhmLBd, fwhmUBd, etaLB, etaUB)
% ig_mat: n×4 행렬, 각 행 = [amp, mean, FWHM, eta]  (이번 반복의 initial guess)
    lb_mat = [ig_mat(:,1).*ampLBr(:), ig_mat(:,2)+meanLBd(:), ig_mat(:,3)+fwhmLBd(:), etaLB(:)];
    ub_mat = [ig_mat(:,1).*ampUBr(:), ig_mat(:,2)+meanUBd(:), ig_mat(:,3)+fwhmUBd(:), etaUB(:)];
    lb_arr = reshape(lb_mat.', 1, []);
    ub_arr = reshape(ub_mat.', 1, []);
end