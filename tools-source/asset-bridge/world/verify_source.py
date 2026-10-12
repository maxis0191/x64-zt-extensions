"""Check the local source pin and prepared patch without native compilation.

Only a temporary copy of one source file is patched and reverse-checked.
The shared ZoneTool checkout is never modified.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

from trigger_bridge import PIN, TYPE_MAP, require

ROOT = Path(__file__).resolve().parent
RELATIVE = 'src/zonetool/zonetool/h1/converter/iw7/assets/clipmap.cpp'
PATCH = ROOT / 'zonetool-fab9358-trigger-types.patch'
MARKER = '\t\t\tstd::uint8_t convert_trigger_type(std::int32_t flags)\n\t\t\t{\n'
GUARD = '''\t\t\t\t// Never silently erase H1-only or unknown trigger behavior.
\t\t\t\tconstexpr std::int32_t supported_flags =
\t\t\t\t\tzonetool::h1::CLIENT_TRIGGER_VISIONSET | zonetool::h1::CLIENT_TRIGGER_AUDIO |
\t\t\t\t\tzonetool::h1::CLIENT_TRIGGER_BLEND_VISION | zonetool::h1::CLIENT_TRIGGER_BLEND_AUDIO |
\t\t\t\t\tzonetool::h1::CLIENT_TRIGGER_NPC;
\t\t\t\tif (flags < 0 || (flags & ~supported_flags) != 0)
\t\t\t\t{
\t\t\t\t\tthrow std::runtime_error("Unsupported H1 client trigger type bits");
\t\t\t\t}

'''


def read_source(path):
    with Path(path).open('rb') as stream:
        value = stream.read(2 * 1024 * 1024 + 1)
    require(len(value) <= 2 * 1024 * 1024, 'Source file exceeds 2 MiB')
    return value.replace(b'\r\n', b'\n')


def sha(value):
    return hashlib.sha256(value).hexdigest()


def patched(source):
    require(source.count(MARKER) == 1, 'Converter function anchor differs')
    include = '#include "clipmap.hpp"\n'
    require(source.count(include) == 1, 'Converter include anchor differs')
    return source.replace(include, include + '#include <stdexcept>\n', 1).replace(MARKER, MARKER + GUARD, 1)


def patch_bytes(source):
    return ''.join(difflib.unified_diff(source.splitlines(keepends=True),
                                      patched(source).splitlines(keepends=True),
                                      fromfile='a/' + RELATIVE, tofile='b/' + RELATIVE)).encode('utf-8')


def enums(source):
    block = re.search(r'enum clientTriggerType_t[^\{]*\{(.*?)\};', source, re.S)
    require(block is not None, 'Trigger enum missing')
    return {name: int(number, 16) for name, number in
            re.findall(r'(CLIENT_TRIGGER_\w+)\s*=\s*(0x[0-9A-Fa-f]+)\s*,', block.group(1))}


def git(cwd, *args):
    result = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True,
                            check=True, timeout=20)
    return result.stdout.strip()


def verify(source_repo):
    source_repo = Path(source_repo)
    require(source_repo.is_absolute(), 'Absolute existing source repository required')
    require(git(source_repo, 'rev-parse', 'HEAD') == PIN, 'Different ZoneTool source pin')
    contract = json.loads((ROOT / 'source-contract.json').read_text())
    require(contract['source_pin'] == PIN, 'Contract pin differs')
    sources = {}
    for name, expected in contract['lf_sha256'].items():
        data = read_source(source_repo / name)
        require(sha(data) == expected, 'Source hash differs: ' + name)
        sources[name] = data.decode('utf-8')
    h1 = enums(sources['src/zonetool/zonetool/h1/structs.hpp'])
    iw7 = enums(sources['src/zonetool/zonetool/iw7/structs.hpp'])
    source = sources[RELATIVE]
    mappings = re.findall(r'convert\(zonetool::h1::clientTriggerType_t::(\w+), '
                          r'zonetool::iw7::clientTriggerType_t::(\w+)\);', source)
    require(len(mappings) == 5 and {h1[a]: iw7[b] for a, b in mappings} == TYPE_MAP,
            'Adapter mapping differs from the actual converter/enums')
    generated = patch_bytes(source)
    require(PATCH.read_bytes() == generated, 'Prepared patch differs from exact source transformation')
    with tempfile.TemporaryDirectory(prefix='.source-test-', dir=ROOT) as temporary:
        temporary = Path(temporary).resolve()
        require(temporary.parent == ROOT, 'Unexpected temporary cleanup root')
        target = temporary / RELATIVE
        target.parent.mkdir(parents=True)
        target.write_bytes(source.encode('utf-8'))
        git(temporary, 'apply', '--check', str(PATCH))
        git(temporary, 'apply', str(PATCH))
        require(target.read_bytes() == patched(source).encode('utf-8'), 'Applied patch bytes differ')
        git(temporary, 'apply', '--reverse', '--check', str(PATCH))
        git(temporary, 'apply', '--reverse', str(PATCH))
        require(target.read_bytes() == source.encode('utf-8'), 'Reversed patch bytes differ')
    require(read_source(source_repo / RELATIVE).decode('utf-8') == source, 'Shared source changed')
    return {'source_pin': PIN, 'files_verified': len(sources), 'mapping_entries': len(mappings),
            'base_lf_sha256': sha(source.encode()), 'patched_lf_sha256': sha(patched(source).encode()),
            'patch_sha256': sha(generated), 'patch_apply_reverse': True,
            'native_build': False, 'map_or_ff_test': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-repo', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.source_repo), indent=2))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(2, str(error) + '\n')
