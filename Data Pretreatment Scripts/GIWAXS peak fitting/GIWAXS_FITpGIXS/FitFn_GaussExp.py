# FitFn_GaussExp.py
"""
Exponential background + N peaks 피팅 모듈

모델:  y = a·x^(-b) + c  +  Σ peak_i(...)

Peak types:
  gaussian:      [A, μ, FWHM]        → 3 params/peak
  lorentzian:    [A, μ, FWHM]        → 3 params/peak
  pseudo_voigt:  [A, μ, FWHM, η]     → 4 params/peak
                 η∈[0,1]: 0=pure Gaussian, 1=pure Lorentzian
"""

import numpy as np
from scipy.optimize import least_squares

MEAN_LB_FACTOR = 0.95
MEAN_UB_FACTOR = 1.05
PEAK_MASK_FWHM_FACTOR = 2.5

PEAK_TYPES = ('pseudo_voigt', 'gaussian', 'lorentzian')

def _npp(peak_type):
    return 4 if peak_type == 'pseudo_voigt' else 3

def fwhm_to_sigma(fwhm):
    return fwhm / (2 * np.sqrt(2 * np.log(2)))

# =============================================================================
# Peak functions
# =============================================================================

def exp_background(x, a, b, c):
    return a * np.power(x, -b) + c

def gaussian(x, A, mu, fwhm):
    sigma = fwhm_to_sigma(fwhm)
    if sigma == 0: sigma = 1e-8
    return A * np.exp(-((x - mu) ** 2) / (2 * sigma ** 2))

def lorentzian(x, A, mu, fwhm):
    hg = fwhm / 2.0
    if hg == 0: hg = 1e-8
    return A / (1.0 + ((x - mu) / hg) ** 2)

def pseudo_voigt(x, A, mu, fwhm, eta):
    return eta * lorentzian(x, A, mu, fwhm) + (1 - eta) * gaussian(x, A, mu, fwhm)

def peak_func(x, peak_params, peak_type='gaussian'):
    if peak_type == 'pseudo_voigt':
        return pseudo_voigt(x, *peak_params)
    elif peak_type == 'lorentzian':
        return lorentzian(x, *peak_params)
    return gaussian(x, *peak_params)

# =============================================================================
# Pack / Unpack
# =============================================================================

def pack_params(bkg_params, peak_params_list):
    flat = list(bkg_params)
    for pk in peak_params_list:
        flat.extend(pk)
    return np.array(flat, dtype=float)

def unpack_params(params, peak_type='gaussian'):
    a, b, c = params[0], params[1], params[2]
    npp = _npp(peak_type)
    peaks = []
    for i in range(3, len(params), npp):
        peaks.append(tuple(params[i:i+npp]))
    return (a, b, c), peaks

# =============================================================================
# Model
# =============================================================================

def model_func(x, params, peak_type='gaussian'):
    (a, b, c), peak_params = unpack_params(params, peak_type)
    bkg = exp_background(x, a, b, c)
    individual = [peak_func(x, pk, peak_type) for pk in peak_params]
    total = bkg + sum(individual)
    return total, bkg, individual

def _weights(y):
    return 1.0

def residuals(params, x, y, peak_type):
    total, _, _ = model_func(x, params, peak_type)
    return (total - y) * _weights(y)

# =============================================================================
# Bounds & Masks
# =============================================================================

def make_bounds(x, peak_positions, peak_type='gaussian'):
    x_min, x_max = x.min(), x.max()
    x_range = x_max - x_min

    lb = [0, -20, 0]
    ub = [np.inf, 20, np.inf]

    for (px, _) in peak_positions:
        # FWHM이 0이 되지 않도록 1e-4 하한 방어선 유지
        lb.extend([0, px * MEAN_LB_FACTOR, 1e-4])
        ub.extend([np.inf, px * MEAN_UB_FACTOR, x_range])
        if peak_type == 'pseudo_voigt':
            lb.append(0.0)
            ub.append(1.0)

    return np.array(lb), np.array(ub)

def _make_peak_mask(x, peak_ig_list, factor=None):
    f = factor if factor is not None else PEAK_MASK_FWHM_FACTOR
    mask = np.zeros(len(x), dtype=bool)
    for pk in peak_ig_list:
        mu, fwhm = pk[1], pk[2]
        half_range = fwhm * f
        mask |= (x >= mu - half_range) & (x <= mu + half_range)
    return mask

def _bkg_residuals(bkg_params, x, y):
    a, b, c = bkg_params
    return (exp_background(x, a, b, c) - y) * _weights(y)

def _to_pv_ig(peak_ig_list):
    return [(A, mu, fwhm, 0.5) for (A, mu, fwhm) in peak_ig_list]

def _to_gl_ig(peak_ig_list):
    return [(pk[0], pk[1], pk[2]) for pk in peak_ig_list]

