# executed inside scene.py namespace: courtyard, window room, market street, city, stadium
P = lambda f: Vector(CAN(T(f)))      # f = OLD (v1) frame number; T() maps it to the v2 timeline

_PS = [Vector(CAN(f)) for f in np.arange(HOOK, 600, 0.5)]
def keep_clear(x0, x1, y0, y1, top, margin=5.0):
    """lower a building top so it never touches the can path (+margin)"""
    best = top
    for p in _PS:
        if y0-3 <= p.y <= y1+3 and x0-3 <= p.x <= x1+3:
            best = min(best, p.z-margin)
    return max(best, 3.0)

def bld(name, x0, x1, y0, y1, top, mat=None, base=0.0, clear=True, roof=True):
    if clear: top = keep_clear(x0, x1, y0, y1, top)
    o = box(name, ((x0+x1)/2, (y0+y1)/2, base+(top-base)/2), (x1-x0, y1-y0, top-base), mat or M['facade'])
    if roof:
        box(name+'_roof', ((x0+x1)/2, (y0+y1)/2, top+0.12), (x1-x0+0.3, y1-y0+0.3, 0.25), M['concrete'])
    return top

def roof_props(x0, x1, y0, y1, top, n=4):
    for k in range(n):
        x = random.uniform(x0+1, x1-1); y = random.uniform(y0+1, y1-1)
        r = random.random()
        if r < 0.35:   # water tank on legs
            cyl(f'tank{top:.0f}{k}', (x, y, top+1.9), 0.9, 1.6, M['tin'], seg=16)
            for dx, dy in ((-.6, -.6), (.6, -.6), (-.6, .6), (.6, .6)): cyl('tleg', (x+dx, y+dy, top+0.55), 0.04, 1.1, M['rust'], seg=6)
        elif r < 0.7:  # antenna mast
            cyl(f'ant{top:.0f}{k}', (x, y, top+3.0), 0.025, 6.0, M['black'], seg=6)
            for h in (3.5, 4.5, 5.4): box('ant_arm', (x, y, top+h), (0.02, 1.6-0.2*(h-3.5), 0.02), M['black'])
        elif r < 0.85:  # satellite dish
            sp = sphere('dish', (x, y, top+1.0), 0.45, M['concrete'], seg=12, scale=(1, 0.3, 1)); sp.rotation_euler = (0.3, 0, random.random()*6)
        else:
            box('chimney', (x, y, top+0.9), (0.6, 0.6, 1.8), M['brick'])
    box('parapet', ((x0+x1)/2, y0+0.1, top+0.5), (x1-x0, 0.2, 1.0), M['concrete'])

# ---------------------------------------------------------------- courtyard between alley mouth and the window building
def build_courtyard():
    box('court_ground', (0, 23, -0.5), (60, 40, 1.0), M['cobble'])
    for side, (x0, x1) in (('L', (-40, -7)), ('R', (7, 40))):
        for k, (y0, y1) in enumerate(((14, 20), (20, 26), (26, 32))):
            top = random.uniform(9, 15)
            top = bld(f'ct{side}{k}', x0, x1, y0, y1, top)
            roof_props(x0, x1, y0, y1, top, 3)
    # extend alley walls to the courtyard corners
    bld('alleyL', -9, -1.5, 14, 32, 13, M['brick'], clear=False, roof=False)
    bld('alleyR', 1.5, 9, 14, 32, 14.5, M['plaster'], clear=False, roof=False)
    # (the alley boxes above hide the open courtyard; carve it by making them start beyond x=+-7)
    for n in ('alleyL', 'alleyR'): bpy.data.objects.remove(bpy.data.objects[n])
    bld('alleyL2', -9, -7, 14, 32, 13, M['brick'], clear=False, roof=False)
    bld('alleyR2', 7, 9, 14, 32, 14.5, M['plaster'], clear=False, roof=False)
    # laundry & lines across the courtyard, a tree, a moped
    for k in range(3):
        y = 18+k*4.2; z = 5.5+k*0.9
        pts = [(-7+t*14, y, z-0.5*math.sin(math.pi*t)) for t in np.linspace(0, 1, 20)]
        crv = bpy.data.curves.new('cline', 'CURVE'); crv.dimensions = '3D'; crv.bevel_depth = 0.006
        sp = crv.splines.new('POLY'); sp.points.add(len(pts)-1)
        for p, q in zip(sp.points, pts): p.co = (*q, 1)
        co = bpy.data.objects.new('cline', crv); co.data.materials.append(M['black']); sc.collection.objects.link(co)
        for j in range(6):
            x = -5.5+j*2.0+random.uniform(-.3, .3); t = (x+7)/14
            cloth(f'cy{k}{j}', (x, y, z-0.5*math.sin(math.pi*t)-0.5), (0.5, 0.8), random.choice([(0.6, 0.12, 0.1), (0.85, 0.85, 0.8), (0.1, 0.25, 0.45), (0.9, 0.7, 0.2)]), wave=0.05, rot=(math.pi/2, 0, math.pi/2))
    # warm window glow lights across the courtyard
    for (x, y, z) in ((-6.6, 22, 6), (6.6, 25, 8), (-6.6, 29, 9), (6.6, 17, 5)):
        light('AREA', 'cw', (x*0.9, y, z), 700, (1.0, 0.65, 0.3), size=1.5, rot=(math.radians(90), 0, math.radians(90 if x < 0 else -90)))

