"""Original tiny image fixtures and an independent DDS-header oracle. No game data."""
from dataclasses import replace
from contextlib import redirect_stdout
import io
import json
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import resident_image as subject


def copied(width=2, height=2, levels=1, fmt=28, size=16):
    return subject.CopiedImage(width, height, 1, width, height, levels, levels,
        fmt, size, 1, 0, 0, 0, 0, 0, 0, False, False, 2)


def dds_oracle(blob):
    """Read fixed DDS/DX10 offsets independently of the production layout/format table."""
    if len(blob) < 148 or blob[:4] != b"DDS ":
        raise ValueError("not a complete DDS header")
    word = lambda offset: int.from_bytes(blob[offset:offset+4], "little")
    if word(4) != 124 or word(76) != 32 or word(80) != 4 or blob[84:88] != b"DX10":
        raise ValueError("wrong DDS/DX10 header")
    if word(132) != 3 or word(136) != 0 or word(140) != 1 or word(144) != 0:
        raise ValueError("not a single 2D image with unknown alpha mode")
    if blob[32:76] != bytes(44) or blob[88:108] != bytes(20) or blob[112:128] != bytes(16):
        raise ValueError("nonzero reserved fields")
    return dict(flags=word(8), height=word(12), width=word(16), pitch=word(20),
                depth=word(24), levels=word(28), caps=word(108), dxgi=word(128), pixels=blob[148:])


