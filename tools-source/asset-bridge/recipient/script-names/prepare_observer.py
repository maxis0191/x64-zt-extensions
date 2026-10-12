"""Render/check a single-source patch. Never applies it or invokes a compiler."""
import argparse
import difflib
import hashlib
from pathlib import Path
import os
import stat

HERE = Path(__file__).resolve().parent
SOURCE_SHA = 'f1c9fb861b81727dc7e3882f5116231e6dc0d1a0e6f5838953a62232171059bc'
SOURCE = 'src/zonetool/zonetool/iw7/zonetool.cpp'
LIMIT = 256 * 1024

def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Expected unique source anchor')
    return text.replace(old, new, 1)

def render(data):
    if len(data) > LIMIT or hashlib.sha256(data).hexdigest() != SOURCE_SHA:
        raise ValueError('Pinned native source bytes differ')
    text = data.decode('utf-8').replace('\r\n', '\n')
    original = text
    text = once(text, '#include <utils/cryptography.hpp>',
                '#include <utils/cryptography.hpp>\n#include "recipient_script_names.hpp"')
    observer = (HERE/'native_observer.inc').read_text(encoding='utf-8').replace('\r\n', '\n')
    anchor = '\tvoid dump_enemy_scripts('
    text = once(text, anchor, '\n'.join('\t'+line if line else '' for line in observer.splitlines())+'\n\n'+anchor)
    cli = (HERE/'native_cli.inc').read_text(encoding='utf-8').replace('\r\n', '\n')
    anchor = '\t\t\t\tif (args[i] == "-enemy-reference-check")'
    text = once(text, anchor, cli+'\n'+anchor)
    return original, text

def source_snapshot(path):
    path = Path(path).absolute()
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink() or ancestor.is_junction():
            raise ValueError('Redirected source path refused')
    with path.open('rb', buffering=0) as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > LIMIT:
            raise ValueError('Source file type/size refused')
        data = stream.read(LIMIT+1)
        after = os.fstat(stream.fileno())
        sig = lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        if len(data) != before.st_size or sig(before) != sig(after):
            raise ValueError('Source changed/truncated during snapshot')
    return data

def patch_for(data):
    before, after = render(data)
    return ''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),
                                      fromfile='a/'+SOURCE,tofile='b/'+SOURCE))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-repo', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    patch = patch_for(source_snapshot(args.source_repo/SOURCE))
    target = HERE/'zonetool-fab9358-script-names.patch'
    if args.check:
        if target.read_text(encoding='utf-8') != patch:
            raise SystemExit('Recorded patch differs')
    else:
        # Only this owned source artifact is written, never the native checkout.
        target.write_text(patch,encoding='utf-8',newline='\n')
    print(f'Patch {"checked" if args.check else "rendered"}: {len(patch.encode())} bytes; no compile/apply/run')
