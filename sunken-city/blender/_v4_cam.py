    # ================= v4: FPV dive through the forum (frames 109..480) =================
    aim_old = aim.copy()
    BANK = np.zeros(NF)
    F0, F1 = 109, 480
    CX_, CY_, RO_ = 0.5, 63.5, 4.5          # toppled statue = orbit centre
    WIN_ = np.array([0.0, 84.0, -15.6])

    wp = [(124, (3.3, 5.6, -8.0)), (148, (1.8, 11.0, -18.6)), (162, (1.4, 16.8, -19.4)),
          (175, (1.4, 22.6, -19.5)), (188, (-1.4, 27.0, -19.7)), (201, (1.4, 31.4, -19.4)),
          (214, (-1.4, 35.8, -19.7)), (227, (1.4, 40.2, -19.5)), (240, (-1.4, 44.6, -19.6)),
          (252, (0.6, 49.0, -20.3)), (260, (2.4, 51.4, -21.0)), (272, (0.5, 56.0, -18.2)),
          (279, (CX_, CY_ - RO_, -19.0))]
    for k_ in range(1, 7):                  # clockwise half orbit, 30 deg steps
        a_ = math.radians(-90 - 30 * k_)
        wp.append((int(round(279 + 6.5 * k_)), (CX_ + RO_ * math.cos(a_), CY_ + RO_ * math.sin(a_), -19.0 - 0.7 * math.sin(k_ * 0.5))))
    wp += [(328, (4.5, 68.6, -19.6)), (337, (7.0, 70.6, -19.8)), (346, (8.6, 73.3, -19.5)), (352, (8.8, 75.8, -18.8)),
           (357, (8.8, 77.4, -18.0)), (365, (8.8, 80.0, -17.9)), (373, (6.0, 81.3, -18.0)), (386, (1.0, 81.6, -18.4)),
           (397, (-3.6, 80.6, -18.9)), (403, (-4.4, 78.4, -19.4)), (409, (-4.2, 75.5, -19.9)),
           (417, (-4.0, 72.5, -20.3)), (426, (-3.0, 68.5, -20.9)), (437, (-2.0, 63.5, -19.8)),
           (446, (0.0, 60.8, -17.8)), (454, (1.8, 61.8, -16.9)), (462, (1.0, 63.3, -16.5)), (470, (0.1, 64.8, -16.3))]
    wp.sort(key=lambda w: w[0])
    wfr = np.array([F0] + [w[0] for w in wp] + [F1], float)
    WP = np.array([pos[F0 - 1]] + [w[1] for w in wp] + [pos[F1 - 1]], float)
    Mv = np.zeros_like(WP)
    for i_ in range(len(WP)):
        if i_ == 0:
            Mv[i_] = pos[F0 - 1] - pos[F0 - 2]
        elif i_ == len(WP) - 1:
            Mv[i_] = pos[F1 - 1] - pos[F1 - 2]
        else:
            Mv[i_] = (WP[i_ + 1] - WP[i_ - 1]) / (wfr[i_ + 1] - wfr[i_ - 1])
    PP = np.zeros((F1 - F0 + 1, 3))
    for k_, f_ in enumerate(range(F0, F1 + 1)):
        i_ = int(min(max(np.searchsorted(wfr, f_, side="right") - 1, 0), len(WP) - 2))
        h_ = wfr[i_ + 1] - wfr[i_]
        t_ = (f_ - wfr[i_]) / h_
        PP[k_] = ((2 * t_**3 - 3 * t_**2 + 1) * WP[i_] + (t_**3 - 2 * t_**2 + t_) * h_ * Mv[i_] +
                  (-2 * t_**3 + 3 * t_**2) * WP[i_ + 1] + (t_**3 - t_**2) * h_ * Mv[i_ + 1])
    # drone wobble (small, off-axis, two frequencies)
    tt_ = np.arange(F0, F1 + 1) / 24.0
    ramp_ = np.clip((tt_ - 4.6) / 0.6, 0, 1) * np.clip((20.0 - tt_) / 0.6, 0, 1)
    PP[:, 0] += ramp_ * (0.05 * np.sin(tt_ * 11.0) + 0.03 * np.sin(tt_ * 19.0 + 1.3))
    PP[:, 2] += ramp_ * (0.05 * np.sin(tt_ * 9.0 + 0.7) + 0.03 * np.sin(tt_ * 17.0))
    pos[F0 - 1:F1] = PP
    # look direction: tangent (look-ahead), statue during the orbit, window at the end, old aim at the start
    n_ = len(PP)
    look_t = np.zeros((n_, 3))
    for k_ in range(n_):
        a0, a1 = max(0, k_ - 3), min(n_ - 1, k_ + 5)
        look_t[k_] = PP[a1] - PP[a0]
    yaw_t = np.unwrap(np.arctan2(look_t[:, 0], look_t[:, 1]))
    pit_t = np.arctan2(look_t[:, 2], np.hypot(look_t[:, 0], look_t[:, 1]))
    fr_k = np.arange(F0, F1 + 1)

    def ang_to(target, ref_yaw):
        d_ = target - PP
        y_ = np.arctan2(d_[:, 0], d_[:, 1])
        y_ = y_ + 2 * np.pi * np.round((ref_yaw - y_) / (2 * np.pi))
        return y_, np.arctan2(d_[:, 2], np.hypot(d_[:, 0], d_[:, 1]))
    yaw_c, pit_c = ang_to(np.array([CX_, CY_, SEABED + 1.0]), yaw_t)
    wc = np.array([smoothstep(279, 288, f) * (1 - smoothstep(312, 324, f)) for f in fr_k])
    yaw_w, pit_w = ang_to(WIN_, yaw_t)
    ww = np.array([smoothstep(452, 476, f) for f in fr_k])
    yaw_o, pit_o = ang_to(aim_old[F0 - 1:F1], yaw_t)
    wo = np.array([1 - smoothstep(114, 142, f) for f in fr_k])
    yt = yaw_t * (1 - wc) + yaw_c * wc
    pt = pit_t * (1 - wc) + pit_c * wc
    yt = yt * (1 - ww) + yaw_w * ww
    pt = pt * (1 - ww) + pit_w * ww
    yt = yt * (1 - wo) + yaw_o * wo
    pt = pt * (1 - wo) + pit_o * wo
    # spring (underdamped) so the camera lags, overshoots a touch and settles
    def spring(tgt, w0, zeta, x0, v0=0.0):
        x_, v_ = x0, v0
        out_ = np.zeros_like(tgt)
        dt_ = 1.0 / 24.0
        for k_ in range(len(tgt)):
            a_ = w0 * w0 * (tgt[k_] - x_) - 2 * zeta * w0 * v_
            v_ += a_ * dt_
            x_ += v_ * dt_
            out_[k_] = x_
        return out_
    yaw_s = spring(yt, 11.0, 0.62, yt[0])
    pit_s = spring(pt, 11.0, 0.65, pt[0])
    # bank from yaw rate x speed, clamped to 25 deg; spring for overshoot
    spd = np.linalg.norm(np.gradient(PP, axis=0), axis=1) * 24.0
    yr = np.gradient(yaw_s) * 24.0
    bank_t = np.clip(np.arctan(-yr * spd / 9.81) * 1.5, -math.radians(25), math.radians(25))
    bank_s = spring(bank_t, 9.0, 0.5, 0.0)
    bank_s = np.clip(bank_s, -math.radians(25), math.radians(25))
    barrel = np.array([2 * math.pi * smoothstep(356, 372, f) for f in fr_k])
    BANK[F0 - 1:F1] = bank_s + barrel
    dirs = np.stack([np.sin(yaw_s) * np.cos(pit_s), np.cos(yaw_s) * np.cos(pit_s), np.sin(pit_s)], 1)
    aim[F0 - 1:F1] = PP + dirs * 10.0
    CAM_SPEED = spd
    for a_ in range(0, n_, 24):
        print("SPEED f%d-%d %.1f m/s" % (F0 + a_, F0 + min(a_ + 23, n_ - 1), spd[a_:a_ + 24].mean()))
    print("FPV path ok: mean speed %.1f m/s, max %.1f m/s" % (spd[20:340].mean(), spd.max()))
