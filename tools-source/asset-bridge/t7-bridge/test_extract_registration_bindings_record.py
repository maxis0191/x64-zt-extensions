"""Authored text transport fixtures; no real capture, native or opaque IO."""
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import extract_registration_bindings_record as transport


def record(**extra):
    value = dict(schema=transport.consumer.SCHEMA, source_profile=transport.consumer.PROFILE,
                 native_source_commit=transport.NATIVE_SOURCE)
    value.update(extra)
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def log(record_bytes=None, prefix=b""):
    return b"authored diagnostic\r\n" + prefix + transport.MARKER + b" " + (record() if record_bytes is None else record_bytes) + b"\r\nfinished\r\n"


class RecordTransportTests(unittest.TestCase):
    def test_raw_slice_utf8_byte_offsets_and_line_endings(self):
        original = record(text='é { } \\" end', number=1.00)
        for newline in (b"\r\n", b"\n", b""):
            raw = "préface Ω ".encode() + transport.MARKER + b" " + original + newline
            with self.subTest(newline=newline):
                sliced, offsets = transport.extract_record(raw)
                self.assertEqual(sliced, original)
                self.assertEqual(offsets, dict(marker_byte_offset=len("préface Ω ".encode()),
                    record_byte_offset=len("préface Ω ".encode())+len(transport.MARKER)+1,
                    record_byte_length=len(original)))
                self.assertEqual(raw[offsets["record_byte_offset"]:][:offsets["record_byte_length"]], original)

    def test_absent_duplicate_and_record_embedded_marker_refuse(self):
        for raw in (b"no marker", log()+log(), log(record(text=transport.MARKER.decode())),
                    b"stray "+transport.MARKER+b"\n"+log()):
            with self.subTest(raw=raw[:80]), self.assertRaises(ValueError):
                transport.extract_record(raw)

    def test_bad_utf8_trailer_multiline_duplicate_and_nonfinite_refuse(self):
        base = record()
        for raw in (b"\xff\n"+log(), log(base+b" trailer"), log(base+b" "),
                    log(base[:-1]+b',"x":1,"x":2}'), log(base[:-1]+b',"nested":{"x":1,"x":2}}'),
                    log(base[:-1]+b',"x":NaN}'), log(base[:-1]+b',"x":Infinity}'),
                    log(base[:-1]+b',\n"x":1}'), log(b"[]"), log(base+b"{}")):
            with self.subTest(raw=raw[-90:]), self.assertRaises(ValueError):
                transport.extract_record(raw)

    def test_exact_identity_types_and_depth_bound(self):
        for key in ("schema", "source_profile", "native_source_commit"):
            for value in (None, True, 1, [], "wrong"):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    transport.extract_record(log(record(**{key: value})))
        nested = []
        for _ in range(23): nested = [nested]
        transport.extract_record(log(record(nested=nested)))  # Root + 24 arrays = 25.
        with self.assertRaises(ValueError): transport.extract_record(log(record(nested=[nested])))

    def test_exact_record_and_log_size_boundaries(self):
        empty = record(padding="")
        exact = record(padding="x"*(transport.RECORD_LIMIT-len(empty)))
        self.assertEqual(len(exact), transport.RECORD_LIMIT)
        self.assertEqual(transport.extract_record(log(exact))[0], exact)
        with self.assertRaises(ValueError): transport.extract_record(log(exact[:-1]+b" }"))
        raw = log()
        exact_log = b"x"*(transport.LOG_LIMIT-len(raw))+raw
        transport.extract_record(exact_log)
        for bad in (exact_log+b"x", b"", "text", bytearray(raw)):
            with self.subTest(kind=type(bad).__name__), self.assertRaises(ValueError): transport.extract_record(bad)

    def paths(self, root, raw=None):
        source = root/"stdout.log"; source.write_bytes(log() if raw is None else raw)
        return source, root/"bindings.json", root/"transport.json"

    def run_transport(self, paths, **changes):
        source, output, manifest = paths; raw = source.read_bytes()
        args = dict(log=source, log_bytes=len(raw), log_sha256=transport.sha(raw),
                    output=output, manifest=manifest, native_exit_code=0)
        args.update(changes)
        return transport.materialize(**args)

    def test_materialization_keeps_exact_bytes_and_separate_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            raw_record = record(text="Ω", untouched=1.50)
            raw = log(raw_record, "é ".encode()); paths = self.paths(Path(folder), raw)
            result = self.run_transport(paths, native_exit_code=7)
            source, output, manifest = paths
            self.assertEqual(source.read_bytes(), raw)
            self.assertEqual(output.read_bytes(), raw_record)
            self.assertEqual(json.loads(manifest.read_bytes()), result)
            self.assertEqual(result["origin_log"], dict(Path=str(source), Bytes=len(raw), SHA256=transport.sha(raw)))
            self.assertEqual(result["record"], dict(Path=str(output), Bytes=len(raw_record), SHA256=transport.sha(raw_record)))
            self.assertEqual(result["extractor_source"]["SHA256"], transport.sha(Path(transport.__file__).read_bytes()))
            self.assertEqual(result["native_exit_code"], 7)
            self.assertTrue(result["transport_only"])
            self.assertFalse(result["semantic_validation_performed"]); self.assertFalse(result["ready"])
            # This valid transport deliberately lacks the DTO; unchanged reader must refuse it.
            with self.assertRaises(ValueError): transport.consumer.classify(json.loads(output.read_bytes()), 7)

    def test_pin_and_exit_types_refuse_before_open(self):
        for changes in (dict(log_bytes=True), dict(log_bytes=0), dict(log_bytes=transport.LOG_LIMIT+1),
                        dict(log_sha256="A"*64), dict(log_sha256=None), dict(native_exit_code=True),
                        dict(native_exit_code="0"), dict(native_exit_code=2**32), dict(native_exit_code=-2**31-1)):
            with self.subTest(changes=changes), patch.object(Path, "open", side_effect=AssertionError("opened")), self.assertRaises(ValueError):
                transport.materialize(Path.cwd()/"stdout.log", changes.get("log_bytes", 1), changes.get("log_sha256", "a"*64),
                    Path.cwd()/"out.json", Path.cwd()/"provenance.json", changes.get("native_exit_code", 0))

    def test_lexical_opaque_device_ads_reserved_relative_refuse_before_metadata(self):
        for path in ("relative.json", r"C:drive.json", r"\\?\C:\a.json", r"\\.\C:\a.json",
                     r"C:\a.json:stream", r"C:\CON\a.json", r"C:\NUL.json", str(Path.cwd()/"a.exe"),
                     str(Path.cwd()/"a.pdb"), str(Path.cwd()/"a.ff"), str(Path.cwd()/"a.xpak")):
            with self.subTest(path=path), patch.object(Path, "lstat", side_effect=AssertionError("metadata")), \
                 patch.object(Path, "open", side_effect=AssertionError("opened")), self.assertRaises(ValueError):
                transport.ordinary_path(path, ".json")

    def test_reparse_leaf_and_ancestor_refuse_before_open(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/"report.json"; real_lstat = Path.lstat
            for entry in (target, target.parent):
                def lstat(path, *args, **kwargs):
                    if path == entry: return SimpleNamespace(st_mode=0o100644, st_file_attributes=0x400)
                    return real_lstat(path, *args, **kwargs)
                with self.subTest(entry=entry), patch.object(Path, "lstat", lstat), \
                     patch.object(Path, "open", side_effect=AssertionError("opened")), self.assertRaises(ValueError):
                    transport.ordinary_path(target, ".json")

    def test_existing_outputs_overlap_missing_parent_and_wrong_log_name_refuse(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = self.paths(Path(folder)); before = paths[0].read_bytes()
            for target in paths[1:]:
                target.write_bytes(b"keep")
                with self.assertRaises(ValueError): self.run_transport(paths)
                self.assertEqual(target.read_bytes(), b"keep"); target.unlink()
            for changes in (dict(manifest=paths[1]), dict(output=Path(folder)/"absent"/"out.json")):
                with self.subTest(changes=changes), self.assertRaises(ValueError): self.run_transport(paths, **changes)
            renamed = Path(folder)/"different.log"; renamed.write_bytes(before)
            with self.assertRaises(ValueError): self.run_transport((renamed, *paths[1:]))
            self.assertEqual(paths[0].read_bytes(), before)

    def test_wrong_pinned_size_hash_and_directory_refuse(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = self.paths(Path(folder))
            for changes in (dict(log_bytes=1), dict(log_sha256="0"*64)):
                with self.subTest(changes=changes), self.assertRaises(ValueError): self.run_transport(paths, **changes)
                self.assertFalse(paths[1].exists()); self.assertFalse(paths[2].exists())
            paths[0].unlink(); paths[0].mkdir()
            with self.assertRaises(ValueError):
                transport.materialize(paths[0], paths[0].stat().st_size, "0"*64, *paths[1:], 0)

    def test_create_new_race_and_flush_failure_preserve_existing_or_partial_output(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = self.paths(Path(folder)); write = transport.write_new_verified
            @contextmanager
            def race(path, raw):
                path.write_bytes(b"racing-owner")
                with write(path, raw) as held: yield held
            with patch.object(transport, "write_new_verified", side_effect=race), self.assertRaises(FileExistsError): self.run_transport(paths)
            self.assertEqual(paths[1].read_bytes(), b"racing-owner"); self.assertFalse(paths[2].exists())
            paths[1].unlink()
            with patch.object(transport.os, "fsync", side_effect=OSError("authored flush failure")), self.assertRaises(OSError): self.run_transport(paths)
            self.assertEqual(paths[1].read_bytes(), record()); self.assertFalse(paths[2].exists())

    def test_readback_mismatch_refuses(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"authored.json"
            with patch.object(transport, "verify_new_output", side_effect=ValueError("authored readback mismatch")), self.assertRaises(ValueError):
                with transport.write_new_verified(path, b"original"): self.fail("yielded before readback")
            self.assertEqual(path.read_bytes(), b"original")
            # Exercise the real readback mismatch, using an existing held stream.
            with path.open("r+b") as stream, self.assertRaisesRegex(ValueError, "readback"):
                transport.verify_new_output(path, stream, transport.os.fstat(stream.fileno()), b"different")

    def test_input_mutation_or_leaf_identity_change_never_reports_success(self):
        for replace in (False, True):
            with self.subTest(replace=replace), tempfile.TemporaryDirectory() as folder:
                paths = self.paths(Path(folder)); write = transport.write_new_verified; original = paths[0].read_bytes()
                changed = False; real_lstat = Path.lstat
                def lstat(path, *args, **kwargs):
                    info = real_lstat(path, *args, **kwargs)
                    if changed and path == paths[0]:
                        return SimpleNamespace(st_dev=info.st_dev, st_ino=info.st_ino+1, st_size=info.st_size)
                    return info
                @contextmanager
                def mutate(path, raw):
                    nonlocal changed
                    with write(path, raw) as held:
                        if path == paths[1]:
                            if replace: changed = True
                            else: paths[0].write_bytes(original.replace(b"finished", b"modified"))
                        yield held
                with patch.object(Path, "lstat", lstat), patch.object(transport, "write_new_verified", side_effect=mutate), self.assertRaises(ValueError): self.run_transport(paths)
                self.assertEqual(paths[1].read_bytes(), record())
                if not replace: self.assertFalse(paths[2].exists())
                else: self.assertEqual(paths[0].read_bytes(), original)

    def test_output_or_provenance_mutated_during_publication_refuses(self):
        for index in (1, 2):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as folder:
                paths = self.paths(Path(folder)); original = paths[0].read_bytes(); write = transport.write_new_verified
                @contextmanager
                def mutate(path, raw):
                    with write(path, raw) as held:
                        if path == paths[2]:
                            target = paths[index]; existing = target.read_bytes()
                            target.write_bytes(b"x"+existing[1:])  # Same length; after manifest initial readback.
                        yield held
                with patch.object(transport, "write_new_verified", side_effect=mutate), self.assertRaisesRegex(ValueError, "readback"):
                    self.run_transport(paths)
                self.assertEqual(paths[0].read_bytes(), original)
                self.assertTrue(paths[1].exists()); self.assertTrue(paths[2].exists())

    def test_new_output_leaf_identity_and_reparse_change_refuse(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"authored.json"
            with path.open("x+b") as stream:
                stream.write(b"original"); stream.flush(); opened = transport.os.fstat(stream.fileno())
                changed = SimpleNamespace(st_mode=opened.st_mode, st_dev=opened.st_dev, st_ino=opened.st_ino+1,
                    st_size=opened.st_size, st_file_attributes=0)
                real_lstat = Path.lstat
                def lstat(entry, *args, **kwargs): return changed if entry == path else real_lstat(entry, *args, **kwargs)
                with patch.object(Path, "lstat", lstat), self.assertRaisesRegex(ValueError, "identity"):
                    transport.verify_new_output(path, stream, opened, b"original")
                changed.st_file_attributes = 0x400
                with patch.object(Path, "lstat", lstat), self.assertRaisesRegex(ValueError, "reparse"):
                    transport.verify_new_output(path, stream, opened, b"original")

    def test_cli_authored_record_then_unchanged_consumer(self):
        import test_registration_bindings_consumer as authored
        with tempfile.TemporaryDirectory() as folder:
            raw_record = json.dumps(authored.report(), separators=(",", ":")).encode()
            paths = self.paths(Path(folder), log(raw_record)); original = paths[0].read_bytes()
            command = [sys.executable, "-B", str(Path(transport.__file__)), "--log", str(paths[0]),
                "--log-bytes", str(len(original)), "--log-sha256", transport.sha(original),
                "--output-json", str(paths[1]), "--provenance-json", str(paths[2]), "--native-exit-code", "0"]
            extracted = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(extracted.returncode, 0, extracted.stderr)
            consumed = subprocess.run([sys.executable, "-B", str(Path(transport.consumer.__file__)), str(paths[1]),
                                      "--native-exit-code", "0"], capture_output=True, text=True)
            self.assertEqual(consumed.returncode, 0, consumed.stderr)
            result = json.loads(consumed.stdout)
            self.assertEqual(result["outcome"], "RegistrationBindingsObserved")
            self.assertFalse(result["ready"]); self.assertEqual(result["payload_bytes_read"], 0)
            self.assertEqual(paths[0].read_bytes(), original); self.assertEqual(paths[1].read_bytes(), raw_record)


if __name__ == "__main__":
    unittest.main()
