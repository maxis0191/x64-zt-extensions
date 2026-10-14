"""One read-only modal snapshot of the caller's verified original target.

Reuse recipient Win32Reader primitives unchanged. No DLL/process/window action
occurs on import; the original H1 caller supplies the identity under admission.
"""
import argparse
import json
import ntpath
from pathlib import Path
import sys
import time


def capture(api, handle, expected, digest, clock=time.monotonic):
    helper = api.identity(api.current_handle())
    target = api.identity(handle)
    fields = ('pid', 'parent_pid', 'created_filetime')
    if (any(target[name] != expected[name] for name in fields)
            or ntpath.normcase(target['image']) != ntpath.normcase(expected['image'])
            or helper['parent_pid'] != expected['parent_pid']):
        raise OSError('Original target/creator identity differs')
    record = {'schema': 'iw7.world-modal-window/1', 'identity': target,
              'helper': helper, 'modal_window_observed': False,
              'identity_verified_after': False, 'hwnd': None, 'title': None,
              'class': None, 'controls': [], 'text_bytes': 0, 'errors': [],
              'text_truncated': False, 'window_limit': 8, 'control_limit': 8,
              'text_limit': 16 * 1024, 'message_timeout_ms': 200,
              'whole_capture_deadline_guaranteed': False,
              'interaction_performed': False, 'material_reference_measured': False,
              'DirectJobMembershipQueried': False}

    def verify(hwnd=None):
        if api.identity(handle) != target or api.identity(api.current_handle()) != helper:
            raise OSError('Original process identity changed')
        if hwnd is not None and api.window_owner(hwnd) != target['pid']:
            raise OSError('Modal HWND was reassigned')

    def take(value):
        raw = value.encode('utf-8', 'replace')
        remaining = record['text_limit'] - record['text_bytes']
        selected = raw[:remaining].decode('utf-8', 'ignore')
        record['text_bytes'] += len(selected.encode('utf-8'))
        record['text_truncated'] |= len(raw) > remaining
        return selected

    try:
        verify()
        if digest(target['image']).lower() != expected['sha256'].lower():
            raise OSError('Original image hash changed')
        for hwnd in api.windows(target['pid'])[:8]:
            verify(hwnd)
            kind = api.class_name(hwnd)
            verify(hwnd)
            if kind != '#32770':
                continue
            caption = api.caption(hwnd)
            verify(hwnd)
            record.update(modal_window_observed=True, hwnd=hwnd,
                          title=take(caption), **{'class': take(kind)})
            deadline = clock() + 2.0
            for child in api.children(hwnd)[:8]:
                if clock() >= deadline or record['text_bytes'] >= record['text_limit']:
                    record['text_truncated'] = True
                    break
                verify(hwnd)
                if api.window_owner(child) != target['pid'] or not api.is_child(hwnd, child):
                    raise OSError('Child control ownership changed')
                child_kind = api.class_name(child)
                verify(hwnd)
                if api.window_owner(child) != target['pid'] or not api.is_child(hwnd, child):
                    raise OSError('Child control reassigned before text read')
                text, saturated, error = '', False, None
                if child_kind.casefold() == 'static':
                    try:
                        text, saturated = api.static_text(child)
                    except OSError as failure:
                        error = str(failure)[:160]
                verify(hwnd)
                if api.window_owner(child) != target['pid'] or not api.is_child(hwnd, child):
                    raise OSError('Child control reassigned during read')
                if api.class_name(child) != child_kind:
                    raise OSError('Child control class changed during read')
                record['text_truncated'] |= saturated
                record['controls'].append({'hwnd': child, 'class': take(child_kind),
                                           'text': take(text), 'buffer_saturated': saturated,
                                           'error': error})
            verify(hwnd)
            if api.class_name(hwnd) != '#32770' or api.caption(hwnd) != caption:
                raise OSError('Modal window changed during snapshot')
            verify(hwnd)
            break  # One owned dialog only, regardless of its caption.
        verify(record['hwnd'])
        if digest(target['image']).lower() != expected['sha256'].lower():
            raise OSError('Original image hash changed after read')
        record['identity_verified_after'] = True
    except BaseException as failure:
        # Never attribute text if a process/HWND check failed or was unavailable.
        record.update(hwnd=None, title=None, **{'class': None}, controls=[], text_bytes=0)
        record['errors'].append(type(failure).__name__)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('pid', 'parent-pid', 'created-filetime'):
        parser.add_argument('--' + name, type=int, required=True)
    for name in ('image', 'created', 'sha256', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    if min(args.pid, args.parent_pid, args.created_filetime) <= 0:
        raise ValueError('Positive original target identities required')
    package = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(package / 'ops'))
    sys.path.insert(0, str(package / 'tools-source/asset-bridge/recipient'))
    from iw7_capture import Observer
    from iw7_debugger import digest, local_output
    from recipient_dialog import Win32Reader, save_record
    output = local_output(args.output)
    observer = Observer(args.pid, args.image, args.created, args.sha256)
    try:
        expected = dict(pid=args.pid, parent_pid=args.parent_pid,
                        created_filetime=args.created_filetime, image=args.image,
                        sha256=args.sha256)
        record = capture(Win32Reader(), observer.handle, expected, digest)
        save_record(output, record)
        print(json.dumps({'output': str(output),
                          'modal_window_observed': record['modal_window_observed'],
                          'identity_verified_after': record['identity_verified_after']}))
        return 0 if record['identity_verified_after'] else 1
    finally:
        observer.close()  # Only this observer's read-only handle.


if __name__ == '__main__':
    raise SystemExit(main())
