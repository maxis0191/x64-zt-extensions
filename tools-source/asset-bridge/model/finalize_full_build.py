"""Bind an already closed successful build to its real outputs; never execute it."""
import argparse
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from prepare_full_build import digest, q, run

def file_record(path):
    return {'path':str(path.resolve(strict=True)), 'bytes':path.stat().st_size, 'sha256':digest(path)}

def finalize(root):
    root = root.resolve(strict=True)
    destination = root / 'build-artifact.local.json'
    if destination.exists(): raise ValueError('Preserve the previous artifact receipt')
    prep_path, result_path = root / 'preparation.local.json', root / 'result.local.json'
    prep, result = json.loads(prep_path.read_text()), json.loads(result_path.read_text())
    assert prep['schema'] == 'iw7.zonetool-isolated-overlay/1'
    assert result['Schema'] == 'iw7.zonetool-full-build/1'
    assert result['Failure'] is None and result['ReadOnlyInputsUnchanged']
    assert result['LeaseReleased'] and result['JobClosureVerified']
    assert not result.get('AuditErrors') and not result.get('ReleaseError')
    attempt = result['Attempts'][-1]
    assert attempt['ExitCode'] == 0 and attempt['JobActiveAtClose'] == 0
    assert attempt['SchedulerAttached'] and attempt['Priority'] == 0x4000
    total = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    assert total < 1600*1024**2 and total < result['HardCeiling'] == 2*1024**3
    for item in prep['readonly_inputs']:
        assert digest(Path(item['path'])) == item['sha256'], item['path']
    project = root / 'zonetool-community.vcxproj'
    assert digest(project) == prep['project_sha256']
    inputs = {str(Path(n.attrib['Include'])).upper() for n in ET.parse(project).getroot().findall('.//' + q('ClCompile') + '[@Include]')}
    tlog = root / 'obj/tlog/CL.command.1.tlog'
    lines = tlog.read_text(encoding='utf-16').splitlines()
    entries = {}
    for i in range(0, len(lines), 2):
        assert lines[i].startswith('^') and i+1 < len(lines), 'Unexpected CL tlog structure'
        entries[lines[i][1:].upper()] = lines[i+1]
    assert len(inputs) == prep['compile_units'] == 413 and inputs <= entries.keys()
    for path in inputs:
        command = entries[path]
        assert re.search(r'/D\s+"?EXPERIMENTAL_IW7(?:"|\s|$)', command)
        assert not re.search(r'(^|\s)/MP(?:\d|\s|$)', command, re.I)
        assert re.search(r'(^|\s)/WX(?:\s|$)', command)
    pch_inputs = [p for p in inputs if p.endswith('\\STD_INCLUDE.CPP')]
    assert len(pch_inputs) == 1 and '/Yc"std_include.hpp"'.lower() in entries[pch_inputs[0]].lower()
    attempt_number = int(attempt['Attempt'])
    assert attempt_number == attempt['Attempt'] and attempt_number > 0
    log = root / f'build-{attempt_number}.log'
    log_text = log.read_text(encoding='utf-8-sig')
    assert re.search(r'\b0 Warning\(s\)', log_text) and re.search(r'\b0 Error\(s\)', log_text)
    artifact = {'schema':'iw7.zonetool-community-candidate/1',
        'executable':file_record(root / 'bin/zonetool-community.exe'),
        'pdb':file_record(root / 'bin/zonetool-community.pdb'),
        'preparation_sha256':digest(prep_path), 'result_sha256':digest(result_path),
        'macro_compiled':True, 'compile_units_verified':413, 'fresh_candidate_pch':True,
        'commands_tlog':file_record(tlog), 'build_log':file_record(log),
        'source_pin':prep['source_pin'], 'patch_sha256':prep['patches'],
        'helper_source_commit':run('git','rev-parse','HEAD',cwd=Path(__file__).resolve().parent),
        'candidate_bytes_observed_final':total,
        'reserved_physical_bytes':4*1024**3, 'reserved_commit_bytes':6*1024**3,
        'stop_threshold_bytes':1600*1024**2, 'hard_ceiling_bytes':2*1024**3,
        'limitations':['No executable runtime or FF build performed.',
            'H1 map layout compatibility was repaired from history; maps/collision/scriptables remain experimental and runtime-unvalidated.',
            'Model native fixture coverage is separate from FF loading, rendering, animation and owner acceptance.']}
    destination.write_text(json.dumps(artifact, indent=2)+'\n')
    print(json.dumps(artifact, indent=2))
    return artifact

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    finalize(parser.parse_args().root)
