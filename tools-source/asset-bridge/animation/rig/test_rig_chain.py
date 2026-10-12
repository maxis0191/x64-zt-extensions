"""Plan and independent-read refusals using original synthetic data only."""
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest

from plan_rig_chain import (CANDIDATE_SHA, JOB_SHA, PROVIDERS, ZONE, check_base,
                            compose, expected_inventory, fresh_root, inventory, load_json, pinned)
from read_rig_chain import load_pairs, reader_refusal, verify_chain
from test_clip_rig import clip_bytes, meta
from test_skin_native import surface_offsets, synthetic


def base_plan():
    rows = [{"Relative": "main/fileSysCheck.cfg", "Mode": "Copy", "Bytes": 77}]
    rows += [{"Relative": "original_test_" + str(i), "Mode": "HardLink", "Bytes": 1} for i in range(71)]
    return {"Schema": "iw7.animation-ff-plan/2", "Zone": "sdk_animation_probe", "Ready": False, "FFBuilt": False,
            "Bindings": {name: {"Path": "/original-test/" + name, "SHA256": digest} for name, digest in PROVIDERS.items()},
            "Candidate": {"SHA256": CANDIDATE_SHA, "Path": "/original-test/zonetool.exe"}, "JobSourceSHA256": JOB_SHA, "JobSource": "/original-test/BuildJob.cs",
            "PhysicalBytes": 8 * 1024**3, "CommitBytes": 11 * 1024**3, "StockInputs": rows, "StagingCopyBytes": 77,
            "StockContentAndIdentityRecheckPending": True, "PythonExe": "/original-test/python.exe", "NativeInput": "/original-test/probe.xab"}


def data():
    a, b, files = synthetic("first")
    c, d, _ = synthetic("second")
    return files, meta(files), {"first": (a, b), "second": (c, d)}


def inventory_log(rows=None):
    rows = expected_inventory() if rows is None else rows
    return 'Loading zone "' + ZONE + '"\n' + "\n".join('Loading asset "' + row.split(',', 1)[1] + '" of type ' + row.split(',', 1)[0] + '.' for row in rows)


