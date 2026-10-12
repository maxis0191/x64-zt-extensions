"""Tiny anonymous-pipe experiment; no child process, retail input or debugger.

Loads the existing SDK drain by exact hash. The read1 proxy is an experiment,
not a change to the producer or provider.
"""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import threading

PIN = 'a2ab493cf551a43eea3797e5e8437e41aa8f0246d770838956d8984b68c4701d'


def observe(drain, method):
    read_fd, write_fd = os.pipe()
    entered, written, exceeded = threading.Event(), threading.Event(), threading.Event()
    source = os.fdopen(read_fd, 'rb')  # Same BufferedReader as default Popen PIPE.

    class Proxy:
        def read(self, size):
            entered.set()
            return getattr(source, method)(size)

    class Sink(io.BytesIO):
        def write(self, data):
            value = super().write(data)
            written.set()
            return value

    destination = Sink()
    worker = threading.Thread(target=drain, args=(Proxy(), destination, exceeded), daemon=True)
    worker.start()
    try:
        if not entered.wait(2):
            raise RuntimeError('Drain never entered its read')
        os.write(write_fd, b'x'*96)
        short_visible = written.wait(.2)
        short_bytes = len(destination.getvalue())
        if method == 'read':
            if short_visible or short_bytes:
                raise AssertionError('Pinned buffered read unexpectedly exposed short data')
            os.write(write_fd, b'y'*(4096-96))
            if not written.wait(2) or len(destination.getvalue()) != 4096:
                raise AssertionError('The exact 4096-byte block did not reach the sink')
        elif not short_visible or short_bytes != 96:
            raise AssertionError('read1 proxy failed to expose the short live pipe output')
        os.close(write_fd);write_fd = None
        worker.join(2)
        if worker.is_alive() or exceeded.is_set():
            raise AssertionError('Fixture drain did not close cleanly')
        return {'method':method,'short_chunk_bytes':96,'visible_before_eof_or_4096':short_visible,
                'bytes_before_eof_or_4096':short_bytes,'final_bytes':len(destination.getvalue()),
                'drain_closed':True,'limit_exceeded':False}
    finally:
        if write_fd is not None:
            os.close(write_fd)
        worker.join(2)
        if not worker.is_alive():
            source.close();destination.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-drain', required=True, type=Path)
    args = parser.parse_args()
    if hashlib.sha256(args.sdk_drain.read_bytes()).hexdigest() != PIN:
        raise ValueError('Reviewed SDK drain changed')
    spec = importlib.util.spec_from_file_location('sdk_drain', args.sdk_drain)
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    print(json.dumps({'sdk_drain_sha256':PIN,'child_processes_started':0,'native_target_started':False,
                      'provider_modified':False,'experiments':[observe(module.copy_bounded, method)
                       for method in ('read','read1')],
                      'limit':'Visibility behavior only; does not identify the recipient stall or prove any hidden log bytes existed.'},indent=2))


if __name__ == '__main__':
    main()
