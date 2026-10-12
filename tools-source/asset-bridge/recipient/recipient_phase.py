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
from datetime import datetime, timezone

from recipient_contract import EXE_SHA, check_output, command, require, sha, text, validate_requests

SDK_DRAIN_SHA = 'a2ab493cf551a43eea3797e5e8437e41aa8f0246d770838956d8984b68c4701d'
LOG_LIMIT = 2*1024*1024


class BoundedLogWriter:
    """Make the pinned drain's write-all assumption explicit for raw files.

    At most 16 writes per <=4096-byte drain chunk. Count actual accepted bytes,
    including a prefix preceding failure; never report a partial write complete.
    OSError is deliberate: the unchanged provider converts it to failed capture.
    """
    MAX_WRITE_CALLS = 16

    def __init__(self, raw, limit=LOG_LIMIT):
        self.raw = raw
        self.limit = limit
        self.bytes_written = 0
        self.failed = False
        self.drain_exception = None

    def write(self, data):
        if self.failed:
            raise OSError('Recipient log writer already failed')
        requested = len(data)
        try:
            if requested > 4096 or self.bytes_written+requested > self.limit:
                raise OSError('Recipient log chunk or total byte bound exceeded')
            view = memoryview(data)
            offset = 0
            for _ in range(self.MAX_WRITE_CALLS):
                if offset == requested:
                    return requested
                count = self.raw.write(view[offset:])
                if type(count) is not int or count <= 0 or count > requested-offset:
                    raise OSError('Recipient raw log write made invalid or zero progress')
                offset += count
                self.bytes_written += count
            if offset == requested:
                return requested
            raise OSError('Recipient raw log write retry bound exceeded')
        except OSError:
            self.failed = True
            raise

    def flush(self):
        try:
            self.raw.flush()
        except OSError:
            self.failed = True
            raise

    def fileno(self):
        return self.raw.fileno()

    def close(self):
        self.raw.close()


def guarded_drain(drain, source, destination, failed):
    """Report every exceptional worker exit to the phase's owning thread.

    The pinned provider handles OSError only. Record the exception type without
    invoking its potentially failing __str__; even SystemExit must fail capture.
    """
    try:
        drain(source, destination, failed)
    except BaseException as error:
        destination.failed = True
        destination.drain_exception = type(error).__name__[:128]
        failed.set()


def capture_streams(process, logs, drain, timeout, observe=None):
    """Bounded raw-pipe capture; caller still owns the original process/job.

    On timeout the native writer may remain live. Return that fact and keep
    already written bytes; never claim stream/job closure or kill a PID here.
    """
    exceeded = threading.Event()
    workers, handles = [], []
    for name,stream in (('stdout',process.stdout),('stderr',process.stderr)):
        # The provider flushes each write; raw destinations also preserve the
        # emitted prefix when timeout exits via os._exit without Python cleanup.
        handle = BoundedLogWriter((logs/(name+'.log')).open('xb', buffering=0));handles.append(handle)
        worker = threading.Thread(target=guarded_drain,args=(drain,stream,handle,exceeded),daemon=True)
        worker.start();workers.append(worker)
    failure = None
    deadline = time.monotonic()+timeout
    while process.poll() is None:
        if exceeded.is_set() or time.monotonic() >= deadline:
            failure = 'log limit/drain failure' if exceeded.is_set() else 'phase timeout'
            break
        if observe is not None:
            try: failure = observe()
            except BaseException as error: failure = 'diagnostic observer raised '+type(error).__name__[:128]
            if failure: break
        time.sleep(.05)
    if failure is None:
        for worker in workers: worker.join(2)
        if exceeded.is_set() or any(worker.is_alive() for worker in workers): failure = 'drain failure or inherited pipe remains open'
    if failure is None and any(h.failed or h.bytes_written != os.fstat(h.fileno()).st_size for h in handles):
        failure = 'log byte accounting differs from retained file'
    exceptions = [f'{name} drain raised {handle.drain_exception}'
                  for name,handle in zip(('stdout','stderr'),handles) if handle.drain_exception]
    if exceptions:
        failure = '; '.join(exceptions)
    return failure,workers,handles


