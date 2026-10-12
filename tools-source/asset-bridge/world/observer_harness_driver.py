"""One bounded compile/fixture sequence inside the existing original BuildJob.

Owns no job or lease and never kills a process. The PowerShell owner alone
authorizes the fixture after inspecting original-job members and guards its EXE.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import threading
import time

from check_observer_harness import validate, unique_object, require, TRANSCRIPT_LIMIT


def read_json(path, limit=65536):
    with Path(path).open('rb') as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, 'Protocol JSON byte bound')
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique_object)


def digest(path, limit=32 * 1024 * 1024):
    with Path(path).open('rb') as stream:
        raw = stream.read(limit + 1)
    require(0 < len(raw) <= limit, 'Pinned input byte bound')
    return hashlib.sha256(raw).hexdigest()


def publish(path, value):
    raw = (json.dumps(value, indent=2) + '\n').encode()
    require(len(raw) <= 65536, 'Protocol receipt byte bound')
    pending = Path(str(path) + '.pending')
    with pending.open('xb') as stream:
        stream.write(raw)
    require(not Path(path).exists(), 'Never overwrite a receipt')
    pending.rename(path)


def deadline(now, group_start, phase_start, phase):
    require(phase in ('compile', 'fixture', 'permit'), 'Unknown driver phase')
    limit = 10 if phase == 'fixture' else 90
    require(0 <= now - group_start < 120, 'World group deadline')
    require(0 <= now - phase_start < limit, 'World phase deadline')


def load_drain(path, expected):
    require(digest(path, 16384) == expected.lower(), 'Reviewed drain pin differs')
    spec = importlib.util.spec_from_file_location('world_reviewed_drain', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.copy_bounded


def run_phase(phase, exe, arguments, expected, root, drain, started,
              *, clock=time.monotonic, sleep=time.sleep, popen=subprocess.Popen):
    require(phase in ('compile', 'fixture'), 'Native phase allowlist')
    require(digest(exe) == expected.lower(), 'Executable pin differs')
    phase_start = clock()
    deadline(phase_start, started, phase_start, phase)
    env = os.environ.copy()
    for name in ('CL', '_CL_'):
        env.pop(name, None)
    env['PATH'] = str(Path(exe).parent) + os.pathsep + env.get('PATH', '')
    env['TMP'] = env['TEMP'] = str(root / 'tmp')
    process = popen([str(exe), *arguments], cwd=root, env=env, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, creationflags=0x08000000 if os.name == 'nt' else 0)
    exceeded = threading.Event()
    workers, handles = [], []
    failure = None
    try:
        for name, source in (('stdout', process.stdout), ('stderr', process.stderr)):
            handle = (root / f'{phase}.{name}.log').open('xb')
            handles.append(handle)
            worker = threading.Thread(target=drain, args=(source, handle, exceeded), daemon=True)
            worker.start(); workers.append(worker)
        while process.poll() is None:
            deadline(clock(), started, phase_start, phase)
            require(not exceeded.is_set(), 'Log limit or drain error')
            sleep(.02)
        require(process.returncode == 0, 'Native nonzero exit')
        # Enforce phase/group deadlines after exit and after each bounded drain.
        deadline(clock(), started, phase_start, phase)
        drain_end = clock() + 2
        for worker in workers:
            worker.join(max(0, min(drain_end - clock(), 2)))
            deadline(clock(), started, phase_start, phase)
        require(not exceeded.is_set() and not any(w.is_alive() for w in workers), 'Drain failure or inherited pipe')
    except Exception as error:
        failure = str(error)
    finally:
        for handle, worker in zip(handles, workers):
            if not worker.is_alive():
                handle.close()
    receipt = {'schema': 'iw7.material-v2-phase-result/1', 'phase': phase,
               'pid': process.pid, 'exit_code': process.poll(), 'failure': failure,
               'executable_sha256': expected, 'log_limit_each': 2 * 1024 * 1024,
               'ownership': 'outer original Windows job'}
    publish(root / f'{phase}.json', receipt)
    require(not failure, failure or 'Native phase failed')
    return receipt


def validate_spec(spec):
    require(spec.get('schema') == 'iw7.world-observer-driver/1', 'Driver schema')
    for key in ('root', 'compiler', 'fixture', 'drain'):
        require(isinstance(spec.get(key), str) and Path(spec[key]).is_absolute(), 'Absolute driver path')
    root = Path(spec['root'])
    require(Path(spec['fixture']) == root / 'observer.exe', 'Fixed owned fixture path')
    require(isinstance(spec.get('arguments'), list) and 1 <= len(spec['arguments']) <= 32 and
            all(isinstance(a, str) and 0 < len(a) <= 2048 and '\0' not in a for a in spec['arguments']), 'Compiler arguments')
    for key in ('compiler_sha256', 'drain_sha256', 'token'):
        value = spec.get(key)
        require(isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value), 'Driver pin/token')
    return spec


def validate_permit(permit, spec, fixture_hash):
    require(isinstance(permit, dict) and permit.get('schema') == 'iw7.world-observer-permit/1' and
            permit.get('token') == spec['token'], 'Fixture permit identity')
    require(permit.get('fixture_sha256') == fixture_hash, 'Guarded compiled fixture identity')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True, type=Path)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    require(os.name == 'nt', 'Windows original-job driver only')
    require(digest(args.spec, 65536) == args.sha256.lower(), 'Driver spec pin differs')
    spec = validate_spec(read_json(args.spec))
    root = Path(spec['root']); started = time.monotonic()
    try:
        (root / 'tmp').mkdir()
        drain = load_drain(spec['drain'], spec['drain_sha256'])
        run_phase('compile', spec['compiler'], spec['arguments'], spec['compiler_sha256'], root, drain, started)
        permit_path = root / 'fixture-go.json'
        while not permit_path.exists():
            deadline(time.monotonic(), started, started, 'permit')
            time.sleep(.02)
        permit = read_json(permit_path)
        fixture_hash = digest(spec['fixture'])
        validate_permit(permit, spec, fixture_hash)
        run_phase('fixture', spec['fixture'], [], fixture_hash, root, drain, started)
        with (root / 'fixture.stdout.log').open('rb') as stream:
            checked = validate(stream.read(TRANSCRIPT_LIMIT + 1))
        require(0 <= time.monotonic() - started < 120, 'World group deadline after parsing')
        publish(root / 'checked.json', checked)
        return 0
    except Exception as error:
        publish(root / 'driver-failure.json', {'schema': 'iw7.world-observer-failure/1', 'failure': str(error)[:2048]})
        # No process kill/wait escape: parent stops its retained original job.
        return 2


if __name__ == '__main__':
    os._exit(main())
