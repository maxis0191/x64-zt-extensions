"""Original synthetic fixtures only; no retail data, engine or native compilation."""
import contextlib
import io
import json
from pathlib import Path
import random
import struct
import tempfile
import unittest

import blend_bridge as bridge


def meta(counts=(1, 1, 1, 1, 0, 0, 0, 0), bones=4):
    return {"schema": bridge.SCHEMA, "blend_vert_counts": list(counts),
            "vertex_count": sum(counts), "bone_count": bones, "rigid_vert_list_count": 0}


# Literal independent examples for each group. Weights deliberately include
# >255 values: this tool preserves uint16 words, it does not infer normalization.
H1 = bytes.fromhex("c000 0000 4000 ffff 0000 4000 3412 8000 cdab 0000 4000 0100 8000 0200 c000 0300")
IW7 = bytes.fromhex("0300 0000 0000 0100 ffff 0000 0000 0100 3412 0200 cdab 0000 0000 0100 0100 0200 0200 0300 0300 0000")


class BlendTests(unittest.TestCase):
    def test_literal_all_supported_groups(self):
        result = bridge.convert_h1(H1, meta())
        self.assertEqual(result, IW7)
        self.assertEqual(bridge.inspect_iw7(result, meta()), [
            {"bones": [3], "weight_words": []}, {"bones": [0, 1], "weight_words": [65535]},
            {"bones": [0, 1, 2], "weight_words": [4660, 43981]},
            {"bones": [0, 1, 2, 3], "weight_words": [1, 2, 3]}])
        receipt = bridge.verify_correspondence(H1, result, meta())
        self.assertEqual((receipt["h1_bytes"], receipt["iw7_bytes"]), (32, 40))
        self.assertFalse(receipt["weight_direction_engine_verified"])
        self.assertFalse(receipt["xsb_emitted"])

    def test_five_to_eight_never_silently_skip(self):
        for group in range(4, 8):
            with self.subTest(group=group + 1):
                counts = [0] * 8
                counts[group] = 1
                with self.assertRaisesRegex(ValueError, "5..8"):
                    bridge.convert_h1(b"\0" * ((2 * group + 1) * 2), meta(counts))

    def test_metadata_refusals(self):
        mutations = [lambda m: m.update(vertex_count=3), lambda m: m.update(vertex_count=True),
                     lambda m: m.update(bone_count=0), lambda m: m.update(bone_count=256),
                     lambda m: m.update(bone_count=1.0), lambda m: m.update(rigid_vert_list_count=1),
                     lambda m: m.update(rigid_vert_list_count=False), lambda m: m.update(extra=1),
                     lambda m: m.update(schema="unknown"), lambda m: m["blend_vert_counts"].pop(),
                     lambda m: m["blend_vert_counts"].__setitem__(0, -1),
                     lambda m: m["blend_vert_counts"].__setitem__(0, 32768),
                     lambda m: m["blend_vert_counts"].__setitem__(0, True)]
        for mutate in mutations:
            candidate = meta()
            mutate(candidate)
            with self.subTest(metadata=candidate), self.assertRaises(ValueError):
                bridge.convert_h1(H1, candidate)

    def test_all_truncated_and_trailing_lengths(self):
        for data, function in [(H1, bridge.convert_h1), (IW7, bridge.inspect_iw7)]:
            for length in range(len(data)):
                with self.subTest(length=length, function=function.__name__), self.assertRaises(ValueError):
                    function(data[:length], meta())
            with self.assertRaises(ValueError):
                function(data + b"\0", meta())

    def test_division_is_not_silent_rounding(self):
        for bone_word_offset in (0, 2, 4, 8, 10, 14, 18, 20, 24, 28):
            corrupt = bytearray(H1)
            corrupt[bone_word_offset] += 1
            with self.subTest(offset=bone_word_offset), self.assertRaisesRegex(ValueError, "divisible"):
                bridge.convert_h1(bytes(corrupt), meta())

    def test_bone_range_and_padding(self):
        with self.assertRaisesRegex(ValueError, "skeleton"):
            bridge.convert_h1(H1, meta(bones=3))
        with self.assertRaisesRegex(ValueError, "skeleton"):
            bridge.inspect_iw7(IW7, meta(bones=3))
        for offset in (2, 10, 22, 38):
            corrupt = bytearray(IW7)
            corrupt[offset] = 1
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, "trailing record"):
                bridge.inspect_iw7(bytes(corrupt), meta())

    def test_correspondence_catches_changed_weight_and_valid_bone(self):
        for offset, message in [(0, "bone"), (8, "weight")]:
            corrupt = bytearray(IW7)
            corrupt[offset] -= 1
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, message):
                bridge.verify_correspondence(H1, bytes(corrupt), meta())

    def test_boundary_bone_254(self):
        self.assertEqual(bridge.convert_h1(bytes.fromhex("803f"), meta((1, 0, 0, 0, 0, 0, 0, 0), 255)),
                         bytes.fromhex("fe00 0000"))

    def test_deterministic_original_corpus(self):
        rng = random.Random(71012)
        for _ in range(100):
            counts = [rng.randrange(5) for _ in range(4)] + [0] * 4
            counts[0] += 1
            original, expected = [], []
            for group, count in enumerate(counts[:4]):
                for _ in range(count):
                    bones = [rng.randrange(255) for _ in range(group + 1)]
                    weights = [rng.randrange(65536) for _ in range(group)]
                    words = [bones[0] * 64]
                    for bone, weight in zip(bones[1:], weights):
                        words.extend([bone * 64, weight])
                    original.extend(words)
                    expected.append({"bones": bones, "weight_words": weights})
            source = struct.pack("<" + "H" * len(original), *original)
            metadata = meta(counts, 255)
            result = bridge.convert_h1(source, metadata)
            self.assertEqual(bridge.inspect_iw7(result, metadata), expected)
            bridge.verify_correspondence(source, result, metadata)

    def test_cli_fresh_output_and_refusal_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            metadata, source, output = root / "metadata.json", root / "h1.bin", root / "iw7.u16.bin"
            metadata.write_text(json.dumps(meta()), encoding="utf-8")
            source.write_bytes(H1)
            argv = ["--metadata", str(metadata), "--h1-blend", str(source), "--output", str(output)]
            with contextlib.redirect_stdout(io.StringIO()) as receipt:
                self.assertEqual(bridge.main(argv), 0)
            self.assertTrue(json.loads(receipt.getvalue())["independent_word_readback"])
            self.assertEqual(output.read_bytes(), IW7)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(bridge.main(argv), 1)
            self.assertEqual(output.read_bytes(), IW7)
            self.assertEqual(source.read_bytes(), H1)
            # A validation refusal does not create an output at all.
            metadata.write_text('{"schema":1,"schema":2}', encoding="utf-8")
            argv[-1] = str(root / "rejected.u16.bin")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(bridge.main(argv), 1)
            self.assertFalse((root / "rejected.u16.bin").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