# ---------------------------------------------------------------- the window building with the open window + room
def build_room():
    yF, yB = 32.0, 38.0
    wx0, wx1, wz0, wz1 = -0.65, 0.75, 6.9, 8.7     # entry window
    ex0, ex1 = -0.4, 1.2                            # exit window (same z)
    H = 16.0
    fm = M['facade']
    def wall(name, y, thick, holes_x, mat):
        x0, x1 = holes_x
        box(name+'L', ((-30+x0)/2, y, H/2), (x0+30, thick, H), mat)
        box(name+'R', ((x1+30)/2, y, H/2), (30-x1, thick, H), mat)
        box(name+'lo', ((x0+x1)/2, y, wz0/2), (x1-x0, thick, wz0), mat)
        box(name+'hi', ((x0+x1)/2, y, (wz1+H)/2), (x1-x0, thick, H-wz1), mat)
    wall('Bfront', yF+0.15, 0.3, (wx0, wx1), fm)
    wall('Bback', yB+0.15, 0.3, (ex0, ex1), fm)
    # solid masses beside/above/below the room
    box('Bmass_L', (-16.5, 35.15, H/2), (27, 5.7, H), M['concrete']); box('Bmass_R', (17.3, 35.15, H/2), (27.4, 5.7, H), M['concrete'])
    box('Bfloor', (0.3, 35.15, 3.2), (6.6, 5.7, 6.4), M['concrete']); box('Bceil', (0.3, 35.15, (9.4+H)/2), (6.6, 5.7, H-9.4), M['plaster'])
    for k, (x0, x1) in enumerate(((-40, -30), (30, 40))): box(f'Bside{k}', ((x0+x1)/2, 35.15, H/2), (10, 6.3, H), fm)
    # window reveal frames + sill + open shutters
    fr = M['frame2']
    for (x0, x1, y, nm) in ((wx0, wx1, yF, 'in'), (ex0, ex1, yB+0.3, 'out')):
        box(f'fr_T{nm}', ((x0+x1)/2, y-0.05 if nm == 'in' else y+0.05, wz1+0.06), (x1-x0+0.2, 0.14, 0.12), fr)
        box(f'fr_B{nm}', ((x0+x1)/2, y-0.15 if nm == 'in' else y+0.15, wz0-0.05), (x1-x0+0.3, 0.36, 0.1), M['concrete'])
        box(f'fr_L{nm}', (x0-0.06, y-0.05 if nm == 'in' else y+0.05, (wz0+wz1)/2), (0.12, 0.14, wz1-wz0+0.2), fr)
        box(f'fr_R{nm}', (x1+0.06, y-0.05 if nm == 'in' else y+0.05, (wz0+wz1)/2), (0.12, 0.14, wz1-wz0+0.2), fr)
    # shutters thrown open against the facade (entry side)
    sh1 = box('shutterL_in', (wx0-0.03, yF-0.32, (wz0+wz1)/2), (0.04, 0.68, wz1-wz0), fr, rot=(0, 0, math.radians(-20)))
    sh2 = box('shutterR_in', (wx1+0.03, yF-0.32, (wz0+wz1)/2), (0.04, 0.68, wz1-wz0), fr, rot=(0, 0, math.radians(20)))
    sh1.location.x = wx0-0.32; sh2.location.x = wx1+0.32
    # flower pots on the sill
    for x in (-0.45, 0.35):
        cyl('pot', (x, yF-0.18, wz0+0.09), 0.09, 0.16, M['rust'], seg=12); sphere('plant', (x, yF-0.18, wz0+0.28), 0.14, simple('leaf', (0.08, 0.2, 0.06), 0.7), seg=10, scale=(1, 1, 0.8))
    # balcony slab below the window
    box('balc', (0.05, yF-0.45, wz0-0.25), (2.2, 0.9, 0.12), M['concrete'], bevel=0.01)
    for x in np.linspace(-1.0, 1.1, 8): cyl('rail', (x, yF-0.85, wz0+0.25), 0.012, 0.9, M['black'], seg=6)
    box('railtop', (0.05, yF-0.85, wz0+0.7), (2.2, 0.04, 0.04), M['black'])
    # ---------------- room interior (warm tungsten)
    wallm = M['plaster']; rx0, rx1 = -3.0, 3.6; fz = 6.4
    box('room_wL', (rx0-0.05, 35.15, (fz+9.4)/2), (0.1, 5.7, 3.0), wallm); box('room_wR', (rx1+0.05, 35.15, (fz+9.4)/2), (0.1, 5.7, 3.0), wallm)
    box('roomfloor', (0.3, 35.15, fz+0.004), (6.6, 5.7, 0.008), pbr('roomwood', 'worn_planks', tile=1.0, dirt=0.6, streak=0.2))
    box('rug', (0.4, 35.2, fz+0.012), (3.0, 3.6, 0.02), pbr('rugA', 'fabric_pattern_07', tile=0.9, tint=(0.55, 0.12, 0.10, 1), tint_amt=0.85, dirt=0.4))
    box('rug2', (0.4, 35.2, fz+0.02), (2.4, 3.0, 0.02), pbr('rugB', 'fabric_pattern_07', tile=0.6, tint=(0.75, 0.55, 0.3, 1), tint_amt=0.7, dirt=0.4))
    box('roomskirt', (0.3, 32.36, fz+0.08), (6.6, 0.04, 0.16), M['wood'])
    # table with tea glasses and bread
    tz = fz+0.75
    box('table', (-1.5, 35.4, tz-0.03), (1.0, 1.6, 0.06), M['wood'], bevel=0.01)
    for dx, dy in ((-.45, -.75), (.45, -.75), (-.45, .75), (.45, .75)): box('tleg', (-1.5+dx, 35.4+dy, fz+0.37), (0.06, 0.06, 0.72), M['wood'])
    glass = simple('teaglass', (0.9, 0.85, 0.7), 0.05, extra={'Transmission Weight': 0.9, 'IOR': 1.45})
    for k, (dx, dy) in enumerate(((0.1, -0.4), (-0.2, 0.0), (0.15, 0.45))):
        cyl(f'tg{k}', (-1.5+dx, 35.4+dy, tz+0.05), 0.033, 0.09, glass, seg=16, r2=0.04)
        cyl(f'tea{k}', (-1.5+dx, 35.4+dy, tz+0.035), 0.030, 0.06, simple('tea', (0.35, 0.09, 0.02), 0.2), seg=16)
    cyl('plate', (-1.6, 35.9, tz+0.01), 0.16, 0.02, simple('plate', (0.85, 0.82, 0.75), 0.3), seg=24)
    sphere('bread', (-1.6, 35.9, tz+0.06), 0.09, simple('bread', (0.55, 0.36, 0.16), 0.9), scale=(1.2, 0.8, 0.6))
    # chairs, sofa, shelf with books, pictures, radio
    for k, (x, y) in enumerate(((-2.4, 34.9), (-2.4, 36.1))):
        box(f'chair{k}', (x, y, fz+0.45), (0.45, 0.45, 0.06), M['wood']); box(f'chairb{k}', (x-0.2, y, fz+0.8), (0.06, 0.45, 0.7), M['wood'])
        for dx, dy in ((-.18, -.18), (.18, -.18), (-.18, .18), (.18, .18)): box('cleg', (x+dx, y+dy, fz+0.22), (0.04, 0.04, 0.44), M['wood'])
    sofa = simple('sofa', (0.18, 0.28, 0.24), 0.95, extra={'Sheen Weight': 0.5})
    box('sofa_seat', (2.9, 35.2, fz+0.25), (0.9, 2.2, 0.5), sofa, bevel=0.08); box('sofa_back', (3.3, 35.2, fz+0.65), (0.2, 2.2, 0.7), sofa, bevel=0.06)
    box('shelf', (3.45, 33.3, fz+1.0), (0.3, 1.2, 2.0), M['wood'])
    for k in range(5):
        for j in range(9):
            box(f'book{k}{j}', (3.42, 32.8+j*0.11, fz+0.5+k*0.36), (0.22, 0.07, 0.26), simple(f'bk{(k*9+j)%7}', [(0.5, 0.1, 0.1), (0.1, 0.2, 0.4), (0.7, 0.6, 0.3), (0.15, 0.3, 0.15), (0.6, 0.6, 0.55), (0.3, 0.1, 0.3), (0.05, 0.05, 0.05)][(k*9+j) % 7], 0.7))
    for k, (y, z, w, h) in enumerate(((33.6, fz+1.9, 0.5, 0.7), (36.5, fz+1.7, 0.7, 0.5))):
        box(f'pic{k}', (rx0+0.06, y, z), (0.04, w, h), M['frame2']); box(f'picin{k}', (rx0+0.09, y, z), (0.02, w*0.85, h*0.85), simple(f'pc{k}', [(0.6, 0.5, 0.3), (0.3, 0.45, 0.55)][k], 0.8))
    box('radio', (-2.75, 36.6, fz+0.4), (0.25, 0.35, 0.2), M['black']); box('sidetbl', (-2.75, 36.6, fz+0.2), (0.4, 0.5, 0.4), M['wood'])
    sphere('radio_dial', (-2.61, 36.6, fz+0.42), 0.03, emission('dial', (1, .7, .3), 20), seg=8)
    # pendant lamp swinging (near-miss #2 inside the room)
    lampP = P(110.0)
    sw = bpy.data.objects.new('pend_swing', None); sc.collection.objects.link(sw); sw.location = (lampP.x+0.7, 34.9, 9.4)
    cy_ = cyl('pend_cable', (0, 0, -0.35), 0.005, 0.7, M['black'], seg=6); cy_.parent = sw
    sh = cyl('pend_shade', (0, 0, -0.78), 0.25, 0.2, simple('pendshade', (0.7, 0.55, 0.3), 0.6, extra={'Emission Strength': 0}), seg=24, r2=0.06); sh.parent = sw
    bu = sphere('pend_bulb', (0, 0, -0.82), 0.06, emission('pendbulb', (1.0, 0.7, 0.35), 150), seg=12); bu.parent = sw
    pl = light('POINT', 'pend_light', (0, 0, -0.85), 900, (1.0, 0.68, 0.34), size=0.1); pl.parent = sw
    for f, a in ((100, 0), (109, 0), (111, 14), (114, -10), (118, 7), (123, -4), (130, 2), (191, 0)):
        sw.rotation_euler = (math.radians(a*0.4), math.radians(a), 0); sw.keyframe_insert('rotation_euler', frame=int(T(f)))
    light('AREA', 'room_win', (-0.2, 33.0, 8.5), 250, (1.0, 0.7, 0.4), size=1.2, rot=(math.radians(90), 0, 0))
    light('POINT', 'room_lamp2', (2.6, 33.5, 8.3), 250, (1.0, 0.65, 0.3), size=0.15)
    # curtains at the entry window: the left panel is thrown aside by the wind of the can
    cur_mat = simple('curtain', (0.75, 0.66, 0.5), 0.9, extra={'Sheen Weight': 0.8, 'Alpha': 1.0})
    for k, (cx, sgn) in enumerate(((wx0+0.15, 1), (wx1-0.15, -1))):
        c = grid_plane(f'curtain{k}', (0.7, 1.9), 10, 22, cur_mat, center=(cx, yF+0.2, (wz0+wz1)/2+0.05), rot=(math.pi/2, 0, 0))
        wv = c.modifiers.new('wave', 'WAVE'); wv.height = 0.05; wv.width = 0.25; wv.narrowness = 2.5; wv.speed = 0.12; wv.start_position_object = None
        for f, ang in ((100, 0), (106, 0), (108, 38*sgn), (111, 55*sgn), (114, 30*sgn), (120, 15*sgn), (140, 8*sgn)):
            pass
        # billow: bend with a simple rotation about the top edge
        piv = bpy.data.objects.new(f'curpiv{k}', None); sc.collection.objects.link(piv); piv.location = (cx, yF+0.2, wz1+0.02)
        c.parent = piv; c.location = (0, 0, -(wz1-wz0)/2+0.03)
        for f, a in ((100, 0), (106, 0), (108, -35), (110, -55), (113, -30), (118, -15), (130, -8), (191, -6)):
            piv.rotation_euler = (math.radians(a), 0, math.radians(sgn*(a*-0.25))); piv.keyframe_insert('rotation_euler', frame=int(T(f)))

