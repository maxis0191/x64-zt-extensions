"""Create a reviewable local plan; never load native providers or acquire a lease."""
import argparse
import hashlib
import json
from pathlib import Path

import generate
import prepare_native

OWN = Path(__file__).resolve().parent
JOB_SHA = "5f613ebb83019dbf4bfa4f6a93c5329098343729b70acc2cfa70aa8b64f195f8"
JOB_SOURCE_SHA = "ddefa72ff2b98286cd585d1178c13e67dcd646bbcf39d51365660901366c5ca8"
PROVIDERS = {
    "ops/Resource-Scheduler.Core.ps1": "0d0ebef0f434c4e1ecc2614a4061f7e0685988adefcae596ff5a7891b1f3e25b",
    "ops/Resource-Memory.ps1": "6a708d2e7fa9803628bfbf5c670068d63d22a2d2cfc157994afa82d56ac9c241",
    "ops/Resource-RecorderOwnedProcess.Core.ps1": "23d6f589a6f973f6d9c56a2ff3dcb66c4df6a0aa9fe0a7125048dd9061f93c54",
    "ops/native/ResourceMemory.cs": "b159804d12ca504cd592f4cdee191a9b68353e9e0117f9045a28a522b25692e9",
    "tools-source/asset-bridge/animation/Probe-NativeJob.cs": JOB_SOURCE_SHA,
}


def binding(path, expected=None):
    path = generate.regular_ancestry(path)
    before = path.stat()
    generate.require(path.is_file() and before.st_size <= 64 * 1024**2, "bounded file required")
    digest = hashlib.sha256()
    total = 0
    with path.open("rb", buffering=0) as stream:
        while True:
            block = stream.read(min(65536, before.st_size + 1 - total))
            if not block:
                break
            total += len(block)
            generate.require(total <= before.st_size, "file grew while planning")
            digest.update(block)
    after = path.stat()
    generate.require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                     (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) and
                     total == before.st_size, "file changed while planning")
    value = digest.hexdigest()
    generate.require(expected is None or value == expected, "reviewed provider changed: " + str(path))
    return {"Path": str(path), "Bytes": total, "SHA256": value}


