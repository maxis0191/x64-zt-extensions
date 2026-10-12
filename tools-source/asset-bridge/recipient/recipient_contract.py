"""Exact recipient CLI/output contract. Pure import; no native launch."""
import csv
import hashlib
import io
import os
from pathlib import Path
import stat
import struct

EXE_SHA = 'e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04'
MODULE = 'scripts/engine/utility'
PACK = 'paris_enemy_cp_zmb_sdk_beacon_recipient_scripts'
REFERENCE_NAME = 'sdk_beacon_recipient_a'
REFERENCES = [('material','mopw/character_park_clown_zombie_shoes'),
              ('techset','mopw_l_sm_replace_i0c0s0o0n0p0'),
              ('image','park_clown_zombie_shoes_n_3e46d100_packed_nog'),
              ('image','park_clown_zombie_shoes_pink_c_park_clown_zombie_shoes_g_packed_cs')]
SCRIPT_PATH = f'dump/{PACK}/{MODULE}.gscbin'
MAX_BUFFER = 64*1024*1024
MAX_SCRIPT = len(MODULE.encode())+13+2*MAX_BUFFER


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1024*1024):
            result.update(block)
    return result.hexdigest()


def text(path, limit=16384):
    return text_snapshot(path, limit)[0]


def file_state(stream):
    info = os.fstat(stream.fileno())
    require(stat.S_ISREG(info.st_mode), 'Ordinary recipient file required')
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def read_up_to(stream, limit):
    """Accumulate short reads without requesting more than the remaining cap."""
    parts = []
    remaining = limit
    while remaining:
        block = stream.read(remaining)
        if not block:
            break
        require(len(block) <= remaining, 'Recipient stream exceeded requested bytes')
        parts.append(block)
        remaining -= len(block)
    return b''.join(parts)


def text_snapshot(path, limit=16384):
    """Digest and parse text from one bounded original descriptor snapshot."""
    with Path(path).open('rb', buffering=0) as stream:
        before = file_state(stream)
        require(before[2] <= limit, 'Text exceeds fixed recipient bound')
        data = read_up_to(stream, limit+1)
        require(len(data) <= limit, 'Text exceeds fixed recipient bound')
        require(before == file_state(stream) and len(data) == before[2], 'Recipient text changed during snapshot')
    return data.decode('utf-8-sig'), hashlib.sha256(data).hexdigest()


def validate_requests(materials, scripts):
    rows = list(csv.reader(io.StringIO(materials)))
    require(rows == [list(row) for row in REFERENCES], 'Exact ordered four-reference request required')
    require(scripts.replace('\r\n','\n') == MODULE+'\n', 'Exact extensionless utility request required')


def command(phase, exe):
    common = [str(exe), '-headless', '-unbuffered-io', '-strict-content-sources']
    if phase == 'references':
        return common+['-enemy-reference-check','cp_zmb','recipient-material.csv',REFERENCE_NAME]
    require(phase == 'script', 'Only two separately admitted recipient phases exist')
    return common+['-enemy-script-dump','cp_zmb','recipient-scripts.txt',PACK]


def reference_result(value):
    rows = list(csv.reader(io.StringIO(value)))
    require(rows and rows[0] == ['type','name','status'], 'Reference CSV header differs')
    require(rows[1:] == [[*row,'verified'] for row in REFERENCES], 'Four exact non-default verified rows required')
    return {'verified_references':4, 'serialized_content_observed':False}


def script_result(work, manifest):
    rows = list(csv.reader(io.StringIO(manifest)))
    header = ['donor_map','pack_name','module','status','path','size_bytes','sha256']
    require(len(rows) == 2 and rows[0] == header and len(rows[1]) == 7, 'Exactly one script row and exact columns required')
    row = dict(zip(header,rows[1]))
    require(row['donor_map'] == 'cp_zmb' and row['pack_name'] == PACK and row['module'] == MODULE and
            row['status'] == 'dumped' and row['path'] == SCRIPT_PATH, 'Exact successful utility export required')
    path = Path(work)/SCRIPT_PATH
    with path.open('rb', buffering=0) as stream:
        before = file_state(stream)
        size = before[2]
        require(str(size) == row['size_bytes'] and 35 <= size <= MAX_SCRIPT, 'Script byte size differs/exceeds native bound')
        header = read_up_to(stream, 35)
        require(len(header) == 35, 'Truncated ScriptFile header')
        require(header[:23] == MODULE.encode()+b'\0', 'Script content name differs')
        compressed, source, bytecode = struct.unpack('<iii', header[23:])
        require(all(0 <= n <= MAX_BUFFER for n in (compressed,source,bytecode)), 'ScriptFile length outside native bounds')
        require(size == 35+compressed+bytecode, 'ScriptFile representation has extra or missing bytes')
        digest = hashlib.sha256(header)
        remaining = size-35
        while remaining:
            block = stream.read(min(1024*1024, remaining))
            require(block and len(block) <= remaining, 'Truncated/invalid ScriptFile payload read')
            digest.update(block)
            remaining -= len(block)
        require(not stream.read(1), 'ScriptFile grew beyond its bounded representation')
        require(before == file_state(stream), 'ScriptFile identity/metadata changed during snapshot')
        actual = digest.hexdigest()
    require(actual == row['sha256'].lower(), 'Exact serialized ScriptFile hash differs')
    return {'module':MODULE, 'path':SCRIPT_PATH, 'bytes':size, 'sha256':actual,
            'compressed_len':compressed, 'source_len':source, 'bytecode_len':bytecode,
            'decompressed':False, 'transitive_imports_verified':False}


def check_output(phase, work):
    work = Path(work)
    if phase == 'references':
        path = work/'enemy-catalog'/f'{REFERENCE_NAME}.csv'
        manifest, manifest_hash = text_snapshot(path)
        result = reference_result(manifest)
    else:
        require(phase == 'script', 'Unknown recipient phase')
        path = work/'dump'/PACK/'scriptfile-manifest.csv'
        manifest, manifest_hash = text_snapshot(path)
        result = script_result(work,manifest)
    return {**result, 'manifest_path':path.relative_to(work).as_posix(), 'manifest_sha256':manifest_hash,
            'closure_complete':False, 'package_ready':False}