# =============================================================================
# 2-step fitting
# =============================================================================

def _amp_indices(n_peaks, peak_type):
    npp = _npp(peak_type)
    idx = [0, 2]
    for j in range(n_peaks):
        idx.append(3 + j * npp)
    return idx

def _normalize_params(params, scale, n_peaks, peak_type):
    p = params.copy()
    for i in _amp_indices(n_peaks, peak_type):
        if i < len(p): p[i] /= scale
    return p

def _denormalize_params(params, scale, n_peaks, peak_type):
    p = params.copy()
    for i in _amp_indices(n_peaks, peak_type):
        if i < len(p): p[i] *= scale
    return p

def _fit_single_type(ig, x_fit, y_fit, ptype, lb, ub, n_peaks=None):
    y_max = np.max(np.abs(y_fit))
    if y_max == 0: y_max = 1.0

    if n_peaks is None:
        npp = _npp(ptype)
        n_peaks = (len(ig) - 3) // npp

    y_norm = y_fit / y_max
    ig_n = _normalize_params(ig, y_max, n_peaks, ptype)
    lb_n = _normalize_params(lb, y_max, n_peaks, ptype)
    ub_n = _normalize_params(ub, y_max, n_peaks, ptype)

    # NaN/Inf 방어
    ig_n = np.where(np.isfinite(ig_n), ig_n, 1e-6)
    lb_n = np.where(np.isfinite(lb_n), lb_n, 0.0)
    ub_n = np.where(np.isfinite(ub_n), ub_n, 1e10)

    ig_clamped = np.clip(ig_n, lb_n, ub_n)

    try:
        result = least_squares(
            residuals, ig_clamped, args=(x_fit, y_norm, ptype),
            method='trf', ftol=1e-8, xtol=1e-8, bounds=(lb_n, ub_n),
            loss='linear'
        )
        # nan 폭탄 원천 차단: 알고리즘이 nan을 뱉으면 에러로 처리
        if np.any(np.isnan(result.x)):
            raise ValueError("least_squares returned NaNs.")
            
        params_real = _denormalize_params(result.x, y_max, n_peaks, ptype)
        return {
            'params': params_real, 'success': result.success,
            'cost': result.cost, 'message': result.message,
        }
    except Exception as e:
        print(f"    {ptype} fitting failed: {e}")
        # 실패 시 오염되지 않은 원래의 ig 반환
        return {'params': ig.copy(), 'success': False, 'cost': None, 'message': str(e)}

def _step1_bkg(x_all, y_all, bkg_ig, peak_ig_list_3, mask_factor):
    peak_mask = _make_peak_mask(x_all, peak_ig_list_3, factor=mask_factor)
    bkg_mask = ~peak_mask
    if bkg_mask.sum() < 3:
        bkg_mask = np.ones(len(x_all), dtype=bool)

    x_bkg, y_bkg = x_all[bkg_mask], y_all[bkg_mask]

    y_max = np.max(np.abs(y_bkg))
    if y_max == 0: y_max = 1.0
    y_norm = y_bkg / y_max

    bkg_ig_n = [bkg_ig[0] / y_max, bkg_ig[1], bkg_ig[2] / y_max]
    # NaN/Inf guard: a,c must be >= 0; b can be negative
    bkg_ig_n[0] = bkg_ig_n[0] if np.isfinite(bkg_ig_n[0]) and bkg_ig_n[0] >= 0 else 1e-6
    bkg_ig_n[1] = bkg_ig_n[1] if np.isfinite(bkg_ig_n[1]) else 2.0
    bkg_ig_n[2] = bkg_ig_n[2] if np.isfinite(bkg_ig_n[2]) and bkg_ig_n[2] >= 0 else 1e-6
    bkg_lb_n = [0, -20, 0]
    bkg_ub_n = [np.inf, 20, np.inf]

    bkg_ig_n = np.clip(bkg_ig_n, bkg_lb_n, bkg_ub_n)

    try:
        bkg_result = least_squares(
            _bkg_residuals, bkg_ig_n,
            args=(x_bkg, y_norm),
            method='trf', ftol=1e-8, xtol=1e-8,
            bounds=(bkg_lb_n, bkg_ub_n),
            loss='linear'
        )
        if np.any(np.isnan(bkg_result.x)):
            raise ValueError("Background fit returned NaNs.")
            
        a0, b0, c0 = bkg_result.x
        return (a0 * y_max, b0, c0 * y_max), bkg_result.success
    except Exception as e:
        print(f"    Step1 bkg failed: {e}")
        return bkg_ig, False

