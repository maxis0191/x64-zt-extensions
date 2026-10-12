"""Resource tool binding and pre-link drift refusal without native execution."""
import copy
import ntpath
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_contract import SDK_BIN, SDK_TOOLS, key, reviewed_sdk_tools
import build_worker


def fixture():
    pins = [{"path": ntpath.join(SDK_BIN, name), "bytes": length, "sha256": digest}
            for name, (length, digest) in SDK_TOOLS.items()]
    compiler = r"C:\VC\bin\Hostx64\x64\cl.exe"
    return {"sdk_tools": pins, "source_pins": copy.deepcopy(pins), "compiler": compiler,
            "environment": {"PATH": ntpath.dirname(compiler) + ";" + SDK_BIN + r";C:\Windows\System32"}}


class SdkTools(unittest.TestCase):
    def test_exact_two_new_guarded_tools_and_fixed_path(self):
        plan = fixture()
        self.assertEqual(reviewed_sdk_tools(plan, {}), plan["sdk_tools"])

    def test_missing_duplicate_unbound_or_relabelled_tool_fails(self):
        for mode in ("missing", "duplicate", "unbound", "duplicate-source", "unbound-hash", "old-seal"):
            plan = fixture()
            sealed = {}
            if mode == "missing":
                plan["sdk_tools"].pop()
            elif mode == "duplicate":
                plan["sdk_tools"][1] = plan["sdk_tools"][0]
            elif mode == "unbound":
                plan["source_pins"].pop()
            elif mode == "duplicate-source":
                plan["source_pins"].append(plan["source_pins"][0])
            elif mode == "unbound-hash":
                plan["source_pins"][0]["sha256"] = "0"*64
            else:
                sealed[key(plan["sdk_tools"][0]["path"])] = {}
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                reviewed_sdk_tools(plan, sealed)

    def test_wrong_sdk_version_architecture_hash_size_or_search_order_fails(self):
        for mode in ("version", "x86", "hash", "size", "typed-size", "missing-sdk-path", "extra-path", "search-order"):
            plan = fixture()
            if mode == "version":
                plan["sdk_tools"][0]["path"] = plan["sdk_tools"][0]["path"].replace("26100", "22621")
            elif mode == "x86":
                plan["sdk_tools"][0]["path"] = plan["sdk_tools"][0]["path"].replace("x64", "x86")
            elif mode == "hash":
                plan["sdk_tools"][0]["sha256"] = "0"*64
            elif mode == "size":
                plan["sdk_tools"][0]["bytes"] += 1
            elif mode == "typed-size":
                plan["sdk_tools"][0]["bytes"] = str(plan["sdk_tools"][0]["bytes"])
            elif mode == "missing-sdk-path":
                plan["environment"]["PATH"] = plan["environment"]["PATH"].replace(";"+SDK_BIN, "")
            elif mode == "extra-path":
                plan["environment"]["PATH"] += r";C:\unreviewed"
            else:
                plan["environment"]["PATH"] = SDK_BIN + ";" + ntpath.dirname(plan["compiler"]) + r";C:\Windows\System32"
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                reviewed_sdk_tools(plan, {})

    def test_worker_refuses_missing_or_changed_resource_bytes(self):
        plan = fixture()
        with patch.object(build_worker, "bounded", side_effect=FileNotFoundError("fixture missing tool")):
            with self.assertRaises(FileNotFoundError):
                build_worker.verify_sdk_tools(plan, {})
        for mode in ("size", "digest"):
            raw = b"x" * (SDK_TOOLS["rc.exe"][0] + (1 if mode == "size" else 0))
            with self.subTest(mode=mode), patch.object(build_worker, "bounded", return_value=raw):
                with self.assertRaisesRegex(ValueError, "SDK resource tool changed"):
                    build_worker.verify_sdk_tools(plan, {})


if __name__ == "__main__":
    unittest.main()
