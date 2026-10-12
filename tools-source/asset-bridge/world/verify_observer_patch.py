"""Verify a prepared private patch on two temporary source files; never build/run it."""
import argparse
import difflib
import json
from pathlib import Path
import tempfile

from verify_source import PIN, git, read_source, sha
from trigger_bridge import require

ROOT = Path(__file__).resolve().parent
SOURCE = 'src/zonetool/zonetool/iw7/zonetool.cpp'
HEADER = 'src/zonetool/zonetool/iw7/common/world_clipmap_observer.hpp'
PATCH = ROOT / 'zonetool-fab9358-world-observer.patch'
INVOKE = '\t\treturn db_add_xasset_hook.invoke<XAssetHeader>(type, header);\n'
FORWARD = '''\t\treturn world_clip_observer::forward(static_cast<int>(type), header,
\t\t\t[&]() { return db_add_xasset_hook.invoke<XAssetHeader>(type, header); },
\t\t\t[](const XAssetHeader& value) noexcept { return reinterpret_cast<std::uintptr_t>(value.data); });
'''
COMMAND = '''\tbool run_world_clipmap_observation(const std::vector<std::string>& args)
\t{
\t\ttry
\t\t{
\t\t\t// A dedicated, mutually exclusive CLI mode: no concurrent dump/build commands.
\t\t\tif (args.size() != 5 || args[1] != "-headless" || args[2] != "-world-clipmap-observe")
\t\t\t\tthrow std::runtime_error("usage: -headless -world-clipmap-observe <Zombies-map> <exact-clipmap-name>");
\t\t\t(void)enemy_definition_table_for_map(args[3]);
\t\t\tif (!zone_exists(args[3])) throw std::runtime_error("Requested world zone is unavailable");
\t\t\tglobals.target_game = game::iw7;
\t\t\tglobals.dump = globals.dump_csv = globals.verify = false;
\t\t\tasset_type_filter.clear();
\t\t\tif (!world_clip_observer::arm(args[4])) return false;
\t\t\tload_enemy_source_zones(args[3]);
\t\t\twait_for_database();
\t\t\treturn world_clip_observer::finish();
\t\t}
\t\tcatch (const std::exception& error) { ZONETOOL_ERROR("World observer failed: %s", error.what()); }
\t\tcatch (...) { ZONETOOL_ERROR("World observer failed with an unknown error"); }
\t\t(void)world_clip_observer::finish();
\t\treturn false;
\t}

'''
DISPATCH = '''\t\tif (std::find(args.begin(), args.end(), "-world-clipmap-observe") != args.end())
\t\t{
\t\t\tconst bool complete = run_world_clipmap_observation(args);
\t\t\tfflush(nullptr);
\t\t\tstd::quick_exit(complete ? EXIT_SUCCESS : EXIT_FAILURE);
\t\t}
'''


def replace_one(text, old, new):
    require(text.count(old) == 1, 'Expected unique source anchor differs')
    return text.replace(old, new, 1)


def transform(text):
    text = replace_one(text, '#include "common/havok.hpp"\n',
                       '#include "common/havok.hpp"\n#include "common/world_clipmap_observer.hpp"\n')
    text = replace_one(text, INVOKE, FORWARD)
    text = replace_one(text, '\tvoid handle_params()\n', COMMAND + '\tvoid handle_params()\n')
    text = replace_one(text, '\t\tauto args = get_command_line_arguments();\n',
                       '\t\tauto args = get_command_line_arguments();\n' + DISPATCH)
    return text


def patch_bytes(source, header):
    diff = difflib.unified_diff(source.splitlines(True), transform(source).splitlines(True),
                                fromfile='a/' + SOURCE, tofile='b/' + SOURCE)
    addition = difflib.unified_diff([], header.splitlines(True), fromfile='/dev/null', tofile='b/' + HEADER)
    return (''.join(diff) + ''.join(addition)).encode()


def verify(source_repo, write_patch=False):
    source_repo = Path(source_repo)
    require(source_repo.is_absolute() and git(source_repo, 'rev-parse', 'HEAD') == PIN, 'Different source pin')
    contract = json.loads((ROOT / 'havok-audit-2026-10-12.json').read_text())
    source = read_source(source_repo / SOURCE)
    require(sha(source) == contract['source_lf_sha256'][SOURCE], 'Source body differs')
    header = read_source(ROOT / 'world_clipmap_observer.hpp')
    generated = patch_bytes(source.decode(), header.decode())
    if write_patch:
        with PATCH.open('xb') as stream:
            stream.write(generated)
    require(PATCH.read_bytes() == generated, 'Prepared patch differs from source/observer header')
    patched = transform(source.decode()).encode()
    require(patched.count(b'db_add_xasset_hook.invoke<XAssetHeader>(type, header)') == 1,
            'Original invocation must have one syntactic call site')
    require(header.count(b'const auto result = invoke();') == 1 and
            b'catch (...) { original_exception(token); throw; }' in header,
            'Forward-once control flow differs')
    with tempfile.TemporaryDirectory(prefix='.observer-source-', dir=ROOT) as temporary:
        temporary = Path(temporary).resolve()
        require(temporary.parent == ROOT, 'Unexpected temporary cleanup root')
        target, added = temporary / SOURCE, temporary / HEADER
        target.parent.mkdir(parents=True)
        added.parent.mkdir(parents=True)
        target.write_bytes(source)
        git(temporary, 'apply', '--check', str(PATCH))
        git(temporary, 'apply', str(PATCH))
        require(target.read_bytes() == patched and added.read_bytes() == header, 'Applied bytes differ')
        git(temporary, 'apply', '--reverse', '--check', str(PATCH))
        git(temporary, 'apply', '--reverse', str(PATCH))
        require(target.read_bytes() == source and not added.exists(), 'Reverse did not restore original')
    require(read_source(source_repo / SOURCE) == source and not (source_repo / HEADER).exists(),
            'Shared source changed')
    return {'schema': 'iw7.asset-bridge.world-observer-source/1', 'source_pin': PIN,
            'base_lf_sha256': sha(source), 'patched_lf_sha256': sha(patched),
            'header_lf_sha256': sha(header), 'patch_sha256': sha(generated),
            'apply_reverse': True, 'original_syntactic_call_sites': 1,
            'read_budget_bytes': 2048, 'metadata_budget_bytes': 4096,
            'native_compiled': False, 'native_harness_run': False, 'engine_observed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-repo', required=True)
    parser.add_argument('--write-patch', action='store_true', help='Create the owned patch; existing files refused')
    args = parser.parse_args()
    print(json.dumps(verify(args.source_repo, args.write_patch), indent=2))