def _apply_bkg_tight_bounds(lb, ub, bkg_fitted, bkg_bounds_override):
    BKG_MARGIN = 0.20
    if bkg_bounds_override is not None:
        c_lb, c_ub = bkg_bounds_override
        for i in range(3):
            if c_lb[i] is not None: lb[i] = c_lb[i]
            if c_ub[i] is not None: ub[i] = c_ub[i]
    else:
        for i, v in enumerate(bkg_fitted):
            if not np.isfinite(v):
                lb[i] = -20 if i == 1 else 0
                ub[i] = max(ub[i], 0.01)
            elif v < 0:
                # only b (index 1) can be negative
                if i == 1:
                    lb[i] = max(lb[i], v * (1.0 + BKG_MARGIN))  # more negative
                    ub[i] = min(ub[i], v * (1.0 - BKG_MARGIN))  # less negative
                else:
                    lb[i] = 0
                    ub[i] = max(ub[i], 0.01)
            elif v > 0:
                lb[i] = max(lb[i], v * (1.0 - BKG_MARGIN))
                ub[i] = min(ub[i], v * (1.0 + BKG_MARGIN))
            else:  # v == 0
                lb[i] = -0.01 if i == 1 else 0
                ub[i] = max(ub[i], 0.01)

def fit_region(x, y, bkg_ig, peak_ig_list, peak_positions,
               bkg_bounds_override=None, mask_factor=None):
    valid = np.isfinite(y) & (y != 0)
    x_all, y_all = x[valid], y[valid]
    n_peaks = len(peak_ig_list)
    ig_gl = pack_params(bkg_ig, peak_ig_list)

    if len(x_all) < 4:
        ig_pv = pack_params(bkg_ig, _to_pv_ig(peak_ig_list))
        dummy_gl = {'params': ig_gl, 'success': False, 'cost': None, 'message': 'Not enough data'}
        dummy_pv = {'params': ig_pv, 'success': False, 'cost': None, 'message': 'Not enough data'}
        return {'n_peaks': n_peaks, 'gaussian': dummy_gl,
                'lorentzian': dummy_gl.copy(), 'pseudo_voigt': dummy_pv}

    bkg_fitted, bkg_ok = _step1_bkg(x_all, y_all, bkg_ig, peak_ig_list, mask_factor)

    results = {'n_peaks': n_peaks}

    pv_ig_list = _to_pv_ig(peak_ig_list)
    lb_pv, ub_pv = make_bounds(x_all, peak_positions, 'pseudo_voigt')
    _apply_bkg_tight_bounds(lb_pv, ub_pv, bkg_fitted, bkg_bounds_override)
    ig_pv = pack_params(bkg_fitted, pv_ig_list)
    results['pseudo_voigt'] = _fit_single_type(ig_pv, x_all, y_all, 'pseudo_voigt', lb_pv, ub_pv, n_peaks)
    
    for ptype in ('gaussian', 'lorentzian'):
        lb, ub = make_bounds(x_all, peak_positions, ptype)
        _apply_bkg_tight_bounds(lb, ub, bkg_fitted, bkg_bounds_override)
        ig = pack_params(bkg_fitted, peak_ig_list)
        results[ptype] = _fit_single_type(ig, x_all, y_all, ptype, lb, ub, n_peaks)

    return results

# ─── 파라미터 개별 override (배수 방식 롤백 유지) ───
def _apply_amp_overrides(ig, lb, ub, amp_overrides, peak_type):
    if amp_overrides is None: return
    npp = _npp(peak_type)
    for j, ao in enumerate(amp_overrides):
        if ao is None: continue
        value, lb_f, ub_f = ao
        amp_idx = 3 + j * npp
        if amp_idx >= len(ig): continue
        if value is not None: ig[amp_idx] = value
        
        v = ig[amp_idx]
        if lb_f is not None: lb[amp_idx] = v * lb_f
        if ub_f is not None: ub[amp_idx] = v * ub_f

def _apply_mean_overrides(ig, lb, ub, mean_overrides, peak_type):
    if mean_overrides is None: return
    npp = _npp(peak_type)
    for j, mo in enumerate(mean_overrides):
        if mo is None: continue
        value, lb_f, ub_f, fixed = mo
        mean_idx = 3 + j * npp + 1
        if mean_idx >= len(ig): continue
        if value is not None: ig[mean_idx] = value
        
        v = ig[mean_idx]
        if fixed:
            lb[mean_idx] = v
            ub[mean_idx] = v
        else:
            if lb_f is not None: lb[mean_idx] = v * lb_f
            if ub_f is not None: ub[mean_idx] = v * ub_f

