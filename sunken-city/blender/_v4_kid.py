_VC = {}


def _sm(arr, sigma=1.3):
    r = int(sigma * 3)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    return np.convolve(np.pad(arr, (r, r), mode="edge"), k, mode="valid")


def _vault_tables():
    if _VC:
        return _VC
    d62 = kid_state_v1(62 - SHIFT)
    frs = np.arange(62, HOOK + 1)

    def K(keys, smooth=1.3):
        ks = sorted(keys)
        return _sm(np.interp(frs, [k[0] for k in ks], [k[1] for k in ks]), smooth)
    P0 = d62["pos"]
    _VC["frs"] = frs
    _VC["x"] = K([(62, P0[0]), (65, 1.95), (67, 2.05), (69, 2.3), (72, 2.75), (75, 3.0), (HOOK, KID_EX)])
    _VC["y"] = K([(62, P0[1]), (66, -0.9), (70, -0.4), (75, 0.2), (HOOK, KID_ENTRY_Y)])
    z = np.interp(frs, [62, 64, 66, 68, 70, 72, 75], [P0[2], 2.75, 3.1, 3.2, 3.2, 3.18, 3.1])
    tb = (frs - 75) / 24.0
    vz = (0.55 - 3.1 + 4.9 * ((HOOK - 75) / 24.0) ** 2) / ((HOOK - 75) / 24.0)
    z = np.where(frs <= 75, z, 3.1 + vz * tb - 4.9 * tb * tb)
    _VC["z"] = _sm(z, 1.0)
    _VC["z"][-1] = 0.55
    _VC["roll"] = K([(62, 0), (64, -0.6), (66, -1.3), (68, -1.7), (70, -1.8), (75, -1.8), (79, -1.6), (85, -0.9), (91, -0.3), (HOOK, 0.0)])
    for nm in ("hipL", "hipR"):
        _VC[nm] = K([(62, d62[nm]), (64, 1.2), (66, 1.4), (70, 1.3), (73, 0.6), (76, 0.3), (85, 0.15), (HOOK, 0.05)])
    for nm in ("kneeL", "kneeR"):
        _VC[nm] = K([(62, d62[nm]), (64, 1.2), (66, 1.6), (70, 1.5), (73, 0.8), (76, 0.4), (85, 0.2), (HOOK, 0.08)])
    for nm in ("shL", "shR"):
        _VC[nm] = K([(62, d62[nm]), (66, 0.9), (69, 0.5), (72, 0.8), (75, 2.2), (82, 2.7), (HOOK, 2.9)])
    for nm in ("shLy", "shRy"):
        _VC[nm] = K([(62, 0), (66, -0.6), (69, -1.15), (72, -0.7), (75, 0.0), (HOOK, 0.0)])
    for nm in ("elL", "elR"):
        _VC[nm] = K([(62, d62[nm]), (66, 0.5), (69, 0.2), (75, 0.3), (HOOK, 0.2)])
    _VC["armAbd"] = K([(62, d62["armAbd"]), (75, 0.1), (82, 0.5), (HOOK, 0.3)])
    _VC["lean"] = K([(62, d62["lean"]), (66, -0.15), (70, 0.1), (75, 0.25), (85, 0.05), (HOOK, -0.05)])
    _VC["headp"] = K([(62, d62["headp"]), (70, 0.3), (HOOK, -0.05)])
    return _VC


def kid_vault(f):
    T = _vault_tables()
    i = int(f - 62)
    d = {"pos": (float(T["x"][i]), float(T["y"][i]), float(T["z"][i])), "twist": 0.0, "pitch": 0.0, "roll": float(T["roll"][i])}
    for nm in ("hipL", "hipR", "kneeL", "kneeR", "shL", "shR", "shLy", "shRy", "elL", "elR", "armAbd", "lean", "headp"):
        d[nm] = float(T[nm][i])
    return d


def kid_uw(f):
    d = {}
    tt = f - HOOK
    vz0, vy0, tau = -6.2, 1.0, 9.0
    z = 0.55 + vz0 * tau * (1 - math.exp(-tt / tau)) / 24.0 - 0.28 * max(0, tt - 20) / 24.0
    y = KID_ENTRY_Y + vy0 * tau * (1 - math.exp(-tt / tau)) / 24.0
    rel = smoothstep(HOOK + 8, HOOK + 40, f)
    d["pos"] = (KID_EX + 0.12 * rel + 0.4 * tau * (1 - math.exp(-tt / tau)) / 24.0, y, z)
    d["hipL"] = lerp(0.05, 0.55, rel)
    d["hipR"] = lerp(0.05, 0.25, rel)
    d["kneeL"] = lerp(0.08, 0.9, rel)
    d["kneeR"] = lerp(0.08, 0.6, rel)
    d["shL"] = lerp(2.9, 2.3, rel)
    d["shR"] = lerp(2.9, 2.1, rel)
    d["elL"] = lerp(0.2, 0.3, rel)
    d["elR"] = lerp(0.2, 0.3, rel)
    d["armAbd"] = lerp(0.3, 0.6, rel)
    d["lean"] = lerp(-0.05, -0.25, rel)
    d["twist"] = 0.1 * rel * math.sin(tt * 0.12)
    d["headp"] = lerp(0.0, -0.1, rel)
    d["pitch"] = lerp(0.0, -0.5, smoothstep(HOOK, HOOK + 14, f))
    d["roll"] = 0.0
    return d


def kid_state(f):
    if f <= 62:
        return kid_state_v1(f - SHIFT)
    if f <= HOOK:
        return kid_vault(f)
    return kid_uw(f)
