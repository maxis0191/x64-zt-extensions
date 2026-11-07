"""Synthetic tests for t7_fx_to_iw7.py (no game data)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_vfx as vfx  # noqa: E402
import t7_fx_to_iw7 as conv  # noqa: E402


def template_emitter():
    e = vfx.new_emitter()
    st = vfx.new_state()
    init, update = st["moduleGroupDefs"][0], st["moduleGroupDefs"][1]
    for t in ("INIT_SPAWN", "INIT_ATTRIBUTES", "INIT_MATERIAL", "INIT_ATLAS", "INIT_SPAWN_SHAPE_BOX"):
        init["moduleDefs"].append(vfx.new_module("PARTICLE_MODULE_" + t))
    for t in ("COLOR_GRAPH", "SIZE_GRAPH", "INTENSITY_GRAPH"):
        update["moduleDefs"].append(vfx.new_module("PARTICLE_MODULE_" + t))
    e["stateDefs"].append(st)
    e["numStates"] = 1
    e["particleCountMax"] = 1
    return e


def vis(color, size):
    state = {"color": color, "rotation_delta": 0.0, "rotation_total": 0.0, "size": [size, size], "scale": 0.0,
             "extra": [1.0, 0.0, 0.0, 1.0]}
    return {"base": state, "amplitude": dict(state, color=[0, 0, 0, 0], size=[0.0, 0.0])}


def element(kind, a, b, life=150):
    zero = {"base": [0.0, 0.0, 0.0], "amplitude": [0.0, 0.0, 0.0]}
    return {
        "type": 2, "type_name": "sprite", "spawn_kind": kind,
        "visual": {"kind": "material", "name": "ei/gfx_ring_thin"},
        "scalars": {"spawn": {"a": a, "b": b}, "lifespan_msec": {"base": life, "amplitude": 50},
                    "spawn_origin": [{"base": -2.0, "amplitude": 2.0}, {"base": 0.0, "amplitude": 0.0},
                                     {"base": 0.0, "amplitude": 0.0}]},
        "vis_samples": [vis([64, 255, 0, 115], 0.83), vis([0, 255, 0, 0], 7.5)],
        "vel_samples": [{"local_velocity": {"base": [0.1, 0.0, 0.0], "amplitude": [0.0, 0.0, 0.0]},
                         "local_total_delta": zero, "world_velocity": zero, "world_total_delta": zero}],
    }


MATERIALS = {"ei/gfx_ring_thin": {"bo3": "ei/gfx_ring_thin", "iw7": "eq/bo3wpn_gfx_ring_thin", "mode": "add",
                                  "atlas": [1, 1]}}


class ConvertTest(unittest.TestCase):
    def convert(self, elements):
        fx = {"elements": elements}
        model, report = conv.convert("vfx/test/fx", fx, {"sprite": template_emitter()}, MATERIALS,
                                     {"add": 20.0, "blend": 1.0, "light": 1.0})
        back = vfx.decode(vfx.encode(model))
        return back["system"]["emitterDefs"], report

    def test_finite_looping_becomes_spread_burst(self):
        (em,), report = self.convert([element("looping", 50, 3)])
        self.assertEqual(report["emitters"], 1)
        self.assertAlmostEqual(em["particleLife"]["min"], 0.15, places=5)
        self.assertAlmostEqual(em["particleLife"]["max"], 0.2, places=5)
        self.assertEqual(em["particleBurstCount"], {"min": 3, "max": 3})
        self.assertAlmostEqual(em["particleDelay"]["max"], 0.1, places=5)

    def test_endless_looping_becomes_rate(self):
        (em,), _ = self.convert([element("looping", 200, conv.INT_MAX, life=1000)])
        self.assertAlmostEqual(em["particleSpawnRate"]["min"], 5.0, places=4)

    def test_curves_material_shape_velocity(self):
        (em,), _ = self.convert([element("one_shot", 2, 1)])
        self.assertEqual(em["particleBurstCount"], {"min": 2, "max": 3})
        mats = [vfx.module_data(m) for g in em["stateDefs"][0]["moduleGroupDefs"] for m in (g.get("moduleDefs") or [])]
        types = [m["moduleType"] for g in em["stateDefs"][0]["moduleGroupDefs"] for m in (g.get("moduleDefs") or [])]
        self.assertNotIn("PARTICLE_MODULE_INIT_ATLAS", types)   # static material
        by = dict(zip(types, mats))
        self.assertEqual(by["PARTICLE_MODULE_INIT_MATERIAL"]["m_linkedAssetList"]["assetList"][0]["material"],
                         "eq/bo3wpn_gfx_ring_thin")
        red = by["PARTICLE_MODULE_COLOR_GRAPH"]["m_curves"][0]["controlPoints"]
        self.assertAlmostEqual(red[0]["value"], 64 / 255.0, places=5)
        alpha = by["PARTICLE_MODULE_COLOR_GRAPH"]["m_curves"][3]["controlPoints"]
        self.assertAlmostEqual(alpha[-1]["value"], 0.0, places=6)
        size = by["PARTICLE_MODULE_SIZE_GRAPH"]["m_curves"][0]
        self.assertAlmostEqual(size["scale"], 15.0, places=4)   # radius 7.5 -> 15 units across
        self.assertAlmostEqual(by["PARTICLE_MODULE_INIT_SPAWN_SHAPE_BOX"]["m_dimensionsMin"][0], -2.0)
        self.assertAlmostEqual(by["PARTICLE_MODULE_INIT_ATTRIBUTES"]["m_velocityMin"][0], 100.0, places=3)
        self.assertAlmostEqual(by["PARTICLE_MODULE_INTENSITY_GRAPH"]["m_curves"][0]["scale"], 20.0)

    def test_negative_velocity_amplitude_keeps_min_below_max(self):
        e = element("one_shot", 1, 0)
        e["vel_samples"][0]["local_velocity"] = {"base": [0.2, 0.1, 0.0], "amplitude": [-0.15, -0.2, 0.0]}
        (em,), _ = self.convert([e])
        attrs = [vfx.module_data(m) for g in em["stateDefs"][0]["moduleGroupDefs"] for m in (g.get("moduleDefs") or [])
                 if m["moduleType"] == "PARTICLE_MODULE_INIT_ATTRIBUTES"][0]
        for lo, hi in zip(attrs["m_velocityMin"][:3], attrs["m_velocityMax"][:3]):
            self.assertLessEqual(lo, hi)
        self.assertAlmostEqual(attrs["m_velocityMin"][1], -100.0, places=3)

    def test_system_header_is_drawable(self):
        fx = {"elements": [element("one_shot", 2, 1)]}
        model, _ = conv.convert("vfx/test/fx", fx, {"sprite": template_emitter()}, MATERIALS,
                                {"add": 20.0, "blend": 1.0, "light": 1.0})
        s = vfx.decode(vfx.encode(model))["system"]
        self.assertEqual(s["flags"], 0x40001)
        self.assertEqual((s["drawFrustumCullRadius"], s["updateFrustumCullRadius"]), (-1.0, -1.0))

    def test_spawn_range_and_delay(self):
        e = element("one_shot", 2, 1)
        e["scalars"]["spawn_range"] = {"min": 600.0, "max": 1400.0}
        e["scalars"]["spawn_delay_msec"] = {"base": 100, "amplitude": 50}
        (em,), _ = self.convert([e])
        self.assertEqual((em["spawnRangeSq"]["min"], em["spawnRangeSq"]["max"]), (360000.0, 1960000.0))
        self.assertAlmostEqual(em["emitterDelay"]["min"], 0.1, places=6)
        self.assertAlmostEqual(em["emitterDelay"]["max"], 0.15, places=6)

    def test_unbounded_spawn_range_stays_unlimited(self):
        e = element("one_shot", 2, 1)
        e["scalars"]["spawn_range"] = {"min": 0.0, "max": 0.0}
        (em,), _ = self.convert([e])
        self.assertEqual((em["spawnRangeSq"]["min"], em["spawnRangeSq"]["max"]), (0.0, 0.0))

    def test_unconverted_material_is_reported(self):
        e = element("one_shot", 1, 0)
        e["visual"] = {"kind": "material", "name": "ei/gfx_distort_heat"}
        ems, report = self.convert([e])
        self.assertFalse(ems)
        self.assertEqual(report["emitters"], 0)
        self.assertIn("not converted", report["skipped"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