class ResidentImageTests(unittest.TestCase):
    def test_rgba_checkerboard_header_and_original_pixels(self):
        pixels = bytes.fromhex("ff0000ff 00ff00ff 0000ffff ffffffff")
        result = dds_oracle(subject.to_dds(copied(), pixels))
        self.assertEqual(result, dict(flags=0x2100F, height=2, width=2, pitch=8, depth=1,
            levels=1, caps=0x1000, dxgi=28, pixels=pixels))

    def test_linear_non_square_mips_use_tight_rows_in_declared_order(self):
        view = copied(3, 5, 3, 28, 72)  # 3x5x4 + 1x2x4 + 1x1x4
        pixels = b"\x11"*60 + b"\x22"*8 + b"\x33"*4
        blob = subject.to_dds(view, pixels)
        self.assertEqual(dds_oracle(blob)["caps"], 0x401008)
        self.assertEqual(dds_oracle(blob)["pitch"], 12)
        self.assertEqual([m.offset for m in subject.layout(view)], [0, 60, 68])
        self.assertEqual(blob[148:208], b"\x11"*60)
        self.assertEqual(blob[208:216], b"\x22"*8)
        self.assertEqual(blob[216:], b"\x33"*4)

    def test_bc1_red_block_remains_compressed_with_linear_size_flag(self):
        # Original BC1 block: RGB565 red endpoint, black endpoint, every index=0.
        red = bytes.fromhex("00f8 0000 00000000")
        result = dds_oracle(subject.to_dds(copied(4, 4, 1, 71, 8), red))
        self.assertEqual(result["flags"], 0xA1007)
        self.assertEqual(result["pitch"], 8)
        self.assertEqual(result["pixels"], red)

    def test_bc_mip_tail_and_non_multiple_of_four_dimensions(self):
        for fmt, unit in ((71, 8), (77, 16)):
            with self.subTest(fmt=fmt):
                view = copied(7, 5, 3, fmt, 6*unit)  # blocks: 2x2,1x1,1x1
                pixels = b"\x01"*(4*unit) + b"\x02"*unit + b"\x03"*unit
                decoded = dds_oracle(subject.to_dds(view, pixels))
                self.assertEqual(decoded["pitch"], 4*unit)
                self.assertEqual([m.row_pitch for m in subject.layout(view)], [2*unit, unit, unit])
                self.assertEqual([m.slice_pitch for m in subject.layout(view)], [4*unit, unit, unit])
                self.assertEqual(decoded["pixels"], pixels)

    def test_one_by_one_bc_still_contains_one_full_block(self):
        for fmt, size in ((71, 8), (80, 8), (83, 16), (98, 16)):
            decoded = dds_oracle(subject.to_dds(copied(1, 1, 1, fmt, size), bytes(size)))
            self.assertEqual(decoded["pitch"], size)
            self.assertEqual(len(decoded["pixels"]), size)

    def test_every_supported_typed_format_has_expected_storage(self):
        # Explicit SDK IDs/sizes; intentionally independent of subject.FORMATS values.
        expected = {28:4,29:4,49:2,61:1,71:8,72:8,74:16,75:16,77:16,78:16,
                    80:8,81:8,83:16,84:16,87:4,91:4,98:16,99:16}
        self.assertEqual(set(subject.FORMATS), set(expected))
        for fmt, size in expected.items():
            with self.subTest(fmt=fmt):
                pixels = bytes(range(size))
                decoded = dds_oracle(subject.to_dds(copied(1, 1, 1, fmt, size), pixels))
                self.assertEqual((decoded["dxgi"], decoded["pixels"]), (fmt, pixels))

    def test_srgb_and_signed_formats_are_not_relabelled_or_transformed(self):
        for linear, srgb, size in ((28,29,4),(71,72,8),(74,75,16),(77,78,16),(87,91,4),(98,99,16)):
            original = bytes(range(size))
            a = subject.to_dds(copied(1,1,1,linear,size), original)
            b = subject.to_dds(copied(1,1,1,srgb,size), original)
            self.assertEqual(a[:128], b[:128])
            self.assertEqual(a[132:], b[132:])
            self.assertNotEqual(a[128:132], b[128:132])
        for signed, size in ((81,8),(84,16)):
            self.assertEqual(dds_oracle(subject.to_dds(copied(1,1,1,signed,size), bytes(size)))["dxgi"], signed)

    def test_semantic_does_not_invent_slot_packing_or_pixel_transforms(self):
        a = subject.to_dds(copied(), bytes(16))
        b = subject.to_dds(replace(copied(), source_semantic=4), bytes(16))
        self.assertEqual(a, b)  # Material/normal-map mapping is deliberately separate.

    def test_stream_fallback_delayed_and_unknown_flags_are_refused(self):
        cases = {"streaming":1,"streamed_part_count":1,"use_fallback":1,"fallback_level":1,
                 "fallback_size":4,"fallback_pointer_present":True,"delay_load_pixels":True,"flags":1}
        for key, value in cases.items():
            with self.subTest(field=key), self.assertRaises(ValueError):
                subject.to_dds(replace(copied(), **{key:value}), bytes(16))

    def test_malformed_dimensions_counts_and_metadata_types_are_refused(self):
        cases = {"width":0,"height":4097,"depth":2,"width1":1,"height1":1,
                 "level_count":0,"level_count1":2,"map_type":4,"total_size":-1,"source_semantic":21}
        for key, value in cases.items():
            with self.subTest(field=key), self.assertRaises(ValueError):
                subject.layout(replace(copied(), **{key:value}))
        for view in (replace(copied(), width=True), replace(copied(), delay_load_pixels=0),
                     replace(copied(), width=2.0), replace(copied(), total_size=2**40),
                     replace(copied(), level_count=3, level_count1=3)):
            with self.assertRaises(ValueError): subject.layout(view)

    def test_unsupported_typeless_hdr_and_t7_enum_namespace_are_refused(self):
        for fmt in (0,27,70,73,76,79,82,95,96,97,10000):
            with self.subTest(fmt=fmt), self.assertRaises(ValueError):
                subject.layout(replace(copied(), dxgi_format=fmt))
        meta = subject.metadata(copied())
        meta["format_namespace"] = "GfxPixelFormat"
        with self.assertRaises(ValueError): subject.from_metadata(meta)

    def test_padding_truncation_extra_bytes_and_borrowed_memory_are_refused(self):
        for pixels in (bytes(15), bytes(17), bytearray(16), memoryview(bytes(16)), None):
            with self.assertRaises(ValueError): subject.to_dds(copied(), pixels)
        for size in (15,17,32):
            with self.assertRaises(ValueError): subject.layout(replace(copied(), total_size=size))

    def test_budget_boundary_is_checked_without_allocating_large_pixels(self):
        self.assertEqual(subject.layout(copied(4096,4096,1,61,16777216))[0].slice_pitch, 16777216)
        with self.assertRaises(ValueError): subject.layout(copied(4096,4096,2,61,16777216))
        with self.assertRaises(ValueError): subject.layout(replace(copied(), total_size=16777217))

    def test_copy_schema_has_no_defaults_no_unknown_keys_and_no_path_resolution(self):
        meta = subject.metadata(copied())
        self.assertEqual(subject.from_metadata(meta), copied())
        for key in ("format_namespace", "schema", "image"):
            bad = dict(meta)
            del bad[key]
            with self.assertRaises(ValueError): subject.from_metadata(bad)
        meta["image"]["pixels_path"] = "not-opened"
        with self.assertRaises(ValueError): subject.from_metadata(meta)

    def test_file_conversion_and_exclusive_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            meta, pixels, output = root/"copy.json", root/"pixels.bin", root/"image.dds"
            meta.write_text(json.dumps(subject.metadata(copied())), encoding="utf-8")
            pixels.write_bytes(bytes(range(16)))
            receipt = subject.convert_files(meta, pixels, output)
            self.assertEqual(dds_oracle(output.read_bytes())["pixels"], pixels.read_bytes())
            self.assertFalse(receipt["runtime_verified"])
            self.assertFalse(receipt["material_verified"])
            with self.assertRaises(FileExistsError): subject.convert_files(meta, pixels, output)
            self.assertEqual(dds_oracle(output.read_bytes())["pixels"], bytes(range(16)))

    def test_file_input_caps_duplicates_and_short_reads_precede_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            meta, pixels, output = root/"copy.json", root/"pixels.bin", root/"image.dds"
            for data in ('{"x":1,"x":2}', '{"x":NaN}', ' '*16385):
                meta.write_text(data, encoding="utf-8")
                with self.assertRaises(ValueError): subject.convert_files(meta, pixels, output)
                self.assertFalse(output.exists())
            meta.write_text(json.dumps(subject.metadata(copied())), encoding="utf-8")
            for data in (bytes(15),bytes(17)):
                pixels.write_bytes(data)
                with self.assertRaises(ValueError): subject.convert_files(meta, pixels, output)
                self.assertFalse(output.exists())

    def test_independent_oracle_detects_corrupt_dimension_and_header(self):
        blob = bytearray(subject.to_dds(copied(), bytes(16)))
        for offset in (0,4,76,80,84,132,140):
            corrupted = bytearray(blob)
            corrupted[offset] ^= 0x80
            with self.subTest(offset=offset), self.assertRaises(ValueError): dds_oracle(bytes(corrupted))


