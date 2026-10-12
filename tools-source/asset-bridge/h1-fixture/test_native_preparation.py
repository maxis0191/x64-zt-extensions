"""Source-only checks. Requires existing pinned source; never compiles or runs C++."""
import argparse
import json
from pathlib import Path
import re
import tempfile
import threading
import unittest
from unittest import mock

import prepare_native as native

SOURCE = None


class NativePreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SOURCE is None:
            raise unittest.SkipTest("Pinned source preparation requires explicit --source-repo")
        cls.sources, cls.contract = native.checked_sources(SOURCE)
        cls.root = Path(__file__).resolve().parent
        cls.patch = native.bounded(cls.root/"h1-xsurface-reviewed.patch").decode()
        cls.outputs, cls.fragments = native.assemble(cls.sources,cls.patch)
        cls.probe = native.bounded(cls.root/"native_probe.cpp").decode()

    def test_real_parser_bodies_are_verbatim(self):
        text = self.outputs["production_parsers.inc"].decode()
        for name, end in (("xmodel","\n\tvoid xmodel::init("),("xsurface","\n\tvoid xsurface::init(")):
            source = self.sources[native.BASE+"h1/assets/"+name+".cpp"]
            exact = source[source.index("namespace zonetool::h1"):source.index(end)]
            self.assertIn(exact,text)
            self.assertEqual(text.count(name+"::parse("),1)
        self.assertNotIn("db_find_x_asset",text)

    def test_converter_patch_and_exact_bodies(self):
        source = self.sources[native.BASE+"h1/converter/iw7/assets/xsurface.cpp"]
        patched = native.apply_exact_patch(source,self.patch)
        self.assertEqual(native.digest(patched.encode()),native.PATCHED_SHA)
        exact = patched[patched.index("\t\t\tvoid ValidateH1BlendVerts("):patched.index("\n\t\t\tvoid dump(")]
        self.assertIn(exact,self.outputs["production_converters.inc"].decode())
        self.assertIn("self_visibility::XSurfacePackSelfVisibility(default_visibility)",exact)

    def test_changed_patch_and_source_fail_closed(self):
        source = self.sources[native.BASE+"h1/converter/iw7/assets/xsurface.cpp"]
        with self.assertRaisesRegex(ValueError,"patch hash mismatch"):
            native.apply_exact_patch(source,self.patch+"\n")
        with self.assertRaises(ValueError):
            native.apply_exact_patch(source.replace("// into iw7 layout","// modified layout"),self.patch)
        with self.assertRaises(ValueError):
            native.apply_exact_patch(source.replace("surf->vertexLightingIndex","surf->unexpectedIndex"),self.patch)

    def test_declarations_only_adapter_retains_storage(self):
        text = self.outputs["parser_declarations.inc"].decode()
        self.assertNotIn("asset_interface",text)
        self.assertNotIn("override",text)
        self.assertIn("std::vector<std::pair<scr_string_t*, const char*>> script_strings;",text)
        self.assertIn("const char* get_script_string(scr_string_t* ptr);",text)
        self.assertIn("XModel* parse(std::string name, zone_memory* mem);",text)
        self.assertIn("XModelSurfs* parse(const std::string& name, zone_memory* mem);",text)

    def test_production_support_is_not_a_reader_or_allocator_mock(self):
        support = self.outputs["production_support.inc"].decode()
        source = self.sources[native.BASE+"utils/io/filesystem.cpp"]
        self.assertIn(source[source.index("namespace zonetool"):],support)
        self.assertIn("memory::allocator::allocate(const size_t length)",support)
        self.assertIn("uint32_t XSurfacePackSelfVisibility(float* packed)",support)
        self.assertIn('#include "zonetool/utils/io/assetmanager.hpp"',self.probe)
        self.assertNotIn("class reader",support)
        self.assertNotIn("throw std::runtime_error",support)

    def test_no_dump_or_engine_string_resolution_is_substituted(self):
        combined = self.probe + "\n".join(b.decode() for b in self.outputs.values())
        for forbidden in ("SL_ConvertToString(","SL_GetString(","::dump(","LoadLibrary(","db_find_x_asset"):
            self.assertNotIn(forbidden,combined)
        self.assertIn('model_parser.get_script_string(&source_model->boneNames[0])',self.probe)
        self.assertIn('model->boneNames[0] == 0',self.probe)
        self.assertNotRegex(self.probe,r"boneNames\[0\]\s*=(?!=)")

    def test_original_byte_guards_precede_actual_calls(self):
        before = self.probe.index("LockedFixture model_guard")
        parse = self.probe.index('model_parser.parse("paris_h1_original_cube"')
        convert = self.probe.index("xmodel::convert(source_model, converted_memory)")
        self.assertLess(before,parse); self.assertLess(parse,convert)
        self.assertIn("FILE_SHARE_READ",self.probe)
        self.assertIn("std::memcmp(actual.data(), expected, bytes)",self.probe)
        self.assertIn("xsurface::convert(source_group, converted_memory)",self.probe)

    def test_literal_self_visibility_for_actual_profile(self):
        # Independent integer evaluation at exactly representable {0,0,1,0}.
        expected = 256 | (256 << 9) | (127 << 18)
        self.assertEqual(expected,0x01FE0100)
        match = re.search(r"b.selfVisibility.packed == (0x[0-9A-F]+)",self.probe)
        self.assertEqual(int(match.group(1),16),expected)

    def test_source_preparation_budget_not_execution_authorization(self):
        plan = native.compile_plan(SOURCE,self.root/"prepared-native")
        self.assertFalse(plan["compile_executed"])
        self.assertFalse(plan["estimate_is_measured"])
        self.assertEqual((plan["estimated_physical_gib"],plan["estimated_commit_gib"]),(4,6))
        self.assertEqual(plan["compiler_processes"],1)
        self.assertNotIn("/MP",plan["planned_compile_arguments"])
        self.assertLess(sum(map(len,self.outputs.values())) + len(self.probe.encode()),1024*1024)

    def test_preflight_rejects_modified_bytes_and_preparation_refuses_overwrite(self):
        # Only fresh, owned temporary source files under this task's folder.
        with tempfile.TemporaryDirectory(prefix=".native-check-",dir=self.root) as tmp:
            self.assertEqual(Path(tmp).parent,self.root)
            output = Path(tmp)/"prepared"
            native.prepare(SOURCE,output)
            self.assertEqual(native.verify_prepared(SOURCE,output)["prepared_files_verified"],6)
            files = list(output.iterdir())
            before = {p.name:native.digest(p.read_bytes()) for p in files}
            with self.assertRaisesRegex(ValueError,"fresh preparation directory"):
                native.prepare(SOURCE,output)
            self.assertEqual(before,{p.name:native.digest(p.read_bytes()) for p in files})
            target = output/"native_probe.cpp"
            original = target.read_bytes()
            for changed in (original+b"\n",original.replace(b"\n",b"\r\n")):
                target.write_bytes(changed)
                with self.assertRaisesRegex(ValueError,"prepared source differs"):
                    native.verify_prepared(SOURCE,output)
            target.write_bytes(original)
            native.verify_prepared(SOURCE,output)


class BoundedReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parent

    def test_same_handle_read_is_bounded_when_source_grows_concurrently(self):
        # Deterministic real concurrent append after the pre-read fstat, before
        # read. This is the old stat-small/read-unbounded review reproduction.
        with tempfile.TemporaryDirectory(prefix=".native-check-",dir=self.root) as tmp:
            self.assertEqual(Path(tmp).parent,self.root)
            target = Path(tmp)/"growing.cpp"
            original_open = Path.open
            for growth, error in ((b"x"*(native.READ_LIMIT+64),"bounded read limit"),
                                  (b"x","changed during bounded read")):
                target.write_bytes(b"a")
                start, done = threading.Event(),threading.Event()
                writer_errors, requests = [],[]
                def writer():
                    try:
                        if not start.wait(5):
                            raise AssertionError("reader did not reach bounded read")
                        with original_open(target,"ab",buffering=0) as stream:
                            stream.write(growth)
                    except Exception as exc:
                        writer_errors.append(exc)
                    finally:
                        done.set()
                class ReadBarrier:
                    def __init__(self,stream): self.stream=stream
                    def __enter__(self): return self
                    def __exit__(self,*args): self.stream.close()
                    def fileno(self): return self.stream.fileno()
                    def read(self,count):
                        requests.append(count)
                        start.set()
                        if not done.wait(5):
                            raise AssertionError("concurrent writer did not finish")
                        return self.stream.read(count)
                def guarded_open(path,*args,**kwargs):
                    stream = original_open(path,*args,**kwargs)
                    return ReadBarrier(stream) if path == target and args[0] == "rb" else stream
                thread = threading.Thread(target=writer)
                thread.start()
                try:
                    with mock.patch.object(Path,"open",guarded_open):
                        with self.assertRaisesRegex(ValueError,error):
                            native.raw_bounded(target)
                finally:
                    start.set(); thread.join(5)
                self.assertFalse(thread.is_alive())
                self.assertEqual(writer_errors,[])
                self.assertEqual(requests,[native.READ_LIMIT+1])

    def test_replacement_between_path_check_and_open_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix=".native-check-",dir=self.root) as tmp:
            self.assertEqual(Path(tmp).parent,self.root)
            target, replacement = Path(tmp)/"source.cpp",Path(tmp)/"replacement.cpp"
            target.write_bytes(b"first"); replacement.write_bytes(b"other")
            original_open = Path.open
            def replace_before_open(path,*args,**kwargs):
                if path == target and args[0] == "rb":
                    replacement.replace(target)
                return original_open(path,*args,**kwargs)
            with mock.patch.object(Path,"open",replace_before_open):
                with self.assertRaisesRegex(ValueError,"changed while opening"):
                    native.raw_bounded(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo",type=Path,required=True)
    args = parser.parse_args()
    SOURCE = args.source_repo
    unittest.main(argv=[__file__],verbosity=2)
