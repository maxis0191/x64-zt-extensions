import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from prepare_ff import stage, PIN, MATERIAL


def fixture(root):
    run = root / "writer"
    run.mkdir()
    source = {"schema": "iw7.doom-rigid-writer-source/1", "source_pin": PIN,
              "candidate_name": "paris_doom_helmet_rigid_a", "material_reference": MATERIAL,
              "metrics": {"vertices": 3, "triangles": 1, "height_engine_units": 16,
                          "engine_units_per_metre": 16, "radius_engine": 12}}
    (run / "writer-source.json").write_text(json.dumps(source))
    (run / "doom-writer.exe").write_bytes(b"synthetic reader; never executed")
    artifacts = []
    for name in ("xmodel/paris_doom_helmet_rigid_a.xmb", "xsurface/paris_doom_helmet_rigid_a_lod0.xsb"):
        path = run / "artifacts" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic asset; not a model")
        artifacts.append({"Path": name, "Bytes": path.stat().st_size, "SHA256": hashlib.sha256(path.read_bytes()).hexdigest()})
    value = {"Schema": "iw7.doom-rigid-writer-build/1", "SourcePin": PIN, "Source": source,
             "InputSnapshotsMatch": True, "SourceManifestSHA256": hashlib.sha256((run / "writer-source.json").read_bytes()).hexdigest(),
             "WriterSHA256": hashlib.sha256((run / "doom-writer.exe").read_bytes()).hexdigest(), "Artifacts": artifacts,
             "FFBuilt": False, "PixelsVerified": False, "Ready": False,
             "Roundtrip": {"schema": "iw7.doom-rigid-roundtrip/1", "vertices": 3, "triangles": 1,
                           "bones": 1, "surfaces": 1, "lods": 1, "lod0_dist": 1000000, "has_lods": True,
                           "shadow_cutoff_lod": 6, "collision_lod": 255, "geometry_roundtrip_verified": True,
                           "ready": False, "pixels_verified": False, "ff_built": False,
                           "iw7_normal_encoding_verified": False}}
    (run / "writer-provenance.json").write_text(json.dumps(value))
    return run, value


class FFSourceTests(unittest.TestCase):
    def test_minimal_reference_inventory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            run, _ = fixture(root)
            plan = stage(run, root / "ff")
            self.assertEqual(len(plan["source_files"]), 5)
            self.assertEqual(plan["zone"], "paris_enemy_doom_helmet_rigid_a")
            self.assertFalse(plan["material_payload_copied"])
            self.assertFalse(plan["ready"])
            self.assertIn("material,,"+MATERIAL, plan["expected_inventory"])
            self.assertEqual(plan["metrics"]["vertices"], 3)
            self.assertEqual((root / "ff" / "zone_source" / (plan["zone"]+"_recipient.csv")).read_text(), "material,"+MATERIAL+"\n")
            with self.assertRaises(ValueError):
                stage(run, root / "ff")

    def test_mutated_asset_and_reader_refused_before_output(self):
        for relative in ("artifacts/xmodel/paris_doom_helmet_rigid_a.xmb", "doom-writer.exe", "writer-source.json"):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                run, _ = fixture(root)
                path = run / relative
                path.write_bytes(path.read_bytes()+b" ")
                with self.assertRaises(ValueError):
                    stage(run, root / "ff")
                self.assertFalse((root / "ff").exists())

    def test_counts_and_acceptance_claims_refused(self):
        for mutation in (lambda v: v["Roundtrip"].update(vertices=4),
                         lambda v: v["Roundtrip"].update(vertices=True),
                         lambda v: v.update(InputSnapshotsMatch=False),
                         lambda v: v.update(Ready=True),
                         lambda v: v["Roundtrip"].update(pixels_verified=True),
                         lambda v: v["Roundtrip"].update(iw7_normal_encoding_verified=True),
                         lambda v: v["Source"].update(candidate_name="../paris_doom_bad")):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                run, value = fixture(root)
                mutation(value)
                (run / "writer-provenance.json").write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    stage(run, root / "ff")
                self.assertFalse((root / "ff").exists())


if __name__ == "__main__":
    unittest.main()