# ---------------------------------------------------------------- market street (y 38.3 .. 110)
def build_market():
    y0, y1 = 38.3, 112
    box('mk_ground', (0, (y0+y1)/2, -0.5), (16, y1-y0, 1.0), M['cobble'])
    box('mk_ground_far', (0, (y0+y1)/2, -0.55), (120, y1-y0, 1.0), M['asphalt'])
    # buildings both sides
    for side, x0, x1 in (('L', -60, -7.5), ('R', 7.5, 60)):
        y = y0
        while y < y1:
            d = random.uniform(6, 11); top = random.uniform(13, 21)
            t = bld(f'mk{side}{int(y)}', x0, x1, y, y+d, top, clear=False)
            roof_props(x0, x1, y, y+d, t, 2)
            # shopfront: dark opening + shutter + sign + balconies
            xs = x0 if side == 'R' else x1; sg = 1 if side == 'R' else -1
            xf = (7.5 if side == 'R' else -7.5)
            box(f'shopdark{side}{int(y)}', (xf-sg*0.02, y+d/2, 1.5), (0.06, d*0.7, 3.0), simple('shopdark', (0.02, 0.018, 0.02), 0.6))
            box(f'shoplit{side}{int(y)}', (xf-sg*0.04, y+d/2, 1.4), (0.03, d*0.6, 2.4), M['warm_lo'])
            box(f'signbar{side}{int(y)}', (xf-sg*0.15, y+d/2, 3.35), (0.15, d*0.7, 0.55), simple(f'sign{int(y)}{side}', random.choice([(0.5, 0.1, 0.08), (0.08, 0.3, 0.25), (0.75, 0.6, 0.15), (0.1, 0.15, 0.4)]), 0.6, emit=(0.3, 0.25, 0.2), estr=0.6))
            for z in (6.0, 9.0, 12.0):
                for j in range(2):
                    yy = y+d*(0.25+0.5*j)
                    box(f'balc{side}{int(y)}{z}{j}', (xf-sg*0.5, yy, z), (1.0, 1.6, 0.12), M['concrete'])
                    box(f'balcr{side}{int(y)}{z}{j}', (xf-sg*0.98, yy, z+0.5), (0.04, 1.6, 1.0), M['black'])
                    box(f'balwin{side}{int(y)}{z}{j}', (xf-sg*0.03, yy, z+1.0), (0.05, 0.9, 1.7), M['warm_lo'] if random.random() < 0.4 else M['glass_dark'])
            y += d
    # stalls
    fruit_cols = [(0.85, 0.35, 0.05), (0.7, 0.05, 0.04), (0.5, 0.65, 0.1), (0.9, 0.75, 0.1), (0.35, 0.1, 0.35)]
    aw_cols = [(0.7, 0.12, 0.1), (0.1, 0.32, 0.5), (0.85, 0.65, 0.15), (0.15, 0.45, 0.25), (0.85, 0.85, 0.8), (0.55, 0.2, 0.45)]
    n = 0
    for side in (-1, 1):
        y = y0+3
        while y < y1-4:
            x = side*4.6; w, dpt = 3.2, 2.6
            box(f'stt{n}', (x, y, 0.85), (dpt, w, 0.06), M['wood'], bevel=0.01)
            box(f'stb{n}', (x, y, 0.4), (dpt-0.2, w-0.2, 0.8), M['wood'])
            for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                cyl(f'stp{n}', (x+dx*dpt/2, y+dy*w/2, 1.5), 0.03, 3.0, M['rust'], seg=6)
            # canopy (sloping, striped), lit from beneath
            cc = random.choice(aw_cols); tilt = 0.18
            aw = box(f'aw{n}', (x, y, 3.05), (dpt+0.6, w+0.5, 0.03), simple(f'aw{n}', cc, 0.85, extra={'Sheen Weight': 0.5}), rot=(tilt*side*0, tilt*side, 0))
            # produce piles
            bm = bmesh.new(); pc = random.choice(fruit_cols)
            for i in range(90):
                px = random.uniform(-dpt/2+0.2, dpt/2-0.2); py = random.uniform(-w/2+0.2, w/2-0.2)
                pz = 0.9+0.06*random.random()+0.04*math.cos(px*3)
                rad = random.uniform(0.045, 0.06)
                bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=rad, matrix=Matrix.Translation((px, py, pz)))
            ob = _mesh_obj(f'produce{n}', bm, simple(f'fruit{n%5}', fruit_cols[n % 5], 0.35)); ob.location = (x, y, 0)
            for p_ in ob.data.polygons: p_.use_smooth = True
            # hanging bulb + light
            sphere(f'sb{n}', (x-side*0.8, y, 2.85), 0.06, emission('stbulb', (1, .72, .4), 60), seg=8)
            if n % 3 == 0: light('POINT', f'stl{n}', (x-side*0.8, y, 2.7), 250, (1.0, 0.68, 0.35), size=0.08)
            n += 1
            y += w+random.uniform(0.6, 1.6)
    # string lights across the street + hanging lanterns near the flight path
    bulbm = emission('strbulb', (1.0, 0.78, 0.45), 25)
    for k, y in enumerate(np.arange(y0+4, y1-2, 5.5)):
        z0 = 6.2+random.uniform(-.4, .4)
        pts = [(-7.2+t*14.4, y, z0-1.0*math.sin(math.pi*t)) for t in np.linspace(0, 1, 18)]
        crv = bpy.data.curves.new('strl', 'CURVE'); crv.dimensions = '3D'; crv.bevel_depth = 0.008
        sp = crv.splines.new('POLY'); sp.points.add(len(pts)-1)
        for p, q in zip(sp.points, pts): p.co = (*q, 1)
        co = bpy.data.objects.new('strl', crv); co.data.materials.append(M['black']); sc.collection.objects.link(co)
        for i, q in enumerate(pts[1:-1:1]):
            sphere('sbulb', (q[0], q[1], q[2]-0.09), 0.055, bulbm, seg=8)
    lantern = emission('lantern', (1.0, 0.38, 0.1), 6)
    for fr_, dx, dz in ((114.5, 0.75, 0.3), (117.0, -0.7, 0.4), (120.5, 0.6, 0.45), (123.5, -0.65, 0.3), (127.0, 0.7, 0.4), (131.0, -0.6, 0.35)):
        p = P(fr_); top = p.z+dz+1.2
        crv = bpy.data.curves.new('lc', 'CURVE'); crv.dimensions = '3D'; crv.bevel_depth = 0.005
        sp = crv.splines.new('POLY'); sp.points.add(1); sp.points[0].co = (p.x+dx, p.y, 6.4, 1); sp.points[1].co = (p.x+dx, p.y, p.z+dz+0.25, 1)
        co = bpy.data.objects.new('lc', crv); co.data.materials.append(M['black']); sc.collection.objects.link(co)
        lan = sphere('lantern', (p.x+dx, p.y, p.z+dz), 0.16, lantern, seg=14, scale=(1, 1, 1.25))
        light('POINT', 'lantern_l', (p.x+dx, p.y, p.z+dz), 500, (1.0, 0.5, 0.2), size=0.12)
    # bunting triangles
    for k, y in enumerate(np.arange(y0+6, y1-6, 11)):
        for i in range(14):
            t = i/13; x = -7.2+t*14.4
            tri = bmesh.new(); vs = [tri.verts.new(v) for v in ((-0.12, 0, 0), (0.12, 0, 0), (0, 0, -0.28))]; tri.faces.new(vs)
            z = 5.4-0.8*math.sin(math.pi*t)
            o = _mesh_obj('flag', tri, simple(f'flag{i%4}', aw_cols[i % 4], 0.9)); o.location = (x, y+0.0, z)
            wv = o.modifiers.new('w', 'WAVE'); wv.height = 0.03; wv.speed = 0.2; wv.time_offset = random.uniform(0, 30)
    # hanging carpets/laundry on the shop fronts, crowd
    for k in range(10):
        side = random.choice((-1, 1)); y = random.uniform(y0+5, y1-5)
        cloth(f'carpet{k}', (side*7.4, y, 5.6), (1.4, 2.0), random.choice([(0.5, 0.1, 0.08), (0.12, 0.3, 0.4), (0.7, 0.5, 0.2)]), wave=0.03, rot=(math.pi/2, 0, math.pi/2))
    ppl = simple('cloth_p', (0.03, 0.03, 0.035), 0.9)
    for k in range(46):
        side = random.choice((-1, 1)); x = side*random.uniform(2.6, 6.0); y = random.uniform(y0+2, y1-3)
        if abs(x) < 1.3: continue
        h = random.uniform(1.55, 1.8); col = random.choice([(0.03, 0.03, 0.035), (0.08, 0.05, 0.04), (0.04, 0.06, 0.08), (0.12, 0.04, 0.04), (0.1, 0.1, 0.09)])
        mat = simple(f'ppl{k%6}', col, 0.9)
        cyl(f'body{k}', (x, y, h*0.5), 0.16, h*0.75, mat, seg=10, r2=0.13)
        sphere(f'head{k}', (x, y, h-0.11), 0.10, simple('skin_p', (0.25, 0.15, 0.1), 0.6), seg=10)
        cyl(f'legs{k}', (x, y, 0.4), 0.11, 0.8, mat, seg=8, r2=0.13)

