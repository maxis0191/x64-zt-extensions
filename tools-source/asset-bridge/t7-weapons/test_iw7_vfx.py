"""Synthetic tests for iw7_vfx.py (no game data)."""
import contextlib
import io
import json
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_vfx as vfx  # noqa: E402


def offsets(st):
    return {n: o for n, o, _ in st.members}


def sample_model():
    """One emitter, one sprite state: material (shared pointer), colour graph, runner, sound, decal."""
    m = vfx.new_model("vfx/test/raygun_flash")
    e = vfx.new_emitter()
    e["particleLife"] = {"min": 100.0, "max": 150.0}
    e["fadeCurveDef"]["controlPoints"] = vfx.new_curve_points([(0, 1), (1, 0)])
    s = vfx.new_state()
    init, update, _ = s["moduleGroupDefs"]

    mats = []
    for name in ("eq/vfx_flash_green", "eq/vfx_flash_green"):
        mod = vfx.new_module("PARTICLE_MODULE_INIT_MATERIAL")
        la = vfx.new_linked_asset("PARTICLE_MODULE_INIT_MATERIAL", material=name)
        la["material@ptr"] = "0x5000"   # same Material*: the dumper writes an OFFSET the second time
        vfx.module_data(mod)["m_linkedAssetList"]["assetList"] = [la]
        mats.append(mod)
    init["moduleDefs"] += mats

    runner = vfx.new_module("PARTICLE_MODULE_INIT_RUNNER")
    vfx.module_data(runner)["m_linkedAssetList"]["assetList"] = [
        vfx.new_linked_asset("PARTICLE_MODULE_INIT_RUNNER", particleSystem="vfx/test/child")]
    sound = vfx.new_module("PARTICLE_MODULE_INIT_SOUND")
    vfx.module_data(sound)["m_linkedAssetList"]["assetList"] = [
        vfx.new_linked_asset("PARTICLE_MODULE_INIT_SOUND", sound="wpn_raygun_fire")]
    decal = vfx.new_module("PARTICLE_MODULE_INIT_DECAL")
    vfx.module_data(decal)["m_linkedAssetList"]["assetList"] = [
        vfx.new_linked_asset("PARTICLE_MODULE_INIT_DECAL", material0="mim/a", material1="wim/a")]
    atlas = vfx.new_module("PARTICLE_MODULE_INIT_ATLAS")
    vfx.module_data(atlas)["m_playRate"] = 30
    init["moduleDefs"] += [runner, sound, decal, atlas]

    color = vfx.new_module("PARTICLE_MODULE_COLOR_GRAPH")
    curves = vfx.module_data(color)["m_curves"]
    for i, value in enumerate((0.2, 1.0, 0.3, 1.0)):
        curves[i]["scale"] = 1.0
        curves[i]["controlPoints"] = vfx.new_curve_points([(0, value), (0.5, value), (1, 0)])
    update["moduleDefs"].append(color)

    e["stateDefs"].append(s)
    m["system"]["emitterDefs"].append(e)
    return m


class LayoutTest(unittest.TestCase):
    def test_struct_sizes_and_offsets(self):
        self.assertEqual(vfx.SYSTEM.size, 0x80)
        self.assertEqual(vfx.EMITTER.size, 144)
        self.assertEqual(offsets(vfx.EMITTER)["fadeCurveDef"], 80)
        self.assertEqual(offsets(vfx.STATE)["flags"], 16)
        self.assertEqual(offsets(vfx.SYSTEM)["editorPosition"], 64)
        decal = vfx.MODULE_DEFS[vfx.MT["PARTICLE_MODULE_INIT_DECAL"]][1]
        self.assertEqual(offsets(decal)["m_linkedAssetList"], 32)
        age = vfx.MODULE_DEFS[vfx.MT["PARTICLE_MODULE_TEST_AGE"]][1]
        self.assertEqual(offsets(age)["m_eventHandlerData"], 16)
        self.assertEqual(offsets(age)["m_age"], 48)
        mdef = vfx.module_def_struct(vfx.MT["PARTICLE_MODULE_INIT_ATLAS"])
        self.assertEqual((mdef.size, offsets(mdef)["initAtlas"]), (160, 16))

    def test_minimal_stream_tokens(self):
        m = vfx.new_model("vfx/x")
        data = vfx.encode(m)
        # the null name pointer got a fresh synthetic value so that the string is written
        m["system"]["name@ptr"] = "0x%x" % vfx.FRESH_POINTER_BASE
        system = vfx.encode_struct(vfx.SYSTEM, m["system"])
        expected = (b"\x08\x01" + struct.pack("<I", 1) + system + b"\x06\x01vfx/x\x00"
                    + b"\x08\x00" + b"\x08\x00")
        self.assertEqual(data, expected)
        self.assertEqual(struct.unpack_from("<i", system, 24)[0], 15)
        back = vfx.decode(data)
        self.assertEqual(back["system"]["name"], "vfx/x")
        self.assertEqual(back["system"]["emitterDefs"], None)