def make_plan(source, prepared, fixture, providers, job, vc, sdk, sdk_version, run):
    prepare_native.verify_prepared(source, prepared)
    generate.regular_ancestry(run)
    runtime = OWN.parents[2] / "runtime"
    generate.require(run.is_relative_to(runtime) and run != runtime and not run.exists(),
                     "fresh run root beneath this worktree runtime required")
    inputs = []
    contract = json.loads(prepare_native.raw_bounded(OWN / "native-source-contract.json"))
    inputs += [binding(source / name) for name in contract["lf_sha256"]]
    inputs += [binding(prepared / name) for name in
               ("parser_declarations.inc", "production_parsers.inc", "production_converters.inc",
                "production_support.inc", "fixture_bytes.inc", "native_probe.cpp", "preparation.local.json")]
    for name, payload in generate.build_payloads().items():
        generate.require(prepare_native.raw_bounded(fixture / name) == payload, "original fixture differs")
        inputs.append(binding(fixture / name))
    for name in ("Run-H1Native.ps1", "H1Native.Core.ps1", "plan_native.py", "prepare_native.py",
                 "generate.py", "inspect_fixture.py", "native_probe.cpp", "native-source-contract.json",
                 "h1-xsurface-reviewed.patch"):
        inputs.append(binding(OWN / name))
    inputs += [binding(providers / name, sha) for name, sha in PROVIDERS.items()]
    inputs.append(binding(job, JOB_SHA))
    compiler_dir = vc / "bin/Hostx64/x64"
    # Pin executable/compiler anchors. System/SDK closure is not claimed hermetic.
    for name in ("cl.exe", "link.exe", "c1xx.dll", "c2.dll", "mspdb140.dll", "msobj140.dll"):
        inputs.append(binding(compiler_dir / name))
    include = [vc / "include"] + [sdk / "Include" / sdk_version / n for n in ("ucrt", "shared", "um", "winrt")]
    libraries = [vc / "lib/x64", sdk / "Lib" / sdk_version / "ucrt/x64", sdk / "Lib" / sdk_version / "um/x64"]
    for directory in include + libraries:
        generate.require(generate.regular_ancestry(directory).is_dir(), "installed toolchain directory missing")
    for path in (vc / "include/vector", sdk / "Include" / sdk_version / "um/Windows.h",
                 sdk / "Lib" / sdk_version / "um/x64/user32.lib"):
        inputs.append(binding(path))
    compile_root = run / "compile"
    args = ["/nologo", "/std:c++20", "/EHsc", "/W4", "/MT", "/Od", "/Z7",
            "/I" + str(source / "src/zonetool"), "/I" + str(source / "src/common"),
            "/Fo" + str(compile_root / "native_probe.obj"), "/Fe" + str(compile_root / "native_probe.exe"),
            str(prepared / "native_probe.cpp"), "/link", "/INCREMENTAL:NO", "user32.lib"]
    return {"Schema": "iw7.h1-native-plan/1", "NativeExecuted": False, "LeaseAcquired": False,
            "Authorization": "Plan is not a native GO; invoke one stage only after coordinator approval",
            "RunRoot": str(run), "FixtureRoot": str(fixture), "PreparedRoot": str(prepared),
            "SourceRoot": str(source), "SourcePin": generate.PIN,
            "Runner": str(OWN / "Run-H1Native.ps1"), "Core": str(OWN / "H1Native.Core.ps1"),
            "Scheduler": str(providers / "ops/Resource-Scheduler.Core.ps1"), "JobAssembly": str(job),
            "Compiler": str(compiler_dir / "cl.exe"), "Executable": str(compile_root / "native_probe.exe"),
            "CompileArguments": args, "Include": ";".join(map(str, include)),
            "Lib": ";".join(map(str, libraries)), "CompilerDirectory": str(compiler_dir),
            "OutputLimitBytes": 32 * 1024**2, "MetadataReserveBytes": 1024**2,
            "Stages": {"Compile": {"Kind": "Build", "PhysicalBytes": 4 * 1024**3, "CommitBytes": 6 * 1024**3,
                                  "DeadlineSeconds": 120},
                       "Probe": {"Kind": "Analysis", "PhysicalBytes": 256 * 1024**2, "CommitBytes": 256 * 1024**2,
                                 "DeadlineSeconds": 15}},
            "CleanupSeconds": 5, "ParserPoolBytes": 1024**2, "CompilerProcesses": 1,
            "WholeZoneToolValidated": False, "EstimatesAreMeasured": False,
            "ToolchainFullyHermetic": False, "Bindings": inputs}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "prepared", "fixture", "providers", "job", "vc", "sdk", "run"):
        cli.add_argument("--" + name, type=Path, required=True)
    cli.add_argument("--sdk-version", default="10.0.26100.0")
    cli.add_argument("--output", type=Path, help="optional create-only local plan; stdout otherwise")
    args = cli.parse_args()
    plan = make_plan(args.source, args.prepared, args.fixture, args.providers, args.job,
                     args.vc, args.sdk, args.sdk_version, args.run)
    payload = (json.dumps(plan, indent=2) + "\n").encode()
    generate.require(len(payload) <= 128 * 1024, "plan exceeds 128 KiB")
    if args.output:
        generate.regular_ancestry(args.output)
        with args.output.open("xb") as stream:
            stream.write(payload)
        print(json.dumps({"Path": str(args.output), "SHA256": hashlib.sha256(payload).hexdigest(),
                          "Bindings": len(plan["Bindings"]), "NativeExecuted": False, "LeaseAcquired": False}))
    else:
        print(payload.decode(), end="")
