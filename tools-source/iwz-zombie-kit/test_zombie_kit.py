"""Source tests of the zombie kit on synthetic data (standard library only, no game dump, no Blender).

    python -B -m unittest discover -s tools-source/iwz-zombie-kit

They cover what runs without local inputs: the runner imports and names its missing inputs, the part tables and the
tracked config agree, the scriptable clone swaps whole strings only. The fit (Blender), the model and material
writers on real parts and anything in the game are not covered; see NOTES.md.
"""
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import clone_scriptable  # noqa: E402
import run_zombie  # noqa: E402

ENVIRONMENT = {"IWZ_HEROES": "D:/heroes", "IWZ_BLENDER": "D:/blender.exe", "IWZ_DUMP": "D:/dump", "IWZ_TEXCONV": "D:/texconv.exe"}


def record(text):
    """One string record of a ZoneTool dump: type 6, existing 1, the bytes, NUL."""
    return b"\x06\x01" + text.encode() + b"\0"


class Runner(unittest.TestCase):
    def test_tracked_sources_carry_no_machine_path(self):
        for name in ("run_zombie.py", "fit_zombie.py", "clone_scriptable.py", "inspect_stock_parts.py"):
            with open(os.path.join(HERE, name), encoding="utf-8") as f:
                text = f.read()
            self.assertNotIn("Users\\", text, name)
            self.assertNotIn(":\\", text, name)

    def test_configure_reads_the_environment_and_gives_the_fit_step_its_folder(self):
        environment = dict(ENVIRONMENT)
        saved = (run_zombie.HEROES, run_zombie.BLENDER, run_zombie.DUMP, run_zombie.TEXCONV)
        try:
            run_zombie.configure(environment)
            self.assertEqual((run_zombie.HEROES, run_zombie.BLENDER, run_zombie.DUMP, run_zombie.TEXCONV),
                             ("D:/heroes", "D:/blender.exe", "D:/dump", "D:/texconv.exe"))
            self.assertEqual(environment["IWZ_FIT_DIR"], os.path.join("D:/heroes", "tools", "fit"))
            environment["IWZ_FIT_DIR"] = "E:/fit"
            run_zombie.configure(environment)
            self.assertEqual(environment["IWZ_FIT_DIR"], "E:/fit")
        finally:
            run_zombie.HEROES, run_zombie.BLENDER, run_zombie.DUMP, run_zombie.TEXCONV = saved

    def test_missing_inputs_are_named_and_nothing_is_set(self):
        saved = (run_zombie.HEROES, run_zombie.DUMP)
        with self.assertRaises(SystemExit) as refused:
            run_zombie.configure({"IWZ_BLENDER": "D:/blender.exe"})
        message = str(refused.exception)
        for name in ("IWZ_HEROES", "IWZ_DUMP", "IWZ_TEXCONV"):
            self.assertIn(name, message)
        self.assertNotIn("IWZ_BLENDER:", message)
        self.assertEqual((run_zombie.HEROES, run_zombie.DUMP), saved)

    def test_command_line_stops_before_any_work_when_inputs_are_absent(self):
        environment = {k: v for k, v in os.environ.items() if not k.startswith("IWZ_")}
        with tempfile.TemporaryDirectory() as folder:
            done = subprocess.run([sys.executable, "-I", os.path.join(HERE, "run_zombie.py"), "--config",
                                   os.path.join(HERE, "configs", "zombie_M1.json")],
                                  cwd=folder, env=environment, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(done.returncode, 0)
            self.assertIn("IWZ_HEROES", done.stderr)
            self.assertEqual(os.listdir(folder), [])

    def test_part_tables_of_both_genders_name_the_same_parts(self):
        male, female = run_zombie.GENDER["male"], run_zombie.GENDER["female"]
        self.assertEqual(sorted(male), sorted(female))
        self.assertEqual(sorted(male["swap"]), sorted(female["swap"]))
        self.assertEqual(len(male["swap"]), 12)
        for table in (male, female):
            self.assertEqual(len(set(table["swap"].values())), len(table["swap"]))
            self.assertTrue(table["body_template"].startswith("mo/"))
            self.assertTrue(table["scriptable"].startswith("zombie_"))

    def test_tracked_config_is_readable_by_the_runner(self):
        with open(os.path.join(HERE, "configs", "zombie_M1.json"), encoding="utf-8") as f:
            config = json.load(f)
        self.assertEqual(config["zombie"], "M1")
        self.assertIn(config["gender"], run_zombie.GENDER)
        self.assertFalse(os.path.isabs(config["ai_glb"]))
        self.assertIn("coat", config)

    def test_constant_png_is_a_valid_image_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = run_zombie.png_const(os.path.join(folder, "white.png"), (255, 255, 255, 255), size=4)
            with open(path, "rb") as f:
                data = f.read()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        position, chunks = 8, {}
        while position < len(data):
            length, kind = struct.unpack_from(">I4s", data, position)
            body = data[position + 8:position + 8 + length]
            self.assertEqual(struct.unpack_from(">I", data, position + 8 + length)[0], zlib.crc32(kind + body) & 0xFFFFFFFF)
            chunks[kind] = body
            position += 12 + length
        self.assertEqual(struct.unpack(">IIBBBBB", chunks[b"IHDR"]), (4, 4, 8, 6, 0, 0, 0))
        self.assertEqual(zlib.decompress(chunks[b"IDAT"]), (b"\0" + b"\xff" * 16) * 4)


class ScriptableClone(unittest.TestCase):
    def stream(self):
        return bytearray(b"\x08\x01\x01\x00\x00\x00\x2a" + record("zombie_male_outfit_1") + record("zmb_male_head_01")
                         + record("zmb_male_head_01_damaged") + record("zmb_male_head_01_hair_a") + b"\x09\x02\x00\x00\x00\x00\x00\x00\x00")

    def test_whole_strings_are_swapped_and_longer_strings_are_left_alone(self):
        swapped, counts = clone_scriptable.swap_all(self.stream(), {"zmb_male_head_01": "zmb_iwz_m1_head",
                                                                    "zombie_male_outfit_1": "zombie_iwz_m1"})
        self.assertEqual(counts, {"zmb_male_head_01": 1, "zombie_male_outfit_1": 1})
        self.assertEqual(clone_scriptable.strings_in(swapped),
                         {"zombie_iwz_m1", "zmb_iwz_m1_head", "zmb_male_head_01_damaged", "zmb_male_head_01_hair_a"})
        self.assertTrue(bytes(swapped).startswith(b"\x08\x01\x01\x00\x00\x00\x2a\x06\x01zombie_iwz_m1\0"))
        self.assertTrue(bytes(swapped).endswith(b"\x09\x02\x00\x00\x00\x00\x00\x00\x00"))

    def test_a_string_that_ends_a_longer_one_is_not_swapped(self):
        stream = bytearray(record("big_zmb_male_head_01") + record("zmb_male_head_01"))
        swapped, counts = clone_scriptable.swap_all(stream, {"zmb_male_head_01": "new"})
        self.assertEqual(counts, {"zmb_male_head_01": 1})
        self.assertEqual(bytes(swapped), record("big_zmb_male_head_01") + record("new"))

    def test_command_line_clones_hair_options_and_reports_a_missing_key(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target, mapping = (os.path.join(folder, name) for name in ("source", "target", "map.json"))
            with open(source, "wb") as f:
                f.write(self.stream())
            with open(mapping, "w", encoding="utf-8") as f:
                json.dump({"swap": {"zombie_male_outfit_1": "zombie_iwz_m1"}, "hair_to": "zmb_female_head_hair_nodraw",
                           "hair_prefixes": ["zmb_male_head_0"]}, f)
            command = [sys.executable, "-I", os.path.join(HERE, "clone_scriptable.py"), source, target, mapping]
            done = subprocess.run(command, capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            report = json.loads(done.stdout)
            self.assertEqual(report["swapped"], {"zombie_male_outfit_1": 1})
            self.assertEqual(report["hair_options_to_nodraw"], 1)
            with open(target, "rb") as f:
                cloned = f.read()
            self.assertEqual(clone_scriptable.strings_in(cloned),
                             {"zombie_iwz_m1", "zmb_male_head_01", "zmb_male_head_01_damaged", "zmb_female_head_hair_nodraw"})
            with open(mapping, "w", encoding="utf-8") as f:
                json.dump({"absent_name": "x"}, f)
            done = subprocess.run(command, capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 2)
            self.assertIn("MISSING", done.stdout)


if __name__ == "__main__":
    unittest.main()
