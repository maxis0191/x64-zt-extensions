"""Exact recipient CLI/output contract. Pure import; no native launch."""
import csv
import hashlib
import io
from pathlib import Path
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
    with Path(path).open('rb') as stream:
        data = stream.read(limit+1)
    require(len(data) <= limit, 'Text exceeds fixed recipient bound')
    return data.decode('utf-8-sig')


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
    size = path.stat().st_size
    require(str(size) == row['size_bytes'] and 35 <= size <= MAX_SCRIPT, 'Script byte size differs/exceeds native bound')
    with path.open('rb') as stream:
        require(stream.read(23) == MODULE.encode()+b'\0', 'Script content name differs')
        lengths = stream.read(12)
        require(len(lengths) == 12, 'Truncated ScriptFile lengths')
        compressed, source, bytecode = struct.unpack('<iii', lengths)
    require(all(0 <= n <= MAX_BUFFER for n in (compressed,source,bytecode)), 'ScriptFile length outside native bounds')
    require(size == 35+compressed+bytecode, 'ScriptFile representation has extra or missing bytes')
    actual = sha(path)
    require(actual == row['sha256'].lower(), 'Exact serialized ScriptFile hash differs')
    return {'module':MODULE, 'path':SCRIPT_PATH, 'bytes':size, 'sha256':actual,
            'compressed_len':compressed, 'source_len':source, 'bytecode_len':bytecode,
            'decompressed':False, 'transitive_imports_verified':False}


def check_output(phase, work):
    work = Path(work)
    if phase == 'references':
        path = work/'enemy-catalog'/f'{REFERENCE_NAME}.csv'
        result = reference_result(text(path))
    else:
        require(phase == 'script', 'Unknown recipient phase')
        path = work/'dump'/PACK/'scriptfile-manifest.csv'
        result = script_result(work,text(path))
    return {**result, 'manifest_path':path.relative_to(work).as_posix(), 'manifest_sha256':sha(path),
            'closure_complete':False, 'package_ready':False}