class RigChainDataTests(unittest.TestCase):
    def test_complete_native_and_ff_read_plus_actual_stream_oracle(self):
        files, manifest, pairs = data()
        result = verify_chain(files, manifest, pairs, clip_bytes(), pairs, clip_bytes(4036))
        self.assertEqual(result["status"], "rig-chain-data-pass")
        for stage in (result["native"], result["redump"]):
            self.assertTrue(stage["complete_model_surface_read"])
            self.assertEqual(stage["clip_rig_cpu"]["channel_to_bone"], [0, 1])
            for h in ("first", "second"):
                self.assertEqual(stage["models"][h]["actual_blend_sha256"], hashlib.sha256(files[h + '.blend.u16.bin']).hexdigest())
        for key in ("native_execution_verified", "ff_execution_verified", "stock_restoration_verified", "material_resolution_verified", "engine_weight_direction_verified", "runtime_verified", "ready"):
            self.assertIs(result[key], False)

    def test_native_only_has_no_implied_ff_proof(self):
        files, manifest, pairs = data()
        result = verify_chain(files, manifest, pairs, clip_bytes())
        self.assertEqual(result["status"], "rig-native-data-pass")
        self.assertIsNone(result["redump"])

    def test_half_redump_request_and_missing_profile_refused(self):
        files, manifest, pairs = data()
        with self.assertRaisesRegex(ValueError, "together"):
            verify_chain(files, manifest, pairs, clip_bytes(), pairs)
        with self.assertRaisesRegex(ValueError, "both distinct"):
            verify_chain(files, manifest, {"first": pairs["first"]}, clip_bytes())

    def test_redump_surface_corruption_is_not_replaced_by_source_inputs(self):
        files, manifest, pairs = data()
        corrupt = dict(pairs)
        xmb, xsb = pairs["second"]
        corrupt["second"] = (xmb, xsb + b"\0")
        with self.assertRaisesRegex(ValueError, "trailing"):
            verify_chain(files, manifest, pairs, clip_bytes(), corrupt, clip_bytes(4036))

    def test_one_bone_model_and_swapped_profile_are_rejected(self):
        files, manifest, pairs = data()
        xmb = bytearray(pairs["first"][0])
        xmb[6 + 20] = 1
        for bad in ({**pairs, "first": (bytes(xmb), pairs["first"][1])}, {"first": pairs["second"], "second": pairs["first"]}):
            with self.assertRaises(ValueError):
                verify_chain(files, manifest, bad, clip_bytes())

    def test_material_replacement_and_changed_note_refused(self):
        files, manifest, pairs = data()
        xmb, xsb = pairs["first"]
        bad = {**pairs, "first": (xmb.replace(b"clown", b"other"), xsb)}
        with self.assertRaises(ValueError):
            verify_chain(files, manifest, bad, clip_bytes())
        with self.assertRaises(ValueError):
            verify_chain(files, manifest, pairs, clip_bytes(), pairs, clip_bytes(4036).replace(b"probe_contact", b"other_contact"))

    def test_actual_split_writer_paths_and_flat_redump_paths(self):
        files, manifest, pairs = data()
        from read_rig_chain import MODELS
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for split in (True, False):
                base = root / str(split)
                for h, model in MODELS.items():
                    target = base / h if split else base
                    (target / 'xmodel').mkdir(parents=True, exist_ok=True)
                    (target / 'xsurface').mkdir(exist_ok=True)
                    (target / 'xmodel' / (model + '.xmb')).write_bytes(pairs[h][0])
                    (target / 'xsurface' / (model + '_lod0.xsb')).write_bytes(pairs[h][1])
                self.assertEqual(load_pairs(base, split_profiles=split), pairs)


    def test_loaded_model_pointer_still_refused_with_redacted_context(self):
        files, manifest, pairs = data()
        value = 0x123456789ABCDEF0
        for profile in ("first", "second"):
            bad = dict(pairs)
            model = bytearray(pairs[profile][0])
            struct.pack_into("<Q", model, 6 + 272, value)
            bad[profile] = bytes(model), pairs[profile][1]
            original = dict(bad)
            with self.assertRaises(ValueError) as error:
                verify_chain(files, manifest, pairs, clip_bytes(), bad, clip_bytes(4036))
            message = str(error.exception)
            self.assertIn(f"ff-redump/{profile}/xmodel: unexpected native field", message)
            self.assertIn("XModel.lodInfo[0].surfs offset=272 category=nonzero-8-byte-value", message)
            self.assertIn("address omitted", message)
            self.assertNotIn(str(value), message)
            self.assertNotIn(hex(value)[2:], message.lower())
            self.assertLess(len(message), 320)
            self.assertEqual(bad, original)

    def test_surface_field_still_refused_for_native_and_ff_with_no_address(self):
        files, manifest, pairs = data()
        value = 0x7ABCDEF123456789
        bad = dict(pairs)
        surface = bytearray(pairs["first"][1])
        offset = surface_offsets(surface)[0]
        struct.pack_into("<Q", surface, offset + 88, value)
        bad["first"] = pairs["first"][0], bytes(surface)
        for ff in (False, True):
            with self.assertRaises(ValueError) as error:
                verify_chain(files, manifest, pairs if ff else bad, clip_bytes(),
                             bad if ff else None, clip_bytes(4036) if ff else None)
            message = str(error.exception)
            self.assertIn(("ff-redump" if ff else "native-data") + "/first/xsurface", message)
            self.assertIn("blendVertsBuffer (header name) offset=88 category=nonzero-8-byte-value", message)
            self.assertNotIn(str(value), message)
            self.assertNotIn(hex(value)[2:], message.lower())
            self.assertLess(len(message), 320)
        self.assertEqual(bytes(surface), bad["first"][1])

    def test_other_unsupported_field_is_not_mislabeled_as_loaded_field(self):
        files, manifest, pairs = data()
        surface = bytearray(pairs["first"][1])
        struct.pack_into("<Q", surface, surface_offsets(surface)[0] + 48, 1234)
        bad = {**pairs, "first": (pairs["first"][0], bytes(surface))}
        with self.assertRaises(ValueError) as error:
            verify_chain(files, manifest, bad, clip_bytes())
        self.assertIn("native-data/first/xsurface: unexpected native field", str(error.exception))
        self.assertNotIn("observed", str(error.exception))
        self.assertNotIn("offset=88", str(error.exception))

    def test_truncated_diagnostic_framing_preserves_original_refusal(self):
        error = ValueError("unexpected native field/padding/dependency")
        for kind in ("xmodel", "xsurface"):
            message = str(reader_refusal(error, b"\x08\x01", kind, "first", "ff-redump"))
            self.assertEqual(message, f"ff-redump/first/{kind}: {error}")