def _apply_fwhm_overrides(ig, lb, ub, fwhm_overrides, peak_type):
    if fwhm_overrides is None: return
    npp = _npp(peak_type)
    for j, fo in enumerate(fwhm_overrides):
        if fo is None: continue
        value, lb_f, ub_f = fo
        fwhm_idx = 3 + j * npp + 2
        if fwhm_idx >= len(ig): continue
        if value is not None: ig[fwhm_idx] = value
        
        v = ig[fwhm_idx]
        if lb_f is not None: lb[fwhm_idx] = max(v * lb_f, 1e-6)
        if ub_f is not None: ub[fwhm_idx] = v * ub_f

def fit_region_single(x, y, bkg_ig, peak_ig_list, peak_positions,
                      peak_type='gaussian', bkg_bounds_override=None,
                      mask_factor=None, mean_overrides=None, fwhm_overrides=None,
                      amp_overrides=None):
    valid = np.isfinite(y) & (y != 0)
    x_all, y_all = x[valid], y[valid]

    pig_3 = _to_gl_ig(peak_ig_list) if len(peak_ig_list[0]) > 3 else list(peak_ig_list)
    n_peaks = len(pig_3)

    pig_use = _to_pv_ig(pig_3) if peak_type == 'pseudo_voigt' else pig_3
    ig = pack_params(bkg_ig, pig_use)

    if len(x_all) < 4:
        dummy = {'params': ig, 'success': False, 'cost': None, 'message': 'Not enough data'}
        return {'n_peaks': n_peaks, peak_type: dummy}

    bkg_fitted, _ = _step1_bkg(x_all, y_all, bkg_ig, pig_3, mask_factor)

    lb, ub = make_bounds(x_all, peak_positions, peak_type)
    _apply_bkg_tight_bounds(lb, ub, bkg_fitted, bkg_bounds_override)
    ig_s2 = pack_params(bkg_fitted, pig_use)
    
    _apply_amp_overrides(ig_s2, lb, ub, amp_overrides, peak_type)
    _apply_mean_overrides(ig_s2, lb, ub, mean_overrides, peak_type)
    _apply_fwhm_overrides(ig_s2, lb, ub, fwhm_overrides, peak_type)
    
    result = _fit_single_type(ig_s2, x_all, y_all, peak_type, lb, ub, n_peaks)
    return {'n_peaks': n_peaks, peak_type: result}

def refit_region(x, y, prev_params, peak_positions,
                 bkg_override=None, bkg_margins=None, peak_type='gaussian',
                 original_peak_ig=None, mask_factor=None,
                 mean_overrides=None, fwhm_overrides=None, amp_overrides=None):
    npp = _npp(peak_type)
    (a_prev, b_prev, c_prev), _ = unpack_params(prev_params, peak_type)

    if original_peak_ig is not None:
        pig_3 = _to_gl_ig(original_peak_ig) if len(original_peak_ig[0]) > 3 else list(original_peak_ig)
    else:
        _, prev_peaks = unpack_params(prev_params, peak_type)
        pig_3 = _to_gl_ig(prev_peaks) if npp == 4 else list(prev_peaks)

    if bkg_override is not None:
        a_new = bkg_override[0] if bkg_override[0] is not None else a_prev
        b_new = bkg_override[1] if bkg_override[1] is not None else b_prev
        c_new = bkg_override[2] if bkg_override[2] is not None else c_prev
    else:
        a_new, b_new, c_new = a_prev, b_prev, c_prev

    bkg_ig = (a_new, b_new, c_new)
    bkg_bounds_override = None
    
    if bkg_margins is not None:
        custom_lb, custom_ub = [None, None, None], [None, None, None]
        bkg_vals = [a_new, b_new, c_new]
        for i, mg in enumerate(bkg_margins):
            if mg is not None:
                lb_f, ub_f = mg
                v = bkg_vals[i]
                if lb_f is not None: custom_lb[i] = v * lb_f
                if ub_f is not None: custom_ub[i] = v * ub_f
        bkg_bounds_override = (custom_lb, custom_ub)

    return fit_region_single(x, y, bkg_ig, pig_3, peak_positions,
                             peak_type=peak_type,
                             bkg_bounds_override=bkg_bounds_override,
                             mask_factor=mask_factor,
                             mean_overrides=mean_overrides,
                             fwhm_overrides=fwhm_overrides,
                             amp_overrides=amp_overrides)

def perform_fitting_all(sheet_region_info):
    fit_results = {}
    for sheet_name, regions in sheet_region_info.items():
        sheet_results = []
        for i, reg in enumerate(regions):
            result = fit_region(reg['x'], reg['y'], reg['bkg_ig'], reg['peak_ig_list'], reg['peak_positions'])
            result['range'] = reg['range']
            result['x'], result['y'] = reg['x'], reg['y']
            result['peak_positions'] = reg['peak_positions']
            result['original_peak_ig'] = reg['peak_ig_list']
            result['original_bkg_ig'] = reg['bkg_ig']
            sheet_results.append(result)
        fit_results[sheet_name] = sheet_results
    return fit_results