def run(spec, drain):
    require(spec['schema'] == 'iw7.recipient-phase/1' and spec['phase'] in ('references','script'), 'Exact recipient phase required')
    require(spec.get('diagnostic_mode') in (None,'fatal-text'), 'Unknown diagnostic mode')
    diagnostic = spec.get('diagnostic_mode') == 'fatal-text'
    require(not diagnostic or spec['phase'] == 'references', 'Fatal diagnostic is references-only')
    require(spec['timeout'] == (45 if diagnostic else 240) and spec['sha256'] == EXE_SHA, 'Pinned phase bounds/tool required')
    for field in ('exe','cwd','logs'):
        require(Path(spec[field]).is_absolute(), 'Absolute owned paths required')
    work = Path(spec['cwd'])
    exe = Path(spec['exe'])
    require(exe == work/'zonetool.exe' and exe.stat().st_size == 21696512 and sha(exe) == EXE_SHA, 'Staged E7 tool differs')
    validate_requests(text(work/'recipient-material.csv'), text(work/'recipient-scripts.txt'))
    logs = Path(spec['logs'])
    require(not logs.exists(), 'Fresh phase log directory required')
    logs.mkdir()
    # bufsize=0 yields raw pipe reads: the pinned drain's read(4096) can return
    # available short output without waiting for 4096 bytes or process exit.
    # Stdin/CLI/creation flags remain exactly as in failed attempt A.
    process = subprocess.Popen(command(spec['phase'],exe),cwd=work,stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0,
        creationflags=0x08000000 if os.name == 'nt' else 0)
    start = {'phase':spec['phase'],'pid':process.pid,'parent_pid':os.getpid(),
             'image':str(exe),'executable_sha256':EXE_SHA,
             'spawn_observed_utc':datetime.now(timezone.utc).isoformat(),
             'creation_time_verified':False,'native_creation_utc':None,
             'stdin':'pipe-held-open','output_pipe_buffer_size':0,
             'ownership':'outer original Windows job'}
    (logs/'native-start.json').write_text(json.dumps(start,indent=2)+'\n',encoding='utf-8')
    probe = None
    dialog_record = None
    next_observation = 0
    def observe_dialog():
        nonlocal probe,dialog_record,next_observation
        if time.monotonic() < next_observation: return None
        next_observation = time.monotonic()+.25
        try:
            from recipient_dialog import make_probe
            if probe is None: probe = make_probe(process,exe,EXE_SHA)
            dialog_record = probe.poll()
        except BaseException as error:
            dialog_record = {'schema':'iw7.recipient-fatal-dialog/1','fatal_window_observed':False,
                             'identity_verified_after':False,'errors':[type(error).__name__[:128]]}
            return 'fatal-text observer failed'
        return 'fatal-text observer captured fatal window' if dialog_record is not None else None
    # The normal reference phase needs the same first-fatal evidence as the
    # forced diagnostic. Script export remains outside this observer's scope.
    observe_fatal = spec['phase'] == 'references'
    failure,workers,handles = capture_streams(process,logs,drain,spec['timeout'],observe_dialog if observe_fatal else None)
    if diagnostic:
        failure = failure or 'fatal-text diagnostic ended without fatal window; references not accepted'
        if dialog_record is None:
            dialog_record = {'schema':'iw7.recipient-fatal-dialog/1','fatal_window_observed':False,
                             'identity_verified_after':False,'errors':[], 'outcome':failure}
    if dialog_record is not None:
        from recipient_dialog import save_record
        save_record(logs/'fatal-dialog.json',dialog_record)
    result = {'schema':'iw7.recipient-phase-result/1','phase':spec['phase'],'pid':process.pid,
              'exit_code':process.poll(),'failure':failure,'executable_sha256':EXE_SHA,
              'ownership':'outer original Windows job','log_limit_each':2097152,'observation':None,
              'capture':{'pipe_buffer_size':0,'drain_threads_closed':not any(w.is_alive() for w in workers),
                         'stdout_bytes_at_receipt':(logs/'stdout.log').stat().st_size,
                         'stderr_bytes_at_receipt':(logs/'stderr.log').stat().st_size,
                         'tree_closure_verified':False}}
    if failure is None and process.returncode == 0:
        try: result['observation'] = check_output(spec['phase'],work)
        except (ValueError,OSError) as error: result['failure'] = str(error)
    (logs/'phase.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if diagnostic:
        # The original PowerShell job owner sees this only after both receipts.
        # Never terminate a process from the diagnostic reader or via a PID.
        (logs.parent/'diagnostic-stop.request').write_text('Fatal-text diagnostic finished; stop original job.\n',encoding='utf-8')
    elif dialog_record is not None:
        # Normal mode can succeed with no fatal. A fatal or reader/identity
        # failure instead preserves both receipts before requesting owned stop.
        (logs.parent/'fatal-stop.request').write_text('Fatal-text capture failed reference phase; stop original job.\n',encoding='utf-8')
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
