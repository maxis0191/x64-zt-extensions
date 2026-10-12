"""One fixed animation profile over the existing bounded Beacon phase adapter.

No process owner, stock manager or new generic runner is implemented here.
"""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import sys

ZONE = 'sdk_animation_probe'


def phase_command(phase, executable, reader, redump):
    if phase == 'read':
        return [executable, '-B', str(reader), redump, '--expected-frequency', '1', '--ff-roundtrip']
    verbs = {'build': '-buildzone', 'verify': '-verifyzone', 'dump': '-dumpzone'}
    return [executable, '-headless', '-unbuffered-io', '-strict-content-sources', verbs[phase], ZONE]


def pinned(path, expected, limit):
    path = Path(path).resolve(strict=True)
    with path.open('rb') as stream:
        content = stream.read(limit + 1)
    if len(content) > limit or hashlib.sha256(content).hexdigest() != expected.lower():
        raise ValueError('Pinned bounded phase source differs')
    return path


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--shared-adapter', required=True)
    parser.add_argument('--shared-sha256', required=True)
    parser.add_argument('--reader-sha256', required=True)
    args, remaining = parser.parse_known_args()
    shared_path = pinned(args.shared_adapter, args.shared_sha256, 65536)
    reader = pinned(Path(__file__).with_name('read_probe.py'), args.reader_sha256, 65536)
    spec = importlib.util.spec_from_file_location('_animation_shared_phase', shared_path)
    shared = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shared)
    # Only the command factory differs. Keep its existing bounded drain,
    # timeouts, executable hashing, receipts and outer-job failure semantics.
    shared.command = lambda phase, exe, work, redump: phase_command(phase, exe, reader, redump)
    sys.argv = [str(shared_path)] + remaining
    return shared.main()


if __name__ == '__main__':
    raise SystemExit(main())
