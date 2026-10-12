"""Internal phase of Run-RecipientClosure.ps1; outer BuildJob owns descendants.

No native process on import. Never invoke directly without the outer admitted job.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import threading
import time

from recipient_contract import EXE_SHA, check_output, command, require, sha, text, validate_requests

SDK_DRAIN_SHA = 'a2ab493cf551a43eea3797e5e8437e41aa8f0246d770838956d8984b68c4701d'


def run(spec, drain):
    require(spec['schema'] == 'iw7.recipient-phase/1' and spec['phase'] in ('references','script'), 'Exact recipient phase required')
    require(spec['timeout'] == 240 and spec['sha256'] == EXE_SHA, 'Pinned phase bounds/tool required')
    for field in ('exe','cwd','logs'):
        require(Path(spec[field]).is_absolute(), 'Absolute owned paths required')
    work = Path(spec['cwd'])
    exe = Path(spec['exe'])
    require(exe == work/'zonetool.exe' and exe.stat().st_size == 21696512 and sha(exe) == EXE_SHA, 'Staged E7 tool differs')
    validate_requests(text(work/'recipient-material.csv'), text(work/'recipient-scripts.txt'))
    logs = Path(spec['logs'])
    require(not logs.exists(), 'Fresh phase log directory required')
    logs.mkdir()
    exceeded = threading.Event()
    workers, handles = [], []
    # No shell or breakaway flag; native process inherits the original outer job.
    # Keep the unused stdin pipe open: the pinned console spins on EOF.
    process = subprocess.Popen(command(spec['phase'],exe),cwd=work,stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=0x08000000 if os.name == 'nt' else 0)
    for name,stream in (('stdout',process.stdout),('stderr',process.stderr)):
        handle = (logs/(name+'.log')).open('xb');handles.append(handle)
        worker = threading.Thread(target=drain,args=(stream,handle,exceeded),daemon=True)
        worker.start();workers.append(worker)
    failure = None
    deadline = time.monotonic()+240
    while process.poll() is None:
        if exceeded.is_set() or time.monotonic() >= deadline:
            failure = 'log limit/drain failure' if exceeded.is_set() else 'phase timeout'
            break
        time.sleep(.05)
    if failure is None:
        for worker in workers: worker.join(2)
        if exceeded.is_set() or any(worker.is_alive() for worker in workers): failure = 'drain failure or inherited pipe remains open'
    result = {'schema':'iw7.recipient-phase-result/1','phase':spec['phase'],'pid':process.pid,
              'exit_code':process.poll(),'failure':failure,'executable_sha256':EXE_SHA,
              'ownership':'outer original Windows job','log_limit_each':2097152,'observation':None}
    if failure is None and process.returncode == 0:
        try: result['observation'] = check_output(spec['phase'],work)
        except (ValueError,OSError) as error: result['failure'] = str(error)
    (logs/'phase.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if failure:
        os._exit(2)  # Outer owner stops its original job; never PID-based cleanup.
    for handle in handles: handle.close()
    process.stdin.close()
    return 0 if process.returncode == 0 and result['failure'] is None else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec',required=True,type=Path)
    parser.add_argument('--spec-sha256',required=True)
    parser.add_argument('--sdk-phase',required=True,type=Path)
    args = parser.parse_args()
    require(sha(args.spec) == args.spec_sha256 and sha(args.sdk_phase) == SDK_DRAIN_SHA, 'Phase/drain source changed')
    module_spec = importlib.util.spec_from_file_location('recipient_sdk_drain',args.sdk_phase)
    module = importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module)
    raise SystemExit(run(json.loads(text(args.spec)),module.copy_bounded))
