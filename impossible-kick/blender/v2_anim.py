# v2 animation: juggling, the strike at HOOK (frame 96 = 4.000 s), the 16 s FPV flight, ending B (crossbar ring, drop, keeper, net pocket).
# exec()'d by scene.py after the v1 helpers are defined; it overrides animate_can and build_camera.
def animate_can(can):
    prev = Euler((0, 0, 0))
    # ---- 0-4 s: juggling taps, the flick, the fall and the half-volley set-up (analytic physics in jug_z / jug_xy)
    for f in range(F0, HOOK):
        p = jug_pos(f)
        u = min(1.0, max(0.0, (f-FLICK_T0)/(FLICK_T1-FLICK_T0)))
        k = 1-smooth(u)
        ax = (0.35*math.sin(f*0.45)+0.15)*(1-u) + (4*math.pi*k if u > 0 else 0.0)
        ay = 0.30*math.sin(f*0.33+1)*(1-u) + 0.25*k*math.sin(f*0.5)
        az = 0.09*f
        can.location = p; can.rotation_euler = (ax, ay, az)
        can.keyframe_insert('location', frame=f); can.keyframe_insert('rotation_euler', frame=f)
    ang_t, ang_s = 0.0, 0.0
    prevdir = Vector((0, 0.5, 1)).normalized()
    for f in range(HOOK, F1+1):
        p = can_pos(f)
        v = can_pos(f+0.5)-can_pos(f-0.5) if f > HOOK else Vector((0, 0.5, 1))
        d = v.normalized() if v.length > 1e-6 else prevdir
        rate = 17.0*math.exp(-(f-HOOK)/300.0)                  # deg/frame, end-over-end tumble
        if f >= 606: rate *= max(0.0, 1-(f-606)/12.0)
        ang_t += math.radians(rate); ang_s += math.radians(7.0*(1 if f < 606 else 0.0))
        yaw = math.atan2(-d.x, d.y)
        R = Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(ang_t + 0.9, 3, 'X') @ Matrix.Rotation(ang_s, 3, 'Z')
        if f >= 618:   # lying in the net pocket
            R = Matrix.Rotation(0.5, 3, 'Z') @ Matrix.Rotation(math.radians(-38), 3, 'X') @ Matrix.Rotation(math.radians(20), 3, 'Y')
        if f == HOOK: R = Matrix.Rotation(0.4, 3, 'Z')
        e = R.to_euler('XYZ', prev); prev = e
        can.location = p; can.rotation_euler = e
        can.keyframe_insert('location', frame=f); can.keyframe_insert('rotation_euler', frame=f)
        prevdir = d
    set_interp(can, 'LINEAR')
    sk = can.data.shape_keys.key_blocks['kick_dent']
    sk.value = 0; sk.keyframe_insert('value', frame=HOOK-1); sk.value = 1.0; sk.keyframe_insert('value', frame=HOOK+1)
    # scale cheat: the can grows to 2x during the city/stadium run so it still reads at goal distance (camera back-off scales with it)
    for f_, sc_ in ((0, 1.6), (60, 1.6), (95, 1.0), (470, 1.0), (560, 2.0), (596, 2.0), (620, 3.0), (719, 3.0)):
        can.scale = (sc_,)*3; can.keyframe_insert('scale', frame=f_)
    can.data.transform(Matrix.Translation((0, 0, -0.061)))     # origin to mid-height (locations above are mid-height positions)

def can_scale(f): return 1.0 + 1.0*smooth((f-470)/90.0) + 1.0*smooth((f-596)/24.0)

