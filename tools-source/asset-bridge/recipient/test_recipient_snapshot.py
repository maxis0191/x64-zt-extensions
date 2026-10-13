"""Generated ScriptFile/text snapshots only; no retail bytes or native process."""
import csv
import hashlib
import io
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock

import recipient_contract as c


class TrackedReader:
    def __init__(self, raw, *, chunk=None, first_read=None):
        self.raw, self.chunk, self.first_read = raw, chunk, first_read
        self.requests, self.bytes_read = [], 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.raw.close()

    def fileno(self):
        return self.raw.fileno()

    def read(self, count):
        self.requests.append(count)
        if self.first_read:
            action, self.first_read = self.first_read, None
            action()
        data = self.raw.read(min(count, self.chunk) if self.chunk else count)
        self.bytes_read += len(data)
        return data


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)
        self.path = self.work / c.SCRIPT_PATH
        self.path.parent.mkdir(parents=True)
        self.data = c.MODULE.encode() + b'\0' + struct.pack('<iii', 3, 100, 2) + b'abcXY'
        self.path.write_bytes(self.data)
        self.real_open = Path.open

    def tearDown(self):
        self.temp.cleanup()

    def manifest(self, digest=None):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['donor_map', 'pack_name', 'module', 'status', 'path', 'size_bytes', 'sha256'])
        writer.writerow(['cp_zmb', c.PACK, c.MODULE, 'dumped', c.SCRIPT_PATH, len(self.data),
                         digest or hashlib.sha256(self.data).hexdigest()])
        return output.getvalue()

    def test_script_header_and_digest_use_one_descriptor_with_short_reads(self):
        tracked = []
        def opener(path, *args, **kwargs):
            self.assertEqual(path, self.path)
            self.assertEqual(kwargs.get('buffering'), 0)
            stream = TrackedReader(self.real_open(path, *args, **kwargs), chunk=2)
            tracked.append(stream)
            return stream
        with mock.patch.object(Path, 'open', opener):
            result = c.script_result(self.work, self.manifest())
        self.assertEqual(len(tracked), 1)
        self.assertEqual(tracked[0].bytes_read, len(self.data))
        self.assertEqual(result['sha256'], hashlib.sha256(self.data).hexdigest())
        self.assertGreater(len(tracked[0].requests), 2)

    def test_script_growth_stops_at_declared_size_plus_one(self):
        tracked = []
        def append():
            with self.real_open(self.path, 'ab', buffering=0) as writer:
                writer.write(b'x'*100000)
        def opener(path, *args, **kwargs):
            stream = TrackedReader(self.real_open(path, *args, **kwargs), first_read=append)
            tracked.append(stream)
            return stream
        with mock.patch.object(Path, 'open', opener), self.assertRaisesRegex(ValueError, 'grew'):
            c.script_result(self.work, self.manifest())
        self.assertEqual(len(tracked), 1)
        self.assertEqual(tracked[0].bytes_read, len(self.data)+1)
        self.assertEqual(tracked[0].requests[-1], 1)

    def test_script_shrink_is_not_a_valid_short_payload(self):
        def shrink():
            with self.real_open(self.path, 'r+b', buffering=0) as writer:
                writer.truncate(35)
        def opener(path, *args, **kwargs):
            return TrackedReader(self.real_open(path, *args, **kwargs), first_read=shrink)
        with mock.patch.object(Path, 'open', opener), self.assertRaisesRegex(ValueError, 'payload'):
            c.script_result(self.work, self.manifest())

    def test_later_open_cannot_supply_a_different_digest(self):
        alternate = self.data.replace(b'utility', b'wronggg')
        alt = self.work/'alternate.bin'
        alt.write_bytes(alternate)
        opened = []
        def opener(path, *args, **kwargs):
            opened.append(path)
            return self.real_open(self.path if len(opened) == 1 else alt, *args, **kwargs)
        with mock.patch.object(Path, 'open', opener), self.assertRaisesRegex(ValueError, 'hash differs'):
            c.script_result(self.work, self.manifest(hashlib.sha256(alternate).hexdigest()))
        self.assertEqual(opened, [self.path])

    def test_script_identity_size_and_timestamps_must_stay_stable(self):
        with self.real_open(self.path, 'rb') as stream:
            before = c.file_state(stream)
        for index in range(len(before)):
            changed = list(before)
            changed[index] += 1
            with self.subTest(index=index), mock.patch.object(c, 'file_state', side_effect=[before, tuple(changed)]):
                with self.assertRaisesRegex(ValueError, 'identity/metadata changed'):
                    c.script_result(self.work, self.manifest())

    def test_payload_larger_than_native_max_refuses_before_any_read(self):
        with self.real_open(self.path, 'rb') as stream:
            info = list(c.file_state(stream))
        info[2] = c.MAX_SCRIPT+1
        manifest = self.manifest().replace(f',{len(self.data)},', f',{info[2]},')
        tracked = []
        def opener(path, *args, **kwargs):
            stream = TrackedReader(self.real_open(path, *args, **kwargs))
            tracked.append(stream)
            return stream
        with mock.patch.object(Path, 'open', opener), mock.patch.object(c, 'file_state', return_value=tuple(info)):
            with self.assertRaisesRegex(ValueError, 'byte size'):
                c.script_result(self.work, manifest)
        self.assertEqual(len(tracked), 1)
        self.assertEqual(tracked[0].requests, [])

    def test_manifest_text_and_digest_use_same_bytes_without_reopen(self):
        manifest_path = self.work/'dump'/c.PACK/'scriptfile-manifest.csv'
        raw = self.manifest().encode()
        manifest_path.write_bytes(raw)
        opened = []
        def opener(path, *args, **kwargs):
            opened.append(path)
            return self.real_open(path, *args, **kwargs)
        with mock.patch.object(Path, 'open', opener):
            result = c.check_output('script', self.work)
        self.assertEqual(opened, [manifest_path, self.path])
        self.assertEqual(result['manifest_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertFalse(result['closure_complete'])
        self.assertFalse(result['package_ready'])

    def test_text_growth_uses_only_limit_plus_one_bytes(self):
        path = self.work/'text.csv'
        path.write_bytes(b'a'*16)
        tracked = []
        def append():
            with self.real_open(path, 'ab', buffering=0) as writer:
                writer.write(b'b'*100000)
        def opener(name, *args, **kwargs):
            stream = TrackedReader(self.real_open(name, *args, **kwargs), first_read=append)
            tracked.append(stream)
            return stream
        with mock.patch.object(Path, 'open', opener), self.assertRaisesRegex(ValueError, 'fixed recipient bound'):
            c.text_snapshot(path, 16)
        self.assertEqual(tracked[0].bytes_read, 17)

    def test_exact_text_bound_and_utf8_bom_hash(self):
        path = self.work/'text.csv'
        raw = b'\xef\xbb\xbfvalue'
        path.write_bytes(raw)
        value, digest = c.text_snapshot(path, len(raw))
        self.assertEqual(value, 'value')
        self.assertEqual(digest, hashlib.sha256(raw).hexdigest())
        with self.assertRaises(ValueError):
            c.text_snapshot(path, len(raw)-1)

    def test_text_identity_change_refuses(self):
        path = self.work/'text.csv'
        path.write_bytes(b'abc')
        with self.real_open(path, 'rb') as stream:
            before = c.file_state(stream)
        changed = list(before)
        changed[1] += 1
        with mock.patch.object(c, 'file_state', side_effect=[before, tuple(changed)]):
            with self.assertRaisesRegex(ValueError, 'changed during snapshot'):
                c.text_snapshot(path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