# ---------------------------------------------------------------- city between market and stadium
def build_city():
    box('city_ground', (0, 138, -1.3), (1200, 120, 2.0), simple('cityground', (0.03, 0.03, 0.035), 0.8))
    # street grid glowing sodium orange (from above these read as lit streets)
    lit = emission('street', (1.0, 0.5, 0.15), 3.0)
    for k in range(-6, 7):
        if k == 0: continue
        box(f'stX{k}', (k*40+random.uniform(-4, 4), 140, 0.05), (2.2, 58, 0.05), lit)
    for k in range(0, 8):
        box(f'stY{k}', (0, 113+k*8, 0.05), (600, 1.8, 0.05), lit)
    for i in range(210):
        x = random.uniform(-260, 260); y = random.uniform(100, 175)
        if abs(x) < 9 and y < 118: continue
        w = random.uniform(8, 22); d = random.uniform(8, 22)
        top = random.uniform(9, 42)*(1.0 if abs(x) > 60 else 0.8)
        x0, x1, y0, y1 = x-w/2, x+w/2, y-d/2, y+d/2
        top = keep_clear(x0, x1, y0, y1, top, margin=6.0)
        t = bld(f'city{i}', x0, x1, y0, y1, top, clear=False)
        if random.random() < 0.5: roof_props(x0, x1, y0, y1, t, 1)
    # a few red aircraft-warning beacons on the tallest roofs
    for i in range(8):
        x = random.uniform(-200, 200); y = random.uniform(150, 175)
        cyl('mast', (x, y, 55), 0.3, 20, M['black'], seg=6)
        sphere('beacon', (x, y, 65.5), 0.5, emission('beacon', (1, 0.05, 0.03), 300), seg=8)