def build_camera(can):
    cd = bpy.data.cameras.new('cam'); cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 36.0; cd.lens = 24.0
    cd.clip_start = 0.02; cd.clip_end = 3000
    cd.dof.use_dof = True
    cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
    fo = bpy.data.objects.new('focus', None); sc.collection.objects.link(fo); cd.dof.focus_object = fo
    def noise(f, seed, amp, freq=1.0):
        return amp*(math.sin(f*0.31*freq+seed)+0.6*math.sin(f*0.77*freq+seed*2.3)+0.35*math.sin(f*1.71*freq+seed*4.1))
    prev = Euler((0, 0, 0)); dsm = Vector((0, 0.5, 1)).normalized(); rollsm = 0.0; prevyaw = None
    HOLD = [None]; tsm = [Vector((0.05, 0.05, 0.25))]
    def kick_pos(f):
        t = min(f, HOOK)/float(HOOK); s_ = smooth(t)
        # handheld dolly along the footballer at knee height: from behind-right and back off, closing to the v1 strike position
        x = 0.85+(0.58-0.85)*s_ + 0.05*math.sin(t*2.4)
        y = -1.05+(0.16+1.05)*s_
        z = 0.30+(0.09-0.30)*s_ + 0.02*math.sin(t*5.0)
        return Vector((x, y, z))
    def kick_raw_target(f):
        pc = jug_pos(min(f, HOOK))
        cz = pc.z
        z = 0.14+0.5*cz if cz < 0.8 else 0.54+0.75*(cz-0.8)
        if f >= HOOK-10: z = min(z, 0.14+0.5*cz)
        return Vector((0.6*pc.x+0.4*0.03, 0.9*pc.y+0.1*(pc.y-0.05), max(0.2, z)))
    for f in range(F0, F1+1):
        if f <= HOOK:
            tsm[0] = tsm[0] + (kick_raw_target(f)-tsm[0])*0.30      # operator lag on the tilt
            pos = kick_pos(f); tgt = Vector(tsm[0]); roll = math.radians(-1.5)+noise(f, 5, 0.004)
            if f == HOOK: HOLD[0] = (Vector(pos), Vector(tgt))
            jolt = 0.0; sh = 0.007
        else:
            c0, tgt0 = HOLD[0]
            jolt = math.exp(-(f-HOOK)/2.5)
            p = can_pos(f); v = can_pos(f+0.5)-can_pos(f-0.5); d = v.normalized()
            dsm = (dsm*0.6+d*0.4).normalized()
            sca = can_scale(f)
            back = (0.55 if f < HOOK+12 else 0.75)*sca
            chase = p - dsm*back + Vector((0, 0, 0.16*sca))
            w = smooth((f-HOOK-3)/13.0); w2 = smooth((f-HOOK-0.5)/9.0)
            pos = c0*(1-w) + chase*w
            tgt = tgt0*(1-w2) + (p + dsm*0.35*sca)*w2
            yawv = math.atan2(d.x, d.y); yr = 0 if prevyaw is None else (yawv-prevyaw); prevyaw = yawv
            rollsm = rollsm*0.85 + (-yr*22.0)*0.15
            roll = (rollsm*w + noise(f, 6, 0.010)*w + (math.radians(-1.5)*(1-w)))
            roll *= 1-smooth((f-598)/12.0)
            spd = min(1.0, (can_pos(f+1)-can_pos(f)).length*FPS/24.0)
            sh = 0.006+0.028*spd
            if f >= 606:    # ending: chase stops at the crossbar strike, hands over to a low camera in front of the goal
                e = smooth((f-606)/16.0)
                hold = Vector((-1.7, 307.0, 1.25))                        # oblique low view from the left-front: pocket, net, keeper and crowd in one frame
                pb = smooth((f-660)/60.0)
                hold = hold + Vector((-0.9*pb, -1.3*pb, 0.25*pb))        # slow pull-back over the last 2 s
                pos = pos*(1-e) + hold*e
                pk = p*0.55 + Vector((POCKET_X, NET_BACK_Y+0.45, POCKET_Z+0.15))*0.45
                tgt = tgt*(1-e) + pk*e
                sh = 0.006*(1-e)+0.0035*e
        pos = pos + Vector((noise(f, 11, sh, 1.3), noise(f, 12, sh, 1.1), noise(f, 13, sh, 1.7)))
        if f >= HOOK: pos += Vector((0.015*jolt*math.sin(f*2.1), 0.02*jolt, -0.02*jolt))
        tgt = tgt + Vector((noise(f, 21, sh*0.6), noise(f, 22, sh*0.6), noise(f, 23, sh*0.5)))
        if f in (607, 608): pos += Vector((0.02, 0, 0.03))      # small reaction to the bar ring
        q = (tgt-pos).to_track_quat('-Z', 'Y')
        rq = q @ Quaternion((0, 0, 1), roll)
        e_ = rq.to_euler('XYZ', prev); prev = e_
        cam.location = pos; cam.rotation_euler = e_
        cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)
        fo.location = jug_pos(f) if f < HOOK else can_pos(f)
        fo.keyframe_insert('location', frame=f)
        cd.dof.aperture_fstop = 3.2 if f < HOOK else 3.5
        cd.dof.keyframe_insert('aperture_fstop', frame=f)
        cd.lens = 24.0 if f < HOOK else (20.0 + 10.0*smooth((f-596)/30.0))
        cd.keyframe_insert('lens', frame=f)
    set_interp(cam, 'LINEAR')
    for ob in (fo,): set_interp(ob, 'LINEAR')
    return cam