class HeaderTest(unittest.TestCase):
    def test_new_model_has_stock_header(self):
        # Zeroed cull radii and sun distance draw nothing in game: every stock system reads -1/-1/100000.
        s = vfx.new_model("vfx/x")["system"]
        self.assertEqual((s["drawFrustumCullRadius"], s["updateFrustumCullRadius"], s["sunDistance"]),
                         (-1.0, -1.0, 100000.0))
        self.assertEqual(s["editorRotation"], [0.0, 0.0, 0.0, 1.0])
        self.assertEqual(s["flags"], 0x40000)

    def test_system_flags_follow_element_types(self):
        def model(*types):
            m = vfx.new_model("vfx/x")
            for t in types:
                e = vfx.new_emitter()
                e["stateDefs"] = [vfx.new_state("PARTICLE_ELEMENT_TYPE_" + t)]
                m["system"]["emitterDefs"].append(e)
            return m
        self.assertEqual(vfx.system_flags(model("BILLBOARD_SPRITE")), 0x40001)
        self.assertEqual(vfx.system_flags(model("TAIL", "LIGHT_OMNI")), 0x40007)
        self.assertEqual(vfx.system_flags(model("MODEL")), 0x40002)
        self.assertEqual(vfx.system_flags(model("RUNNER")), 0x41000)


class RoundTripTest(unittest.TestCase):
    def test_build_encode_decode_encode(self):
        data = vfx.encode(sample_model())
        model = vfx.decode(data)
        self.assertEqual(vfx.encode(model, strict=True), data)
        self.assertEqual(vfx.encode(json.loads(json.dumps(model)), strict=True), data)
        s = vfx.summary(model)
        self.assertEqual(s["assets"]["material"], ["eq/vfx_flash_green"])
        self.assertEqual(s["assets"]["particleSystem"], ["vfx/test/child"])
        self.assertEqual(s["assets"]["sound"], ["wpn_raygun_fire"])
        self.assertEqual(s["assets"]["material0"], ["mim/a"])
        self.assertNotIn("material2", s["assets"])
        self.assertEqual(s["modules"]["INIT_MATERIAL"], 2)
        e = model["system"]["emitterDefs"][0]
        self.assertEqual(e["numStates"], 1)
        self.assertEqual(e["fadeCurveDef"]["numControlPoints"], 2)
        color = e["stateDefs"][0]["moduleGroupDefs"][1]["moduleDefs"][0]
        pts = color["colorGraph"]["m_curves"][1]["controlPoints"]
        self.assertEqual([p["time"] for p in pts], [0.0, 0.5, 1.0])
        self.assertEqual(pts[1]["invTimeDelta"], 2.0)

    def test_shared_asset_pointer_is_an_offset(self):
        data = vfx.encode(sample_model())
        # entries: root, name, emitters, states, groups, modules, assetList, material (7)
        self.assertEqual(data.count(b"eq/vfx_flash_green\x00"), 1)
        self.assertIn(struct.pack("<BII", vfx.T_OFFSET, 7, 0), data)
        model = vfx.decode(data)
        mods = model["system"]["emitterDefs"][0]["stateDefs"][0]["moduleGroupDefs"][0]["moduleDefs"]
        names = [vfx.linked_assets(m) for m in mods[:2]]
        self.assertEqual(names, [[("material", "eq/vfx_flash_green")]] * 2)

    def test_edit_of_shared_slot_gets_fresh_pointer(self):
        model = vfx.decode(vfx.encode(sample_model()))
        mods = model["system"]["emitterDefs"][0]["stateDefs"][0]["moduleGroupDefs"][0]["moduleDefs"]
        mods[1]["initMaterial"]["m_linkedAssetList"]["assetList"][0]["material"] = "eq/vfx_flash_blue"
        with self.assertRaises(vfx.PointerConflict):
            vfx.encode(model, strict=True)
        back = vfx.decode(vfx.encode(model))
        mods = back["system"]["emitterDefs"][0]["stateDefs"][0]["moduleGroupDefs"][0]["moduleDefs"]
        self.assertEqual([vfx.linked_assets(m)[0][1] for m in mods[:2]],
                         ["eq/vfx_flash_green", "eq/vfx_flash_blue"])
        ptrs = [m["initMaterial"]["m_linkedAssetList"]["assetList"][0]["material@ptr"] for m in mods[:2]]
        self.assertNotEqual(ptrs[0], ptrs[1])

    def test_list_lengths_drive_counts(self):
        model = vfx.decode(vfx.encode(sample_model()))
        e = model["system"]["emitterDefs"][0]
        e["fadeCurveDef"]["controlPoints"].append({"time": 2.0, "value": 0.0, "invTimeDelta": 1.0, "pad": [0]})
        back = vfx.decode(vfx.encode(model))
        self.assertEqual(back["system"]["emitterDefs"][0]["fadeCurveDef"]["numControlPoints"], 3)

    def test_gaps_and_non_finite_floats_survive(self):
        model = vfx.decode(vfx.encode(sample_model()))
        mods = model["system"]["emitterDefs"][0]["stateDefs"][0]["moduleGroupDefs"][0]["moduleDefs"]
        atlas = mods[-1]
        atlas["_gaps"] = {"36": "0101"}            # bytes past ZoneTool's 20-byte InitAtlas
        model["system"]["sunDistance"] = "f32:7fc00001"
        data = vfx.encode(model)
        back = vfx.decode(data)
        self.assertEqual(back["system"]["emitterDefs"][0]["stateDefs"][0]["moduleGroupDefs"][0]
                         ["moduleDefs"][-1]["_gaps"], {"36": "0101"})
        self.assertEqual(back["system"]["sunDistance"], "f32:7fc00001")
        self.assertEqual(vfx.encode(back, strict=True), data)

    def test_truncated_file_is_an_error(self):
        data = vfx.encode(sample_model())
        with self.assertRaises(vfx.FormatError):
            vfx.decode(data[:-3])
        with self.assertRaises(vfx.FormatError):
            vfx.decode(data + b"\0")

    def test_inv_time_delta_is_float32(self):
        pts = vfx.new_curve_points([(0, 0), (0.1, 1), (0.3, 0)])
        self.assertEqual(pts[1]["invTimeDelta"], vfx.f32(1 / vfx.f32(0.1)))
        self.assertEqual(pts[2]["invTimeDelta"], vfx.f32(1 / vfx.f32(vfx.f32(0.3) - vfx.f32(0.1))))
        self.assertEqual(pts[0]["invTimeDelta"], 0.0)


