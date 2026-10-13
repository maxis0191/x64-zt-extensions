"""Prepare two source-only publication overlays; no build plan or native work.

Historical renderers, providers, prepared roots and receipts remain untouched.
The output requires fresh main AND zonetool11 compilation before a future link.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

import prepare_catalog_trace as legacy
import prepare_cli

HERE = Path(__file__).resolve().parent
NATIVE = HERE / "native_message_publication.inc"
DECLARATION = 'extern "C" __declspec(noreturn) void t7_catalog_message_cli_exit(const int code);'
WRAPPER = r'''extern "C" __declspec(noreturn) void t7_catalog_message_cli_exit(const int code)
{
	const DWORD saved_error = GetLastError();
	if (catalog_trace_enabled)
	{
		// Inspect catalog_message_close_result in a debugger if publication fails.
		// This internal result is not a promise that stderr contains a diagnostic.
		(void)catalog_message_close();
	}
	else std::fflush(nullptr); // Preserve the non-catalogue CLI behavior.
	SetLastError(saved_error);
	std::quick_exit(code);
}

'''


def overlay(main, cli):
    once = prepare_cli.helper.once
    implementation = NATIVE.read_text(encoding="utf-8")
    if not 0 < len(implementation.encode()) <= 16 * 1024:
        raise ValueError("Bounded publication source required")
    start = legacy.MESSAGE_SUPPORT.index("\t__declspec(noinline) void catalog_message_observe(")
    end = legacy.MESSAGE_SUPPORT.index("\t__declspec(noinline) uintptr_t catalog_message_forward(", start)
    previous = legacy.MESSAGE_SUPPORT[start:end]
    main = once(main, "\tvolatile LONG catalog_message_seen = 0;\n", "")
    main = once(main, previous, implementation + "\n")
    main = once(main, "int main()\n{", WRAPPER + "int main()\n{")
    cli = once(cli, "#include <mutex>", "#include <mutex>\n" + DECLARATION)
    for code in ("EXIT_SUCCESS", "EXIT_FAILURE"):
        old = "\t\t\t\tstd::fflush(nullptr);\n\t\t\t\tstd::quick_exit(" + code + ");"
        cli = once(cli, old, "\t\t\t\tt7_catalog_message_cli_exit(" + code + ");")
    return main, cli


def render(native):
    _, source = prepare_cli.render(native)
    old_main = legacy.wire_message_main(source[prepare_cli.PATHS[0]])
    old_cli = source[prepare_cli.PATHS[1]]
    main, cli = overlay(old_main, old_cli)
    patch = ""
    for name, before, after in (("main.cpp", old_main, main), ("zonetool.cpp", old_cli, cli)):
        patch += "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                         fromfile="a/" + name, tofile="b/" + name))
    outputs = {"main.cpp": main.encode(), "zonetool.cpp": cli.encode(), "publication-overlay.patch": patch.encode()}
    report = {"Schema": "iw7.t7-message-publication-source/1",
              "Profile": "t7-catalog-message-publication-source-only",
              "NativeSourceCommit": "fab935826c898806855376662a8a03317b3ad8f1",
              "RequiredFreshStages": ["main", "zonetool11", "link"],
              "HistoricalMainOnlyProfileCompatible": False, "BuildPlanCreated": False,
              "CloseBudgetMilliseconds": 100, "CloseMaxPolls": 100, "MaxRecordBytes": 1023,
              "CloseDiagnostic": "internal atomic result only; blocked/failed sink may publish nothing",
              "InputSource": {"main.cpp": hashlib.sha256(old_main.encode()).hexdigest(),
                              "zonetool.cpp": hashlib.sha256(old_cli.encode()).hexdigest()},
              "Bindings": {"GeneratorSHA256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                           "PublicationSourceSHA256": hashlib.sha256(NATIVE.read_bytes()).hexdigest(),
                           "LegacyWiringSHA256": hashlib.sha256(Path(legacy.__file__).read_bytes()).hexdigest()},
              "Outputs": {name: {"Bytes": len(raw), "SHA256": hashlib.sha256(raw).hexdigest()} for name, raw in outputs.items()},
              "NativeExecuted": False, "CandidateCreated": False, "RuntimeVerified": False, "Ready": False}
    outputs["source-report.json"] = (json.dumps(report, indent=2) + "\n").encode()
    if sum(map(len, outputs.values())) > 1024 * 1024:
        raise ValueError("Source preparation exceeds 1 MiB")
    return outputs, report


def prepare(native, output):
    # Use the existing source-snapshot reader's pin/reparse checks. The output
    # is a fresh single directory; no recursive edits or retained-root writes.
    native, output = Path(native), Path(output)
    if not output.is_absolute() or output.exists() or not output.parent.is_dir():
        raise ValueError("Fresh absolute output with existing parent required")
    for parent in (output.parent, *output.parent.parents):
        if parent.is_symlink() or parent.is_junction():
            raise ValueError("No output reparse ancestry")
    outputs, report = render(native)
    output.mkdir()
    for name, raw in outputs.items():
        with (output / name).open("xb") as stream:
            stream.write(raw)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output), indent=2))
