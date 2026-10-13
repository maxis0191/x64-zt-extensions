import hashlib
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("inspection", Path(__file__).with_name("inspect_sources.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BoundedSourceTests(unittest.TestCase):
    def test_archive_names(self):
        self.assertEqual(module.member_name("model/source.dae"), "model/source.dae")
        for value in ("../outside", "/root", "C:/outside", "x\\y"):
            with self.assertRaises(ValueError):
                module.member_name(value)

    def test_xml_entity_and_wrong_format(self):
        for data in (b"<!DOCTYPE X><X/>", b"<!ENTITY x 'x'><X/>", b"<X/>"):
            with self.assertRaises(ValueError):
                module.collada(data)

    def test_source_identity_and_size(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            source.write_bytes(b"source")
            self.assertEqual(module.identity(source, hashlib.sha256(b"source").hexdigest(), 6)["bytes"], 6)
            for expected, bound in (("0"*64, 6), (hashlib.sha256(b"source").hexdigest(), 5)):
                with self.assertRaises(ValueError):
                    module.identity(source, expected, bound)

    def test_sdna_own_schema(self):
        data = b"SDNANAME" + struct.pack("<I", 0) + b"TYPE" + struct.pack("<I", 1) + b"Bone\0\0\0\0" + b"TLEN" + struct.pack("<H", 8) + b"\0\0STRC" + struct.pack("<IHH", 1, 0, 0)
        self.assertEqual(module.dna_struct_names(data, "<"), ["Bone"])
        with self.assertRaises(ValueError):
            module.dna_struct_names(data[:-1], "<")


if __name__ == "__main__":
    unittest.main()