class IW7ReadbackTests(unittest.TestCase):
    def dump(self, view, pixels, name="community_bo3_color", semantic=2):
        # Independent pinned GfxImage/assetmanager offsets; no native binary.
        scalar = bytearray(112)
        struct.pack_into("<I", scalar, 24, view.dxgi_format)
        scalar[32:35] = bytes((3, semantic, 3))
        struct.pack_into("<II4H", scalar, 40,
                         len(pixels), len(pixels), view.width, view.height, 1, 1)
        scalar[56] = view.level_count
        struct.pack_into("<Q", scalar, 64, 1)
        return (b"\x08\x01\x01\0\0\0" + scalar + b"\x06\x01" + name.encode() +
                b"\0\x08\x01" + struct.pack("<I", len(pixels)) + pixels)

    def verify(self, view, pixels, raw, name="community_bo3_color", semantic=2):
        return subject.verify_iw7_image(view, pixels, raw, name, semantic)

    def test_non_square_full_mips_are_verified_without_a_32px_assumption(self):
        view = copied(3, 5, 3, 29, 72)
        pixels = b"\x11"*60 + b"\x22"*8 + b"\x33"*4
        result = self.verify(view, pixels, self.dump(view, pixels))
        self.assertEqual((result["width"], result["height"], result["mip_count"]), (3, 5, 3))
        self.assertEqual(result["pixel_sha256"], hashlib.sha256(pixels).hexdigest())
        self.assertTrue(result["serialized_pixel_bytes_verified"])
        self.assertFalse(result["material_verified"])
        self.assertFalse(result["rendered_verified"])

    def test_all_typed_formats_compare_bytes_including_bc_tails(self):
        for fmt, size in {28:4,29:4,49:2,61:1,71:8,72:8,74:16,75:16,77:16,78:16,
                          80:8,81:8,83:16,84:16,87:4,91:4,98:16,99:16}.items():
            with self.subTest(fmt=fmt):
                view, pixels = copied(1, 1, 1, fmt, size), bytes(range(size))
                self.assertEqual(self.verify(view, pixels, self.dump(view, pixels))["dxgi_format"], fmt)
        view, pixels = copied(7, 5, 3, 98, 96), bytes(range(96))
        self.assertEqual(self.verify(view, pixels, self.dump(view, pixels))["mip_count"], 3)

    def test_metadata_shape_format_and_mip_corruption_is_refused(self):
        view, pixels = copied(), bytes(16)
        raw = self.dump(view, pixels)
        for offset in (0, 6+24, 6+32, 6+34, 6+40, 6+44, 6+48, 6+50, 6+52, 6+54, 6+56, 6+57, 6+64):
            changed = bytearray(raw)
            changed[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                self.verify(view, pixels, bytes(changed))

    def test_semantic_is_explicit_and_not_inferred_from_t7(self):
        view, pixels = replace(copied(), source_semantic=4), bytes(16)
        raw = self.dump(view, pixels, semantic=5)
        self.assertEqual(self.verify(view, pixels, raw, semantic=5)["iw7_semantic"], 5)
        for semantic in (4, True, -1, 17, None):
            with self.subTest(semantic=semantic), self.assertRaises(ValueError):
                self.verify(view, pixels, raw, semantic=semantic)

    def test_wrong_identity_trailing_truncated_or_changed_pixels_are_refused(self):
        view, pixels = copied(), bytes(range(16))
        raw = self.dump(view, pixels)
        for changed in (raw[:-1], raw+b"x", raw[:-1]+b"x"):
            with self.assertRaises(ValueError): self.verify(view, pixels, changed)
        for name in ("other", "", "bad\0name", "x"*256, None):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.verify(view, pixels, raw, name=name)

    def test_readback_only_reads_explicit_tiny_files_and_creates_no_dds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            meta, data, dump = root/"copy.json", root/"pixels.bin", root/"image.iw7Image"
            view, pixels = copied(), bytes(range(16))
            meta.write_text(json.dumps(subject.metadata(view)))
            data.write_bytes(pixels)
            dump.write_bytes(self.dump(view, pixels))
            result = subject.verify_files(meta, data, dump, "community_bo3_color", 2)
            self.assertTrue(result["serialized_pixel_bytes_verified"])
            self.assertEqual(len(list(root.iterdir())), 3)

    def test_cli_readback_and_original_conversion_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            meta, data, dump, output = (root/name for name in
                                       ("copy.json", "pixels.bin", "image.iw7Image", "image.dds"))
            view, pixels = copied(), bytes(range(16))
            meta.write_text(json.dumps(subject.metadata(view)))
            data.write_bytes(pixels)
            dump.write_bytes(self.dump(view, pixels))
            prefix = ["resident_image.py", str(meta), str(data)]
            for arguments, expected in (
                (["--verify-iw7-image", str(dump)], 2),
                (["--verify-iw7-image", str(dump), "--image-name", "community_bo3_color",
                  "--iw7-semantic", "2"], 0),
                ([str(output)], 0),
            ):
                with patch("sys.argv", prefix+arguments), redirect_stdout(io.StringIO()):
                    self.assertEqual(subject.main(), expected)
            self.assertEqual(dds_oracle(output.read_bytes())["pixels"], pixels)


if __name__ == "__main__":
    unittest.main()