class RigChainPlanTests(unittest.TestCase):
    def plan(self):
        root = Path(__file__).absolute().parent
        compiler = {"Compiler": str(root / 'tools/bin/Hostx64/x64/cl.exe'), "WindowsSdk": "10.0.test", "CompilerSHA256": "0" * 64, "VCTools": "test"}
        return compose(base_plan(), root / 'future', root / 'inputs', root / 'prepared', root / 'source', compiler, root / 'sdk', root)

    def test_plan_has_both_real_writer_profiles_and_sequential_groups(self):
        plan = self.plan()
        self.assertEqual([p['id'] for p in plan['phases']], ['compile', 'emit-first', 'emit-second', 'read-native', 'build', 'verify', 'dump', 'read-ff'])
        self.assertEqual([p['group'] for p in plan['phases']], ['native'] * 4 + ['ff'] * 4)
        self.assertFalse(plan['executor_integration_pending'])
        self.assertTrue(plan['executor_native_validation_pending'])
        self.assertFalse(plan['compiled'])
        self.assertFalse(plan['ff_built'])
        self.assertFalse(plan['ready'])
        self.assertEqual(plan['phases'][1]['command'][-1], 'first')
        self.assertEqual(plan['phases'][2]['command'][-1], 'second')
        self.assertEqual(len(plan['expected_inventory']), 7)
        self.assertEqual(plan['total_ff_staged_entries'], 79)
        self.assertEqual(len(plan['staged_profile_inputs']), 7)
        self.assertEqual(len(plan['retain_redumps_before_restore']), 5)
        self.assertTrue(all(p['working_directory'] for p in plan['phases']))
        self.assertNotIn('netconststrings', plan['zone_csv'])
        self.assertNotIn('paris_model_probe', plan['zone_csv'])
        self.assertEqual(plan['limits']['ff_physical_bytes'], 8 * 1024**3)

    def test_changed_provider_candidate_or_job_refused(self):
        for field in ('provider', 'candidate', 'job'):
            base = base_plan()
            if field == 'provider':
                next(iter(base['Bindings'].values()))['SHA256'] = '0' * 64
            elif field == 'candidate':
                base['Candidate']['SHA256'] = '0' * 64
            else:
                base['JobSourceSHA256'] = '0' * 64
            with self.assertRaises(ValueError): check_base(base)

    def test_stock_modes_duplicate_and_reduced_budget_refused(self):
        for mutate in (lambda b: b.update(PhysicalBytes=1),
                       lambda b: b['StockInputs'][1].update(Relative='MAIN/FILESYSCHECK.CFG'),
                       lambda b: b['StockInputs'][1].update(Mode='Copy'),
                       lambda b: b.update(StockContentAndIdentityRecheckPending=False)):
            base = base_plan()
            mutate(base)
            with self.assertRaises(ValueError): check_base(base)

    def test_exact_inventory_and_remapped_row_order(self):
        self.assertEqual(set(inventory(inventory_log())), set(expected_inventory()))
        self.assertEqual(set(inventory(inventory_log(list(reversed(expected_inventory()))))), set(expected_inventory()))

    def test_inventory_extra_duplicate_wrong_zone_or_error_refused(self):
        expected = expected_inventory()
        for log in (inventory_log(expected + ['xmodel,unexpected']), inventory_log(expected[:-1] + [expected[0]]),
                    inventory_log().replace(ZONE, 'sdk_beacon'), inventory_log() + '\n[ ERROR ] unresolved',
                    inventory_log().replace('Loading asset ', 'prefix Loading asset ', 1)):
            with self.assertRaises(ValueError): inventory(log)

    def test_fresh_root_containment_and_no_directory_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            fresh_root(root / 'runtime/new', root / 'runtime')
            self.assertFalse((root / 'runtime').exists())
            for bad in (root / 'outside', root / 'runtime', root / 'runtime/../escape'):
                with self.assertRaises(ValueError): fresh_root(bad, root / 'runtime')
            (root / 'runtime/existing').mkdir(parents=True)
            with self.assertRaises(ValueError): fresh_root(root / 'runtime/existing', root / 'runtime')

    def test_pins_and_duplicate_receipt_json_are_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / 'manifest.json'
            file.write_bytes(b'{"a":1,"a":2}')
            with self.assertRaisesRegex(ValueError, 'duplicate'): load_json(file)
            file.write_bytes(b'{"x": false}')
            digest = hashlib.sha256(file.read_bytes()).hexdigest()
            self.assertEqual(load_json(file, digest), {'x': False})
            with self.assertRaises(ValueError): pinned(file, '0' * 64)
            with self.assertRaises(ValueError): pinned(file, digest, 1)


if __name__ == '__main__':
    unittest.main()
