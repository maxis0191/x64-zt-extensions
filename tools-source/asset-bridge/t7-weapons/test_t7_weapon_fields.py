"""Synthetic tests for t7_weapon_fields.py (no game data)."""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_weapon_fields as f  # noqa: E402
import t7_weapon_scan as s  # noqa: E402


def block(values, refs=(), children=None, size=0x40):
    raw = bytearray(size)
    for off, value in values.items():
        if isinstance(value, float):
            struct.pack_into("<f", raw, off, value)
        else:
            struct.pack_into("<i", raw, off, value)
    b = {"addr": "0x0", "size": size, "hex": bytes(raw).hex(), "refs": list(refs)}
    if children:
        b["children"] = children
    return b


def scan():
    def weapon(clip, ammo, speed, anim):
        child = block({0x10: ammo, 0x14: speed}, refs=[{"off": 0x20, "kind": "string", "value": anim}])
        return block({0x8: clip, 0xC: clip}, children={"24": child})

    return {"weapons": {
        "ray_gun_zm": weapon(20, 160, 1.5, "vm_raygun_idle"),
        "ray_gun_upgraded_zm": weapon(40, 200, 1.5, "vm_raygun_idle"),
        "thundergun_zm": weapon(2, 12, 0.5, "vm_thundergun_idle"),
    }}


class FieldTests(unittest.TestCase):
    def test_unique_field_found_across_weapons(self):
        hits = f.find_numeric(scan(), {"ray_gun_zm": 160, "thundergun_zm": 12}, ("i32",))
        self.assertEqual(hits, [("root/24", 0x10, "i32")])

    def test_ambiguity_is_reported_not_resolved(self):
        hits = f.find_numeric(scan(), {"ray_gun_zm": 20}, ("i32",))
        self.assertEqual({off for _, off, _ in hits}, {0x8, 0xC})

    def test_float_match(self):
        hits = f.find_numeric(scan(), {"ray_gun_zm": 1.5, "thundergun_zm": 0.5}, ("f32",))
        self.assertEqual(hits, [("root/24", 0x14, "f32")])

    def test_unknown_weapon_refused(self):
        with self.assertRaises(SystemExit):
            f.find_numeric(scan(), {"missing_zm": 1}, ("i32",))

    def test_ref_table(self):
        table = f.ref_table(scan())
        self.assertEqual(table[("root/24", 0x20)]["thundergun_zm"], '"vm_thundergun_idle"')

    def test_parse_known(self):
        self.assertEqual(f.parse_known("a:1,b:2.5"), {"a": 1, "b": 2.5})


class AssetLogTests(unittest.TestCase):
    def test_asset_log_parsing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "log.tsv")
            with open(path, "w", encoding="utf-8") as out:
                out.write("23\tweapon\t,ray_gun_zm\t0000000145B97FB0\n")
                out.write("3\txanim\tvm_raygun_t7_idle\t0000000142F58EE0\n")
                out.write("malformed line\n")
            by_addr, weapons = s.load_asset_log(path)
        self.assertEqual(weapons, [("ray_gun_zm", 0x145B97FB0)])
        self.assertEqual(by_addr[0x142F58EE0]["type_name"], "xanim")


if __name__ == "__main__":
    unittest.main()
