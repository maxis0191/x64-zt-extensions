"""EXACT CHANGE: a fare box rebuilt into a lever-action carbine (Blender 4.5 generator, headless, deterministic).

    blender -b --factory-startup -P exact_change_gun.py -- --params <params.json> --out <work dir>

params.json (written by build_authored_weapon.py from the recipe's "generator_params"): bone names of the donor
view model (keys body, lever, hammer, trigger, mag1, mag2, shells[5], loose[2]), the shell bone x positions,
atlas sizes, camo density, colours. Everything is modelled in the donor view model's space (inches, x forward,
y left, z up) so the donor's hands and animations fit: stock / wrist / lever loop / fore-end where the donor's are.
Output: see authored_blender.finish.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authored_blender as ab  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402


def srgb(h):
    """'#RRGGBB' -> linear tuple."""
    c = [int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


# ------------------------------------------------------------------ looks
def enamel(P):
    green, steel = srgb(P["enamel"]), srgb(P["chip_steel"])

    def build(nodes, links, ctx):
        g = ab.N(nodes, links)
        edge = g.edge(0.06, 9.0)
        chip_noise = g.noise(5.0, 10.0, 0.62, g.coords())
        speck = g.noise(1.6, 6.0, 0.6, g.coords())
        chips = g.smoothstep(g.math("ADD", g.math("MULTIPLY", edge, 1.15), g.math("MULTIPLY", chip_noise, 0.75)),
                             0.86, 0.9)
        face_chips = g.smoothstep(speck, 0.71, 0.715)
        chips = g.math("MAXIMUM", chips, face_chips)
        cav = g.cavity(0.35, 1.4)
        mottle = g.noise(0.9, 3.0, 0.5, g.coords())
        base = g.mix(g.math("MULTIPLY", mottle, 0.35), green, tuple(c * 1.25 for c in green))
        base = g.mix(g.math("MULTIPLY", cav, 0.55), base, srgb("#1a1a14"))
        col = g.mix(chips, base, steel)
        rough = g.lerp(chips, g.math("ADD", 0.34, g.math("MULTIPLY", cav, 0.35)), 0.48)
        peel = g.noise(55.0, 2.0, 0.5, g.coords())
        h = g.math("SUBTRACT", g.math("MULTIPLY", peel, 0.15), g.math("MULTIPLY", chips, 1.0))
        return {"albedo": col, "rough": rough, "metal": chips, "mask": g.val(P["camo"]["enamel"]),
                "normal": g.bump(h, 0.35, 0.02)}
    return ab.look_material("enamel", build)


def brass(P, name="brass", tint="#d9b36a", tarnish="#5e4a24", camo_key="brass", rough0=0.3):
    base_c, tarn = srgb(tint), srgb(tarnish)

    def build(nodes, links, ctx):
        g = ab.N(nodes, links)
        edge = g.edge(0.05, 7.0)
        cav = g.cavity(0.3, 1.6)
        brushed = g.noise(9.0, 6.0, 0.7, g.coords((0.08, 4.0, 4.0)))
        blotch = g.noise(1.4, 5.0, 0.6, g.coords())
        tarnish_f = g.math("MAXIMUM", g.math("MULTIPLY", cav, 0.9),
                           g.math("MULTIPLY", g.smoothstep(blotch, 0.5, 0.75), 0.45))
        tarnish_f = g.math("MULTIPLY", tarnish_f, g.math("SUBTRACT", 1.0, edge), clamp=True)
        col = g.mix(tarnish_f, base_c, tarn)
        col = g.mix(g.math("MULTIPLY", edge, 0.6), col, tuple(min(1.0, c * 1.18) for c in base_c))
        rough = g.math("ADD", g.math("ADD", rough0, g.math("MULTIPLY", brushed, 0.12)),
                       g.math("SUBTRACT", g.math("MULTIPLY", tarnish_f, 0.3), g.math("MULTIPLY", edge, 0.12)))
        return {"albedo": col, "rough": rough, "metal": g.val(1.0), "mask": g.val(P["camo"][camo_key]),
                "normal": g.bump(brushed, 0.08, 0.01)}
    return ab.look_material(name, build)


def coin_roll(P, pitch=0.085):
    """Tokens stacked face to face along x: the seams are a band pattern in the normal and colour maps."""
    base_c, tarn = srgb("#c8a25a"), srgb("#4a3a1c")

    def build(nodes, links, ctx):
        g = ab.N(nodes, links)
        tc = nodes.new("ShaderNodeTexCoord")
        sep = nodes.new("ShaderNodeSeparateXYZ")
        links.new(tc.outputs["Object"], sep.inputs[0])
        phase = g.math("FRACT", g.math("DIVIDE", sep.outputs["X"], pitch))
        seam = g.smoothstep(g.math("ABSOLUTE", g.math("SUBTRACT", phase, 0.5)), 0.38, 0.5)
        jitter = g.noise(3.0, 4.0, 0.6, g.coords())
        col = g.mix(g.math("MAXIMUM", g.math("MULTIPLY", seam, 0.7), g.math("MULTIPLY", jitter, 0.35)), base_c, tarn)
        return {"albedo": col, "rough": g.math("ADD", 0.32, g.math("MULTIPLY", seam, 0.3)), "metal": g.val(1.0),
                "mask": g.val(P["camo"]["token"]), "normal": g.bump(g.math("SUBTRACT", 1.0, seam), 0.6, 0.02)}
    return ab.look_material("coin_roll", build)


def chrome(P):
    def build(nodes, links, ctx):
        g = ab.N(nodes, links)
        cav = g.cavity(0.25, 1.5)
        scratch = g.noise(30.0, 8.0, 0.75, g.coords((0.3, 1.0, 6.0)))
        pit = g.smoothstep(g.noise(12.0, 4.0, 0.6, g.coords()), 0.68, 0.74)
        col = g.mix(g.math("MAXIMUM", g.math("MULTIPLY", cav, 0.6), g.math("MULTIPLY", pit, 0.5)),
                    srgb("#d8dadc"), srgb("#4a4440"))
        rough = g.math("ADD", 0.07, g.math("ADD", g.math("MULTIPLY", scratch, 0.08), g.math("MULTIPLY", cav, 0.25)))
        return {"albedo": col, "rough": rough, "metal": g.val(1.0), "mask": g.val(P["camo"]["chrome"]),
                "normal": g.bump(scratch, 0.03, 0.005)}
    return ab.look_material("chrome", build)


def steel(P):
    def build(nodes, links, ctx):
        g = ab.N(nodes, links)
        cav = g.cavity(0.15, 1.5)
        col = g.mix(cav, srgb("#6e6c68"), srgb("#2a2622"))
        return {"albedo": col, "rough": g.math("ADD", 0.36, g.math("MULTIPLY", cav, 0.3)), "metal": g.val(1.0),
                "mask": g.val(P["camo"]["steel"]), "normal": None}
    return ab.look_material("steel", build)


def plate_paint(P):
    def build(nodes, links, ctx):
        g = ab.N(nodes, links)
        edge = g.edge(0.03, 10.0)
        wear = g.smoothstep(g.math("ADD", edge, g.math("MULTIPLY", g.noise(14.0, 6.0, 0.6, g.coords()), 0.5)),
                            0.85, 0.9)
        col = g.mix(wear, srgb("#141413"), srgb("#c9a45c"))
        return {"albedo": col, "rough": g.lerp(wear, 0.5, 0.25), "metal": wear, "mask": g.val(P["camo"]["plate"]),
                "normal": None}
    return ab.look_material("plate_paint", build)


def glass(P):
    def build(nodes, links, ctx):
        g = ab.N(nodes, links)
        smudge = g.smoothstep(g.noise(2.2, 6.0, 0.65, g.coords()), 0.45, 0.8)
        alpha = g.math("ADD", P["glass_alpha"], g.math("MULTIPLY", smudge, 0.18))
        col = g.mix(smudge, srgb(P["glass_tint"]), srgb("#8a8270"))
        return {"albedo": col, "rough": g.math("ADD", 0.04, g.math("MULTIPLY", smudge, 0.3)), "metal": g.val(0.0),
                "mask": alpha, "normal": None}
    return ab.look_material("glass", build)


# ------------------------------------------------------------------ model
def build(P):
    B = P["bones"]
    M = {"enamel": enamel(P), "brass": brass(P), "brass_dark": brass(P, "brass_dark", "#b8924e", "#3d2f16",
                                                                      "brass", 0.38),
         "token": brass(P, "token", "#c8a25a", "#4a3a1c", "token", 0.34),
         "letters": brass(P, "letters", "#e6c27a", "#6a5228", "plate", 0.2),
         "roll": coin_roll(P), "chrome": chrome(P), "steel": steel(P), "plate": plate_paint(P), "glass": glass(P)}
    part = ab.part
    R = ab.rng(P.get("seed", 1950))

    def screw(name, c, n, bone=B["body"], atlas="main", r=0.075):
        ob = ab.dome(name, c, n, r, r * 0.45, 12)
        ax = [i for i in range(3) if abs(n[i]) > 0.5][0]
        across = (ax + 1) % 3 if ax != 0 else 2
        lo, hi = list(c), list(c)
        for i in range(3):
            half = 0.2 if i == ax else (r * 1.2 if i == across else 0.012)
            lo[i] -= half
            hi[i] += half
            if i == ax:
                lo[i], hi[i] = (c[i] + 0.022, c[i] + 0.2) if n[ax] > 0 else (c[i] - 0.2, c[i] - 0.022)
        ab.cut(ob, ab.box(name + "_slot", lo, hi))
        return part(ob, bone, atlas, M["steel"], smooth_angle=60)

    def rivet(name, c, n, bone=B["body"], atlas="main", r=0.055, mat="brass"):
        return part(ab.dome(name, c, n, r, r * 0.6, 10), bone, atlas, M[mat], smooth_angle=80)

    # ---- receiver: the fare box (enamel), top sloping down behind the hopper so the hammer spur shows
    rec = ab.prism("receiver", [(-15.2, -2.25), (-9.4, -2.25), (-9.4, 1.85), (-12.4, 1.85), (-14.0, 1.3),
                                (-15.2, 0.7)], -0.86, 0.86)
    groove = ab.box("rec_seam", (-15.4, -1.0, -0.62), (-9.2, 1.0, -0.56))
    ab.cut(rec, groove)
    part(rec, B["body"], "main", M["enamel"], bevel_width=0.07, segments=3)
    # brass belt line under the seam
    part(ab.box("belt", (-15.12, -0.9, -0.5), (-9.45, 0.9, -0.3)), B["body"], "main", M["brass"], 0.025, 2)
    # fare plate (left side, faces the camera) with raised lettering and rivets
    part(ab.box("plate", (-14.85, 0.84, -0.12), (-12.55, 0.92, 1.25)), B["body"], "main", M["plate"], 0.018, 2)
    for t, z, s in (("FARE", 0.83, 0.44), ("30", 0.2, 0.62)):
        part(ab.text("txt_" + t, t, s, (-13.7, 0.92, z), (-1, 0, 0), (0, 0, 1), 0.025, 0.006), B["body"], "main",
             M["letters"], smooth_angle=30)
    for i, (x, z) in enumerate(((-14.7, 0.02), (-12.7, 0.02), (-14.7, 1.11), (-12.7, 1.11))):
        rivet("plate_rivet%d" % i, (x, 0.92, z), (0, 1, 0), r=0.05)
    # right side door: a proud panel with four screws
    part(ab.box("door", (-14.6, -0.92, -1.95), (-12.7, -0.84, -0.8)), B["body"], "main", M["enamel"], 0.03, 2)
    for i, (x, z) in enumerate(((-14.42, -1.8), (-12.88, -1.8), (-14.42, -0.95), (-12.88, -0.95))):
        screw("door_screw%d" % i, (x, -0.92, z), (0, -1, 0))
    for i, (x, z) in enumerate(((-10.0, 1.45), (-10.0, -1.85))):
        for side in (1, -1):
            screw("rec_screw%d_%d" % (i, side), (x, 0.86 * side, z), (0, side, 0))

    # ---- stock: sheet-metal enamel shell, brass butt plate, rivet rows
    stock = ab.prism("stock", [(-15.25, 0.0), (-16.5, -0.42), (-18.5, -1.05), (-21.3, -2.32), (-21.55, -2.45),
                               (-21.72, -4.2), (-21.55, -5.85), (-21.2, -5.9), (-20.0, -5.05), (-18.5, -3.95),
                               (-17.0, -3.0), (-15.6, -2.35), (-15.25, -2.25)][::-1], -0.84, 0.84)
    for side in (1, -1):
        ab.groove(stock, [(-16.2, -0.75), (-18.4, -1.55), (-20.9, -2.7), (-21.15, -4.3), (-20.9, -5.25),
                          (-19.9, -4.65), (-18.3, -3.55), (-16.8, -2.65), (-16.2, -2.45)], 0.84 * side)
    part(stock, B["body"], "main", M["enamel"], bevel_width=0.1, segments=3)
    part(ab.prism("buttplate", [(-21.5, -2.3), (-21.82, -2.35), (-22.0, -4.2), (-21.82, -6.0), (-21.5, -6.0),
                                (-21.66, -4.2)][::-1], -0.88, 0.88), B["body"], "main", M["brass_dark"], 0.04, 2)
    for side in (1, -1):
        for i in range(4):
            t = (i + 0.5) / 4
            x = -16.0 + (-20.8 + 16.0) * t
            ztop = -0.42 + (-2.15 + 0.42) * t
            rivet("stock_rivet%d_%d" % (i, side), (x, 0.84 * side, ztop - 0.25), (0, side, 0))
    for side in (1, -1):
        screw("butt_screw%d" % side, (-21.66, 0.0, -3.2 if side > 0 else -5.2), (-1, 0, 0))

    # ---- fore-end under the chute (enamel) with brass end cap and grip ribs
    fe = ab.box("foreend", (-9.45, -1.12, -0.75), (0.9, 1.12, 0.78))
    for i in range(6):
        x = -7.6 + i * 1.1
        for side in (1, -1):
            ab.cut(fe, ab.box("rib%d_%d" % (i, side), (x, 1.06 * side - 0.2, -0.35), (x + 0.32, 1.06 * side + 0.2,
                                                                                      0.25)))
    part(fe, B["body"], "main", M["enamel"], bevel_width=0.1, segments=3)
    part(ab.box("fe_cap", (0.88, -1.15, -0.8), (1.25, 1.15, 0.82)), B["body"], "main", M["brass"], 0.05, 2)

    # ---- the coin chute (barrel): slotted rectangular brass tube, flared mouth
    chute = ab.box("chute", (-9.4, -0.62, 0.72), (5.6, 0.62, 2.2))
    for i in range(7):
        x = -7.9 + i * 1.75
        ab.cut(chute, ab.box("slot%d" % i, (x, -0.38, 2.08), (x + 0.16, 0.38, 2.4)))
    for side in (1, -1):
        ab.cut(chute, ab.box("sideslot%d" % side, (-7.8, 0.62 * side - 0.1, 1.33), (3.6, 0.62 * side + 0.1, 1.58)))
    part(chute, B["body"], "main", M["brass"], bevel_width=0.07, segments=3)
    mouth = ab.box("mouth", (5.55, -0.78, 0.6), (6.15, 0.78, 2.32))
    ab.cut(mouth, ab.box("mouth_hole", (5.8, -0.46, 0.95), (6.4, 0.46, 1.98)))
    part(mouth, B["body"], "main", M["brass_dark"], bevel_width=0.06, segments=3)
    for i, x in enumerate((-6.2, -1.6)):
        part(ab.box("band%d" % i, (x, -0.7, 0.66), (x + 0.36, 0.7, 2.28)), B["body"], "main", M["steel"], 0.04, 2)
        for side in (1, -1):
            screw("band_screw%d_%d" % (i, side), (x + 0.18, 0.7 * side, 1.47), (0, side, 0), r=0.07)
    # sight: brass block with two ears (notch) and a centre post, on the donor's sight line
    part(ab.box("sight_base", (2.6, -0.42, 2.16), (5.0, 0.42, 2.45)), B["body"], "main", M["brass"], 0.05, 2)
    for side in (1, -1):
        part(ab.box("sight_ear%d" % side, (3.7, 0.16 * side if side > 0 else -0.38, 2.4),
                    (4.35, 0.38 if side > 0 else -0.16, 3.1)), B["body"], "main", M["brass"], 0.04, 2)
    part(ab.box("sight_post", (4.15, -0.05, 2.4), (4.3, 0.05, 2.98)), B["body"], "main", M["steel"], 0.015, 1)

    # ---- the hopper: brass frame, glass on rear / left / right, coin slot lid, tokens stacked inside
    hx0, hx1, hy, hz0, hz1 = -12.3, -8.75, 0.98, 1.82, 2.84
    part(ab.box("hop_base", (hx0, -hy, hz0), (hx1, hy, hz0 + 0.12)), B["body"], "main", M["brass"], 0.03, 2)
    lid = ab.box("hop_lid", (hx0 - 0.04, -hy - 0.04, hz1 - 0.13), (hx1 + 0.04, hy + 0.04, hz1))
    part(lid, B["body"], "main", M["brass"], 0.035, 2)
    funnel = ab.box("hop_funnel", (-11.25, -0.36, hz1 - 0.02), (-9.85, 0.36, hz1 + 0.1))
    ab.cut(funnel, ab.box("coin_slot", (-11.0, -0.045, hz1 - 0.2), (-10.1, 0.045, hz1 + 0.3)))
    part(funnel, B["body"], "main", M["brass_dark"], 0.03, 2)
    for i, (x, y) in enumerate(((hx0, hy), (hx0, -hy), (hx1, hy), (hx1, -hy))):
        part(ab.box("post%d" % i, (x - 0.09 if x == hx0 else x - 0.1, y - 0.09 if y > 0 else y - 0.01,
                                   hz0 + 0.1),
                    (x + 0.1 if x == hx0 else x + 0.09, y + 0.01 if y > 0 else y + 0.09, hz1 - 0.12)),
             B["body"], "main", M["brass"], 0.025, 2)
    part(ab.box("hop_front", (hx1 - 0.1, -hy + 0.05, hz0 + 0.1), (hx1, hy - 0.05, hz1 - 0.12)), B["body"], "main",
         M["brass"], 0.02, 2)
    for i, (x, y) in enumerate(((hx0 + 0.15, hy - 0.15), (hx0 + 0.15, -hy + 0.15), (hx1 - 0.15, hy - 0.15),
                                (hx1 - 0.15, -hy + 0.15))):
        screw("lid_screw%d" % i, (x, y, hz1), (0, 0, 1), r=0.06)
    for side in (1, -1):
        part(ab.box("glass_side%d" % side, (hx0 + 0.06, side * (hy - 0.06) - 0.02, hz0 + 0.12),
                    (hx1 - 0.08, side * (hy - 0.06) + 0.02, hz1 - 0.13)), B["body"], "glass", M["glass"])
    part(ab.box("glass_rear", (hx0 - 0.02, -hy + 0.06, hz0 + 0.12), (hx0 + 0.02, hy - 0.06, hz1 - 0.13)),
         B["body"], "glass", M["glass"])
    # one master token (UV island shared by every token copy)
    tok_r, tok_t = 0.33, 0.075
    token = ab.cylinder("token", (0, 0, 0), "z", tok_r, tok_t, 16)
    ab.cut(token, ab.cylinder("token_hole", (0, 0, 0), "z", 0.09, 0.3, 8))
    token = part(token, B["body"], "main", M["token"], bevel_width=0.012, segments=1)
    stacks = [(-11.75, 0.38, 10), (-11.0, -0.35, 8), (-10.25, 0.33, 11), (-9.5, -0.3, 7), (-10.9, 0.42, 3)]
    n = 0
    for sx, sy, cnt in stacks:
        for k in range(cnt):
            if n == 0:
                n += 1
                token.data.transform(Matrix.Translation((sx, sy, hz0 + 0.12 + tok_t / 2)))
                continue
            jitter = Matrix.Translation((sx + R.uniform(-0.04, 0.04), sy + R.uniform(-0.04, 0.04),
                                         hz0 + 0.12 + tok_t / 2 + k * (tok_t + 0.002)))
            rot = Matrix.Rotation(R.uniform(-0.06, 0.06), 4, "X") @ Matrix.Rotation(R.uniform(0, 6.28), 4, "Z")
            back = Matrix.Translation((-stacks[0][0], -stacks[0][1], -(hz0 + 0.12 + tok_t / 2)))
            ab.copy_after_bake(token, "token%d" % n, B["body"], jitter @ rot @ back)
            n += 1

    # ---- hammer: a ticket-punch spur behind the hopper
    part(ab.prism("hammer", [(-13.0, 0.2), (-12.95, 1.2), (-13.5, 1.62), (-14.3, 1.74), (-14.9, 1.62),
                             (-14.88, 1.42), (-14.2, 1.4), (-13.7, 1.12), (-13.6, 0.2)][::-1], -0.18, 0.18),
         B["hammer"], "acc", M["brass_dark"], 0.03, 2)
    # ---- trigger
    part(ab.prism("trigger", [(-14.55, -2.0), (-14.85, -2.6), (-15.05, -3.2), (-15.35, -3.78), (-15.6, -3.72),
                              (-15.3, -3.12), (-15.12, -2.55), (-14.95, -2.0)][::-1], -0.12, 0.12),
         B["trigger"], "acc", M["steel"], 0.03, 2)
    # ---- lever: chromed turnstile arm (loop) + turnstile hub with three arms on both sides of the pivot
    loop = [(-13.2, 0, -2.0), (-13.9, 0, -2.7), (-14.6, 0, -3.95), (-15.6, 0, -4.95), (-17.2, 0, -5.85),
            (-18.8, 0, -6.3), (-19.7, 0, -5.95), (-19.85, 0, -5.15), (-19.0, 0, -4.75), (-17.8, 0, -3.85),
            (-16.95, 0, -3.25)]
    part(ab.curve_tube("lever_arm", loop, 0.16), B["lever"], "acc", M["chrome"], smooth_angle=50)
    part(ab.dome("lever_knob", (-16.95, 0, -3.25), (0.6, 0, 0.8), 0.2, 0.2, 16), B["lever"], "acc", M["chrome"],
         smooth_angle=80)
    piv = P["pivot"]
    for side in (1, -1):
        y0 = 0.86 * side
        hub = ab.cylinder("hub%d" % side, (piv[0], y0 + 0.07 * side, piv[2]), "y", 0.36, 0.14, 28)
        part(hub, B["lever"], "acc", M["chrome"], bevel_width=0.035, segments=3)
        part(ab.dome("hub_cap%d" % side, (piv[0], y0 + 0.14 * side, piv[2]), (0, side, 0), 0.16, 0.08, 16),
             B["lever"], "acc", M["steel"], smooth_angle=70)
        for k in range(3):
            a = math.radians(90 + 120 * k)
            d = Vector((math.cos(a), 0, math.sin(a)))
            p0 = Vector((piv[0], y0 + 0.08 * side, piv[2])) + d * 0.3
            p1 = p0 + d * 0.33
            part(ab.curve_tube("spoke%d_%d" % (side, k), [tuple(p0), tuple(p0.lerp(p1, 0.5)), tuple(p1)], 0.07),
                 B["lever"], "acc", M["chrome"], smooth_angle=50)
            part(ab.dome("spoke_ball%d_%d" % (side, k), tuple(p1), tuple(d), 0.1, 0.1, 12), B["lever"], "acc",
                 M["chrome"], smooth_angle=80)

    # ---- magazine: a brass coin tube (two twins: mag1 in the gun, mag2 the fresh one in the hand)
    mz, mr = -1.29, 0.66
    mx0, mx1 = -10.6, 5.2
    mag = ab.tube("magtube", ((mx0 + mx1) / 2, 0, mz), "x", mr, mr - 0.07, mx1 - mx0, 36)
    for side in (1, -1):
        ab.cut(mag, ab.box("magwin%d" % side, (-9.3, side * 0.45 - 0.4, mz - 0.17), (4.5, side * 0.45 + 0.4,
                                                                                     mz + 0.17)))
    mag = part(mag, B["mag1"], "acc", M["brass_dark"], bevel_width=0.02, segments=2)
    cap_f = ab.cylinder("magcap_f", (mx1 + 0.12, 0, mz), "x", mr + 0.05, 0.3, 36)
    for k in range(18):
        a = 2 * math.pi * k / 18
        ab.cut(cap_f, ab.box("knurl%d" % k, (mx1 - 0.1, (mr + 0.04) * math.cos(a) - 0.03,
                                             mz + (mr + 0.04) * math.sin(a) - 0.03),
                             (mx1 + 0.4, (mr + 0.04) * math.cos(a) + 0.03, mz + (mr + 0.04) * math.sin(a) + 0.03)))
    cap_f = part(cap_f, B["mag1"], "acc", M["brass"], bevel_width=0.025, segments=2)
    cap_r = part(ab.cylinder("magcap_r", (mx0 - 0.08, 0, mz), "x", mr + 0.02, 0.18, 36), B["mag1"], "acc",
                 M["brass"], bevel_width=0.03, segments=2)
    # coin rolls on the shell bones: one master roll, copies on every other shell bone and in the twin
    shells = [x + P.get("shell_offset_x", 0.0) for x in P["shell_x"]]
    roll = ab.cylinder("roll", (shells[0], 0, mz), "x", mr - 0.11, 2.6, 16)
    roll = part(roll, B["shells"][0], "acc", M["roll"], smooth_angle=40)
    for k, x in enumerate(shells[1:], start=1):
        ab.copy_after_bake(roll, "roll%d" % k, B["shells"][k], Matrix.Translation((x - shells[0], 0, 0)))
    for src in (mag, cap_f, cap_r):
        ab.copy_after_bake(src, src.name + "_twin", B["mag2"], Matrix.Identity(4))
    for k, x in enumerate(shells):
        ab.copy_after_bake(roll, "roll_twin%d" % k, B["mag2"], Matrix.Translation((x - shells[0], 0, 0)))
    # loose rolls (chambered / ejected): short copies of the master roll scaled down along x
    lc = P["loose_center"]
    for k, bone in enumerate(B["loose"]):
        m = Matrix.Translation((lc[0], lc[1], lc[2])) @ Matrix.Diagonal((0.45, 0.82, 0.82, 1.0)) @ \
            Matrix.Translation((-shells[0], 0, -mz))
        ab.copy_after_bake(roll, "loose%d" % k, bone, m)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    params = json.load(open(argv[argv.index("--params") + 1]))
    out = argv[argv.index("--out") + 1]
    os.makedirs(out, exist_ok=True)
    ab.reset_scene()
    build(params)
    preview = None
    if params.get("preview"):
        preview = dict(params["preview"])
        preview["path"] = os.path.abspath(os.path.join(out, "blender_3q.png"))
    rep = ab.finish(out, params["atlases"], params["camo_uv_per_inch"], preview)
    print("GENERATOR_OK " + json.dumps({"tris": rep["tris"], "objects": len(rep["objects"]),
                                        "atlases": rep["atlases"]}))


main()
