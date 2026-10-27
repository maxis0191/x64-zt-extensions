"""Prepare an isolated full ZoneTool candidate with the bounded world observer."""
import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from prepare_full_build import digest, prepare, q
from verify_full_overlay import verify

WORLD = Path(__file__).resolve().parent.parent / 'world'
sys.path.insert(0, str(WORLD))
import verify_observer_patch as observer


def prepare_observer(source, output):
    source = source.resolve(strict=True)
    output = output.resolve()
    # This checks the pinned source, patch, header and forward-once source seam.
    receipt = observer.verify(source)
    prepare(source, output)
    verify(output)
    project = output / 'zonetool-community.vcxproj'
    prep_path = output / 'preparation.local.json'
    prep = json.loads(prep_path.read_text(encoding='utf-8'))
    tree = ET.parse(project)
    original = (source / observer.SOURCE).resolve(strict=True)
    entries = [node for node in tree.getroot().iter(q('ClCompile'))
               if node.get('Include') and Path(node.get('Include')).resolve() == original]
    if len(entries) != 1:
        raise ValueError('Expected one IW7 ZoneTool compilation unit')
    source_bytes = observer.read_source(original)
    header_bytes = observer.read_source(WORLD / 'world_clipmap_observer.hpp')
    patched = observer.transform(source_bytes.decode()).encode()
    if observer.sha(patched) != receipt['patched_lf_sha256']:
        raise ValueError('Observer source identity differs')
    unit = output / 'world-observer-zonetool.cpp'
    header = output / 'common' / 'world_clipmap_observer.hpp'
    header.parent.mkdir()
    unit.write_bytes(patched)
    header.write_bytes(header_bytes)
    entry = entries[0]
    entry.set('Include', str(unit))
    includes = ET.SubElement(entry, q('AdditionalIncludeDirectories'))
    includes.text = str(output) + ';' + str(original.parent) + ';%(AdditionalIncludeDirectories)'
    ET.indent(tree, space='  ')
    tree.write(project, encoding='utf-8', xml_declaration=True)
    prep['patched_units'] = 6
    prep['project_sha256'] = digest(project)
    prep['world_observer'] = receipt
    for path in (original, unit, header):
        prep['readonly_inputs'].append({'path': str(path), 'bytes': path.stat().st_size,
                                        'sha256': digest(path)})
    prep_path.write_text(json.dumps(prep, indent=2) + '\n', encoding='utf-8')
    verify(output)
    print(json.dumps({'world_observer': True, 'source_pin': prep['source_pin'],
                      'project_sha256': prep['project_sha256'], 'compiled': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    prepare_observer(args.source, args.output)