# ---------------------------------------------------------------- stadium
def superellipse(a, b, n, cy, N=160):
    pts = []
    for i in range(N):
        t = 2*math.pi*i/N; c, s = math.cos(t), math.sin(t)
        pts.append((a*math.copysign(abs(c)**(2/n), c), cy+b*math.copysign(abs(s)**(2/n), s)))
    return pts

def build_stadium():
    cy = 257.5; n = 3.4
    inner = superellipse(44, 60, n, cy); outer = superellipse(80, 96, n, cy)
    N = len(inner); R = 14
    # crowd material (emissive lit mass + shadowed seats)
    cm = bpy.data.materials.new('crowd'); cm.use_nodes = True; nt = cm.node_tree; nt.nodes.clear()
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = bpy.data.images.load(TEX+'crowd.png'); tex.extension = 'REPEAT'; tex.interpolation = 'Linear'
    uv = nt.nodes.new('ShaderNodeUVMap'); nt.links.new(uv.outputs[0], tex.inputs[0])
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs[1].default_value = 2.2
    _CROWD_EM = em
    nt.links.new(tex.outputs[0], em.inputs[0])
    df = nt.nodes.new('ShaderNodeBsdfDiffuse'); nt.links.new(tex.outputs[0], df.inputs[0])
    mx = nt.nodes.new('ShaderNodeMixShader'); mx.inputs[0].default_value = 0.6
    nt.links.new(df.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
    o = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(mx.outputs[0], o.inputs[0])
    M['crowd'] = cm
    def loft(name, rings, mat, uvscale=(1/200, 1/50), closed=True):
        bm = bmesh.new(); vs = [[bm.verts.new(p) for p in ring] for ring in rings]
        uvl = bm.loops.layers.uv.new('UV')
        s = [0.0]
        for i in range(1, N+1):
            p0 = inner[(i-1) % N]; p1 = inner[i % N]; s.append(s[-1]+math.hypot(p1[0]-p0[0], p1[1]-p0[1]))
        for r in range(len(rings)-1):
            for i in range(N):
                i2 = (i+1) % N
                f = bm.faces.new((vs[r][i], vs[r][i2], vs[r+1][i2], vs[r+1][i])); f.smooth = False
                for lp, (ii, rr) in zip(f.loops, ((i, r), (i+1, r), (i+1, r+1), (i, r+1))):
                    lp[uvl].uv = (s[ii]*uvscale[0], rr*uvscale[1]*14)
        return _mesh_obj(name, bm, mat)
    # stands: stepped bowl profile
    rings = []
    for r in range(R+1):
        t = r/R; k = 0.08+0.92*t
        z = 2.0+24.0*(t**1.25)
        ring = [(inner[i][0]+(outer[i][0]-inner[i][0])*t, inner[i][1]+(outer[i][1]-inner[i][1])*t, z) for i in range(N)]
        rings.append(ring)
    loft('stands', rings, M['crowd'])
    # front wall / advertising boards (emissive)
    boards = bpy.data.materials.new('boards'); boards.use_nodes = True; nt_ = boards.node_tree; nt_.nodes.clear()
    ti = nt_.nodes.new('ShaderNodeTexImage'); ti.image = bpy.data.images.load(TEX+'adboards.png'); ti.extension = 'REPEAT'
    uvn = nt_.nodes.new('ShaderNodeUVMap'); nt_.links.new(uvn.outputs[0], ti.inputs[0])
    em_ = nt_.nodes.new('ShaderNodeEmission'); em_.inputs[1].default_value = 2.2; nt_.links.new(ti.outputs[0], em_.inputs[0])
    oo = nt_.nodes.new('ShaderNodeOutputMaterial'); nt_.links.new(em_.outputs[0], oo.inputs[0])
    ring_lo = [(p[0], p[1], 0.0) for p in inner]; ring_hi = [(p[0], p[1], 1.0) for p in inner]
    loft('boardwall', [ring_lo, ring_hi], boards, uvscale=(-1/32, 1/14))
    # roof canopy over the upper stands
    roof_rings = []
    for t, dz in ((0.52, 0.0), (0.75, 0.6), (1.0, 1.4)):
        z = 2.0+24.0*(t**1.25)+8.0+dz
        roof_rings.append([(inner[i][0]+(outer[i][0]-inner[i][0])*t*1.02, inner[i][1]+(outer[i][1]-inner[i][1])*t*1.02, z) for i in range(N)])
    loft('roof', roof_rings, simple('roofmat', (0.22, 0.23, 0.25), 0.55, metal=0.15), uvscale=(1/40, 1))
    # LED lighting strip under the roof leading edge
    strip = [(inner[i][0]+(outer[i][0]-inner[i][0])*0.53, inner[i][1]+(outer[i][1]-inner[i][1])*0.53, 2.0+24.0*(0.53**1.25)+7.6) for i in range(N)]
    strip2 = [(p[0]*0.995+0, (p[1]-cy)*0.995+cy, p[2]-0.3) for p in strip]
    loft('ledstrip', [strip, strip2], emission('led', (0.9, 0.95, 1.0), 30), uvscale=(1/40, 1))
    # outer facade
    fac = [[(outer[i][0], outer[i][1], 0.0) for i in range(N)], [(outer[i][0], outer[i][1], 27.0) for i in range(N)]]
    fm = loft('facade_out', fac, M['facade'], uvscale=(1/40, 1/28))
    # pitch
    pm = bpy.data.materials.new('pitch'); pm.use_nodes = True; nt = pm.node_tree; bs = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.35, 0.35, 0.35)
    nt.links.new(tc.outputs['Object'], mp.inputs[0])
    g = nt.nodes.new('ShaderNodeTexImage'); g.image = bpy.data.images.load(TEX+'grass_path_2_diff_1k.jpg'); nt.links.new(mp.outputs[0], g.inputs[0])
    wv = nt.nodes.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'Y'; wv.inputs['Scale'].default_value = 0.34; wv.inputs['Distortion'].default_value = 0.0
    nt.links.new(tc.outputs['Object'], wv.inputs[0])
    sq = nt.nodes.new('ShaderNodeMath'); sq.operation = 'GREATER_THAN'; sq.inputs[1].default_value = 0.5; nt.links.new(wv.outputs['Fac'], sq.inputs[0])
    tint = mix(nt, g.outputs[0], (0.30, 0.85, 0.22, 1), sq.outputs[0], 'MULTIPLY')
    tint2 = mix(nt, tint, (0.9, 1.15, 0.9, 1), 0.0)
    tint = mix(nt, tint, (0.55, 0.95, 0.35, 1), 1.0, 'MULTIPLY'); nt.links.new(tint, bs.inputs['Base Color']); bs.inputs['Roughness'].default_value = 0.85
    pitch = box('pitch', (0, cy, -0.05), (68, 105, 0.1), pm)
    pitch.data.polygons  # object-space stripes across the length
    box('pitch_run', (0, cy, -0.1), (2*44, 2*60, 0.08), pm)
    wl = emission('line', (0.9, 0.9, 0.85), 0.9)
    def line(x0, y0_, x1, y1_, w=0.12):
        cxm, cym = (x0+x1)/2, (y0_+y1_)/2; L = math.hypot(x1-x0, y1_-y0_)
        box('ln', (cxm, cym, 0.012), (max(w, abs(x1-x0)), max(w, abs(y1_-y0_)), 0.01), wl)
    ya, yb = cy-52.5, cy+52.5
    for (xa, ya_, xb, yb_) in ((-34, ya, 34, ya), (-34, yb, 34, yb), (-34, ya, -34, yb), (34, ya, 34, yb), (-34, cy, 34, cy),
                               (-20.2, ya, -20.2, ya+16.5), (20.2, ya, 20.2, ya+16.5), (-20.2, ya+16.5, 20.2, ya+16.5),
                               (-20.2, yb, -20.2, yb-16.5), (20.2, yb, 20.2, yb-16.5), (-20.2, yb-16.5, 20.2, yb-16.5),
                               (-9.16, yb, -9.16, yb-5.5), (9.16, yb, 9.16, yb-5.5), (-9.16, yb-5.5, 9.16, yb-5.5)):
        line(xa, ya_, xb, yb_)
    bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=False, segments=64, radius=9.15+0.06)
    bmesh.ops.create_circle(bm, cap_ends=False, segments=64, radius=9.15-0.06)
    ring = bpy.data.objects  # centre circle via cylinder trick
    c1 = cyl('cc_outer', (0, cy, 0.011), 9.2, 0.01, wl, seg=64); c2 = cyl('cc_inner', (0, cy, 0.0125), 9.08, 0.01, pm, seg=64)
    # goals: the far one is the target (+Y end), posts on the goal line y = yb
    goalw = simple('goalpost', (0.92, 0.92, 0.9), 0.35)
    gx = 3.66; gy = yb
    box('post_L', (-gx, gy, 1.22), (0.12, 0.12, 2.44), goalw); box('post_R', (gx, gy, 1.22), (0.12, 0.12, 2.44), goalw)
    cbar = box('crossbar', (0, gy, 2.44), (2*gx+0.12, 0.12, 0.12), goalw)
    for f_, dz_ in ((605, 0.0), (607, -0.035), (609, 0.03), (611, -0.02), (613, 0.012), (616, -0.006), (620, 0.0)):   # bar rings when the can hits it (f606)
        cbar.location = (0, gy, 2.44+dz_); cbar.keyframe_insert('location', frame=f_)
    set_interp(cbar, 'LINEAR')
    for s in (-1, 1):
        cyl(f'stay{s}', (s*gx, gy+0.9, 1.25), 0.025, 2.9, goalw, seg=8, rot=(math.radians(-25), 0, 0))
        box(f'base{s}', (s*gx, gy+1.0, 0.03), (0.06, 2.0, 0.06), goalw)
    box('back_top', (0, gy+0.85, 2.44), (2*gx, 0.05, 0.05), goalw)
    netm = simple('net', (0.85, 0.85, 0.85), 0.9)
    # back net (with bulge shape key) - top edge (y=gy+0.8, z=2.44) to bottom (gy+2.0, 0)
    NX, NZ = 61, 20
    bm = bmesh.new(); grid = []
    for j in range(NZ+1):
        row = []
        for i in range(NX+1):
            x = -gx+2*gx*i/NX; t = j/NZ; z = 2.44*(1-t); y = gy+0.80+1.20*t
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(NZ):
        for i in range(NX): bm.faces.new((grid[j][i], grid[j][i+1], grid[j+1][i+1], grid[j+1][i]))
    me = bpy.data.meshes.new('netback'); bm.to_mesh(me); bm.free()
    net = bpy.data.objects.new('netback', me); sc.collection.objects.link(net); net.data.materials.append(netm)
    net.shape_key_add(name='Basis'); sk = net.shape_key_add(name='bulge')
    cx_, cz_ = POCKET_X, POCKET_Z          # v2: the pocket where the can ends up (ending B)
    for k, v in enumerate(me.vertices):
        d = math.hypot(v.co.x-cx_, (v.co.z-cz_)*1.0)
        amp = 0.95*math.exp(-(d/1.0)**2)
        sk.data[k].co = Vector((v.co.x-0.12*(v.co.x-cx_)*math.exp(-(d/1.0)**2), v.co.y+amp, v.co.z))
    for f, val in BULGE_KEYS:
        sk.value = val; sk.keyframe_insert('value', frame=int(round(f)))
    set_interp(net.data.shape_keys if False else net, 'LINEAR')
    wf = net.modifiers.new('wire', 'WIREFRAME'); wf.thickness = 0.014; wf.use_even_offset = False
    # side + top nets (static)
    for s in (-1, 1):
        bmz = bmesh.new()
        A = bmz.verts.new((s*gx, gy, 2.44)); B = bmz.verts.new((s*gx, gy+0.80, 2.44)); Cc = bmz.verts.new((s*gx, gy+2.0, 0.0)); D = bmz.verts.new((s*gx, gy, 0.0))
        bmz.faces.new((A, B, Cc, D))
        ob = _mesh_obj(f'netside{s}', bmz, netm); sub = ob.modifiers.new('sub', 'SUBSURF'); sub.subdivision_type = 'SIMPLE'; sub.levels = 5; sub.render_levels = 5
        w2 = ob.modifiers.new('wire', 'WIREFRAME'); w2.thickness = 0.012
    bmt = bmesh.new(); A = bmt.verts.new((-gx, gy, 2.44)); B = bmt.verts.new((gx, gy, 2.44)); Cc = bmt.verts.new((gx, gy+0.8, 2.44)); D = bmt.verts.new((-gx, gy+0.8, 2.44)); bmt.faces.new((A, B, Cc, D))
    ob = _mesh_obj('nettop', bmt, netm); sub = ob.modifiers.new('sub', 'SUBSURF'); sub.subdivision_type = 'SIMPLE'; sub.levels = 5; sub.render_levels = 5
    w3 = ob.modifiers.new('wire', 'WIREFRAME'); w3.thickness = 0.012
    # near goal (behind camera path, just a frame)
    box('gpost2L', (-gx, ya, 1.22), (0.12, 0.12, 2.44), goalw); box('gpost2R', (gx, ya, 1.22), (0.12, 0.12, 2.44), goalw); box('gbar2', (0, ya, 2.44), (2*gx+0.12, 0.12, 0.12), goalw)
    # floodlight towers at the four corners
    fl = emission('flood', (1.0, 0.96, 0.88), 900)
    for (tx, ty) in ((-72, 192), (72, 192), (-40, 349), (40, 349)):
        cyl(f'tower{tx}{ty}', (tx, ty, 26), 0.9, 52, M['concrete'], seg=10, r2=0.5)
        box(f'trus{tx}{ty}', (tx, ty, 54.5), (11, 1.2, 7.5), M['black'])
        for r_ in range(4):
            for c_ in range(8):
                px = tx+(c_-3.5)*1.3; pz = 52.3+r_*1.9
                d = Vector((0-px, cy-ty, 0-pz)).normalized()
                pnl = box('lamp', (px, ty+(-1.0 if ty > cy else 1.0), pz), (1.05, 0.12, 1.4), fl)
                pnl.rotation_euler = (math.radians(0), 0, 0)
        lgt = light('SPOT', f'flood{tx}{ty}', (tx, ty, 53), 1.6e6, (1.0, 0.95, 0.86), size=3, spot=34)
        aim(lgt, (tx*0.1, cy, 0))
    # haze volume over the stadium (visible beams, glow)
    hz = box('haze', (0, cy, 40), (230, 240, 90), simple('hz', (1, 1, 1), 1), )
    hzm = bpy.data.materials.new('haze'); hzm.use_nodes = True; nt = hzm.node_tree; nt.nodes.clear()
    vsc = nt.nodes.new('ShaderNodeVolumeScatter'); vsc.inputs['Density'].default_value = 0.0014; vsc.inputs['Anisotropy'].default_value = 0.55
    vsc.inputs['Color'].default_value = (0.85, 0.9, 1.0, 1)
    o = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(vsc.outputs[0], o.inputs['Volume'])
    hz.data.materials.clear(); hz.data.materials.append(hzm); hz.display_type = 'WIRE'
    # ball-boys / players? a few tiny dark figures at the sidelines & photographers behind the goal
    for k in range(9):
        x = random.uniform(-14, 14); y = yb+random.uniform(4, 6.5)
        cyl(f'ph{k}', (x, y, 0.8), 0.22, 1.6, simple('phc', (0.04, 0.04, 0.05), 0.9), seg=8)
        sphere(f'phh{k}', (x, y, 1.7), 0.11, simple('skin_p', (0.25, 0.15, 0.1), 0.6), seg=8)

build_courtyard(); build_room()
if PART != 'stadium':
    build_market(); build_city()
build_stadium()
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'v2_far.py')).read())   # v2 additions (murals, kids, pigeons, keeper, confetti)
