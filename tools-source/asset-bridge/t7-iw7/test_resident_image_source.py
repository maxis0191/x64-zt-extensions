"""Portable source-contract checks only: these do not compile/run the C++ adapter."""
from dataclasses import fields
from pathlib import Path
import re
import unittest

import resident_image

SOURCE = Path(__file__).with_name("resident_image_copy.hpp").read_text(encoding="utf-8")
CODE = re.sub(r"//[^\n]*|/\*.*?\*/", "", SOURCE, flags=re.S)


class ResidentImageSourceTests(unittest.TestCase):
    def test_format_allowlist_matches_encoder(self):
        switch = CODE.split("switch (image.dxgi_format)", 1)[1].split("default:", 1)[0]
        values = [int(v) for v in re.findall(r"case\s+(\d+)\s*:", switch)]
        self.assertEqual(set(values), set(resident_image.FORMATS))
        self.assertEqual(len(values), len(set(values)))

    def test_scalar_metadata_matches_encoder_without_pointers(self):
        body = CODE.split("struct metadata", 1)[1].split("bool operator==", 1)[0]
        names = []
        for match in re.finditer(r"(?:std::uint32_t|bool)\s+([^;]+);", body):
            names.extend(name.strip() for name in match[1].split(","))
        self.assertEqual(names, [field.name for field in fields(resident_image.CopiedImage)])
        self.assertNotIn("*", body)

    def test_bounded_readable_callback_precedes_header_and_pixel_copies(self):
        self.assertLess(CODE.index("readable(source, sizeof(GfxImage))"), CODE.index("std::memcpy(&result, source"))
        self.assertLess(CODE.index("validate(result.image)"), CODE.index("result.pixels.resize"))
        self.assertLess(CODE.index("readable(before.pixels, result.image.total_size)"), CODE.index("std::memcpy(result.pixels.data()"))
        self.assertIn("sizeof(GfxImage) == 0x108", CODE)
        self.assertIn("offsetof(GfxImage, name) == 248", CODE)
        self.assertIn("max() - address", CODE)

    def test_changed_header_is_refused_and_no_engine_or_io_api_is_added(self):
        self.assertIn("view(after) == result.image && after.pixels == before.pixels", CODE)
        self.assertIsNone(re.search(r"\b(?:OpenProcess|ReadProcessMemory|VirtualQuery|VirtualProtect|LoadLibrary\w*|"
            r"CreateFile\w*|WriteFile|CreateThread|DB_\w+|get_data_for_xpak_key|dump|post_unpack)\s*\(", CODE))
        self.assertNotIn("reinterpret_cast<zonetool::iw7", CODE)

    def test_residency_flags_and_chain_size_are_required_in_source(self):
        for condition in ("image.streaming == 0", "image.streamed_part_count == 0", "image.use_fallback == 0",
            "image.fallback_level == 0", "image.fallback_size == 0", "!image.fallback_pointer_present",
            "!image.delay_load_pixels", "image.flags == 0", "total == image.total_size"):
            self.assertIn(condition, CODE)


if __name__ == "__main__":
    unittest.main()
