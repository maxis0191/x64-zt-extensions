"""Prepare original keyed input and exact pinned ZoneTool dump method, no build."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import stat
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PIN = 'fab935826c898806855376662a8a03317b3ad8f1'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def f32(number):
    return struct.unpack('<f', struct.pack('<f', number))[0]


def compile_original(clip):
    # Deliberately one fixed original asset, not a general animation compiler.
    require(clip == json.loads((HERE / 'fixtures/probe-clip.json').read_text()),
            'only the reviewed original probe profile is supported')
    require(clip['numframes'] == 30 and clip['framerate'] == 30 and
            clip['channels'] == ['tag_origin', 'tag_probe'] and
            clip['tag_probe_x_degrees'] == [[0, 0], [10, 45], [20, -45], [30, 0]] and
            clip['frequency'] == 1 and clip['root_motion'] is False and
            clip['translation_tracks'] is False and clip['loop'] is True and
            clip['notetrack'] == {'name': 'probe_contact', 'normalized_time': 0.5} and
            clip['name'] == 'paris_original_probe_bend' and clip['schema'] == 'iw7.original-keyed-probe/1',
            'original probe authoring contract changed')
    samples = []
    for _, angle in clip['tag_probe_x_degrees']:
        half = math.radians(angle) / 2
        # Exact float32 multiply/truncation of pinned QuatInt16::ToInt16.
        samples.extend(int(f32(f32(v) * 32767.0)) for v in (math.sin(half), 0, 0, math.cos(half)))
    return {'data_byte': [0, 10, 20, 30], 'data_short': [3],
            'random_data_short': samples, 'bone_counts': [1, 0, 1, 0, 0, 0, 0, 0, 2, 2]}


def dump_method(source_bytes):
    text = source_bytes.decode('utf-8').replace('\r\n', '\n').removesuffix('\n')
    signature = '\tvoid xanim_parts::dump(XAnimParts* asset)\n'
    require(text.count(signature) == 1 and text.endswith('\t}\n}'), 'unexpected pinned dump method shape')
    method = text[text.index(signature):-1]
    # Preserve the actual production method body, including every optional branch.
    return ('// Generated from verified pinned iw7/assets/xanim.cpp, body unchanged.\n'
            'namespace zonetool::iw7 {\n'
            'class xanim_parts { public: static void dump(XAnimParts* asset); };\n' + method + '}\n').encode()


def check_sources(root, references):
    contract = json.loads((HERE / 'source-contract.json').read_text())
    require(subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip() == PIN,
            'ZoneTool revision differs from prepared pin')
    hashes = {}
    for path, expected in contract['sha256'].items():
        data = (root / contract['path_prefix'] / path).read_bytes()
        require(sha(data) == expected, 'source hash mismatch: ' + path)
        hashes[contract['path_prefix'] + path] = expected
    extra = json.loads((HERE / 'probe-source-contract.json').read_text())
    for path, expected in extra['zonetool_sha256'].items():
        require(sha((root / path).read_bytes()) == expected, 'source hash mismatch: ' + path)
        hashes[path] = expected
    for item in extra['references']:
        require(sha((references / item['file']).read_bytes()) == item['sha256'],
                'reference hash mismatch: ' + item['file'])
    return hashes


def unlinked(path):
    for part in (path, *path.parents):
        if part.exists() or part.is_symlink():
            info = part.lstat()
            require(not part.is_symlink() and not (getattr(info, 'st_file_attributes', 0) &
                    getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024)), 'reparse output refused')


def prepare(source_root, reference_root, output):
    source_root, reference_root, output = Path(source_root), Path(reference_root), Path(output)
    require(source_root.is_absolute() and reference_root.is_absolute() and output.is_absolute(), 'absolute paths required')
    unlinked(output)
    require(not output.exists() and output.parent.is_dir(), 'fresh output directory in an existing parent required')
    hashes = check_sources(source_root, reference_root)
    clip = json.loads((HERE / 'fixtures/probe-clip.json').read_text())
    encoded = compile_original(clip)
    header = '#pragma once\nnamespace original_probe {\n'
    for name, values in encoded.items():
        type_name = 'char' if name == 'data_byte' else 'unsigned char' if name == 'bone_counts' else 'short'
        header += f'inline {type_name} {name}[] = {{{", ".join(map(str, values))}}};\n'
    header += '}\n'
    generated = {
        'probe_clip.hpp': header.encode(),
        'probe_dump.inc': dump_method((source_root / 'src/zonetool/zonetool/iw7/assets/xanim.cpp').read_bytes()),
        'probe-clip.json': (json.dumps(clip, indent=2) + '\n').encode(),
        'probe-zone.csv': b'xanim,paris_original_probe_bend\n',
    }
    manifest = {'schema': 'iw7.prepared-original-probe/1', 'zonetool_pin': PIN,
                'source_hashes': hashes, 'generated_sha256': {p: sha(b) for p, b in generated.items()},
                'writer_sha256': sha((HERE / 'writer_probe.cpp').read_bytes()),
                'abi_sha256': sha((HERE / 'probe_native_abi.hpp').read_bytes()),
                'native_build_executed': False, 'serializer_executed': False, 'runtime_verified': False,
                'frequency_candidate': 1.0, 'frequency_runtime_verified': False,
                'frequency_evidence_sha256': sha((HERE / 'frequency-observations.json').read_bytes()),
                'prepared_bytes': sum(map(len, generated.values()))}
    output.mkdir()
    for name, data in generated.items():
        with (output / name).open('xb') as stream:
            stream.write(data)
    with (output / 'prepared.json').open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=2)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True)
    parser.add_argument('--reference-root', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.source_root, args.reference_root, args.output), indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(json.dumps({'status': 'preparation-failed', 'error': str(exc)}))
        sys.exit(2)