class CliTest(unittest.TestCase):
    def run_main(self, argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vfx.main(argv)
        return code, out.getvalue()

    def test_json_cli_and_roundtrip_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "a.iw7VFX")
            with open(src, "wb") as f:
                f.write(vfx.encode(sample_model()))
            js = os.path.join(tmp, "a.json")
            self.assertEqual(self.run_main(["--to-json", src, "-o", js])[0], 0)
            with open(js, encoding="utf-8") as f:
                doc = json.load(f)
            doc["system"]["emitterDefs"][0]["particleLife"]["max"] = 200.0
            with open(js, "w", encoding="utf-8") as f:
                json.dump(doc, f)
            out = os.path.join(tmp, "b.iw7VFX")
            self.assertEqual(self.run_main(["--from-json", js, "-o", out])[0], 0)
            with open(out, "rb") as f:
                self.assertEqual(vfx.decode(f.read())["system"]["emitterDefs"][0]["particleLife"]["max"], 200.0)

            code, text = self.run_main(["--roundtrip", tmp])
            self.assertEqual(code, 0)
            self.assertIn("2/2 byte-identical", text)
            self.assertIn("PARTICLE_MODULE_INIT_MATERIAL", text)

            with open(os.path.join(tmp, "broken.iw7VFX"), "wb") as f:
                f.write(vfx.encode(sample_model())[:-5])
            code, text = self.run_main(["--roundtrip", tmp])
            self.assertEqual(code, 1)
            self.assertIn("2/3 byte-identical, 1 failed", text)
            self.assertIn("FAIL", text)

    def test_summary_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("vfx/a/flash", "vfx/b/trail"):
                with open(os.path.join(tmp, name.replace("/", "_") + ".iw7VFX"), "wb") as f:
                    f.write(vfx.encode(vfx.new_model(name)))
            code, text = self.run_main(["--summary", tmp, "--match", "trail"])
            self.assertEqual(code, 0)
            self.assertEqual([r["name"] for r in json.loads(text)], ["vfx/b/trail"])


if __name__ == "__main__":
    unittest.main()
