"""Bounded H1 client-trigger records -> named IW7 records, not a map/FF writer.

Fields and five flag mappings come from the pinned local ZoneTool source.
No Havok shapes, pointers, audio/vision settings or runtime acceptance are implied.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import stat
import struct

PIN = 'fab935826c898806855376662a8a03317b3ad8f1'
INPUT_SCHEMA = 'iw7.asset-bridge.h1-client-triggers/1'
TYPE_MAP = {0x1: 0x1, 0x4: 0x2, 0x8: 0x4, 0x10: 0x8, 0x20: 0x10}
SUPPORTED_TYPES = sum(TYPE_MAP)
MAX_BYTES = 1024 * 1024
LIMITS = {'count': 256, 'hullCount': 4096, 'slabCount': 16384}


def require(value, message):
    if not value:
        raise ValueError(message)


def fields(value, expected, label):
    require(type(value) is dict and set(value) == set(expected),
            label + ': exact supported fields required; unknown/missing fields refused')


def integer(value, low, high, label):
    require(type(value) is int and low <= value <= high, label + ': integer out of range')
    return value


def f32(value, label, nonnegative=False):
    require(type(value) in (int, float), label + ': number required')
    try:
        number = float(value)
        require(math.isfinite(number), label + ': finite number required')
        result = struct.unpack('<f', struct.pack('<f', number))[0]
    except (OverflowError, struct.error) as error:
        raise ValueError(label + ': outside finite float32 range') from error
    require(math.isfinite(result) and (number == 0 or result != 0),
            label + ': float32 overflow/underflow refused')
    require(not nonnegative or result >= 0, label + ': negative extent refused')
    return result


def vector(value, label, nonnegative=False):
    require(type(value) is list and len(value) == 3, label + ': exactly three values required')
    return [f32(item, label, nonnegative) for item in value]


def convert_type(flags):
    integer(flags, 0, 2**31 - 1, 'triggerType')
    require(flags & ~SUPPORTED_TYPES == 0,
            'Unsupported H1 triggerType bits (LIGHTSET/CLUT/CONTEXT/WATER/unknown)')
    return sum(target for source, target in TYPE_MAP.items() if flags & source)


def span(record, first, count, length, label):
    start = integer(record[first], 0, 65535, label + '.' + first)
    size = integer(record[count], 0, 65535, label + '.' + count)
    require(start + size <= length, label + ': referenced range exceeds array')
    return start, size


def convert(source):
    fields(source, ('schema', 'trigger', 'triggerType'), 'root')
    require(source['schema'] == INPUT_SCHEMA, 'Unsupported input schema')
    trigger = source['trigger']
    fields(trigger, ('count', 'models', 'hullCount', 'hulls', 'slabCount', 'slabs'), 'trigger')
    for count, name in (('count', 'models'), ('hullCount', 'hulls'), ('slabCount', 'slabs')):
        size = integer(trigger[count], 0, LIMITS[count], count)
        require(type(trigger[name]) is list and len(trigger[name]) == size,
                name + ': declared count differs from array')
    types = source['triggerType']
    require(type(types) is list and len(types) == trigger['count'],
            'triggerType: one explicit entry per model required')
    output_types = [convert_type(value) for value in types]
    models, hulls, slabs = [], [], []
    for record in trigger['models']:
        fields(record, ('contents', 'hullCount', 'firstHull'), 'model')
        first, count = span(record, 'firstHull', 'hullCount', trigger['hullCount'], 'model')
        models.append({'contents': integer(record['contents'], -2**31, 2**31-1, 'model.contents'),
                       'hullCount': count, 'firstHull': first,
                       'windingCount': 0, 'firstWinding': 0, 'flags': 0,
                       'physicsAsset': None, 'physicsShapeOverrideIdx': 65535})
    for record in trigger['hulls']:
        fields(record, ('bounds', 'contents', 'slabCount', 'firstSlab'), 'hull')
        fields(record['bounds'], ('midPoint', 'halfSize'), 'bounds')
        first, count = span(record, 'firstSlab', 'slabCount', trigger['slabCount'], 'hull')
        hulls.append({'bounds': {'midPoint': vector(record['bounds']['midPoint'], 'bounds.midPoint'),
                                  'halfSize': vector(record['bounds']['halfSize'], 'bounds.halfSize', True)},
                      'contents': integer(record['contents'], -2**31, 2**31-1, 'hull.contents'),
                      'slabCount': count, 'firstSlab': first})
    for record in trigger['slabs']:
        fields(record, ('dir', 'midPoint', 'halfSize'), 'slab')
        direction = vector(record['dir'], 'slab.dir')
        require(any(value != 0 for value in direction), 'slab.dir: zero direction unsupported')
        slabs.append({'dir': direction, 'midPoint': f32(record['midPoint'], 'slab.midPoint'),
                      'halfSize': f32(record['halfSize'], 'slab.halfSize', True)})
    return {'schema': 'iw7.asset-bridge.iw7-client-trigger-records/1', 'source_pin': PIN,
            'runtime_ready': False, 'scope': 'client-trigger geometry/type records only; not MapEnts, Havok or FF',
            'trigger': {'count': len(models), 'models': models, 'hullCount': len(hulls),
                        'hulls': hulls, 'slabCount': len(slabs), 'slabs': slabs,
                        'windingCount': 0, 'windings': [], 'windingPointCount': 0, 'windingPoints': []},
            'triggerType': output_types}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def parse(data):
    require(type(data) is bytes and len(data) <= MAX_BYTES, 'Input exceeds 1 MiB')
    try:
        text = data.decode('utf-8-sig')
        depth, quoted, escaped = 0, False, False
        for character in text:
            if quoted:
                if escaped:
                    escaped = False
                elif character == '\\':
                    escaped = True
                elif character == '"':
                    quoted = False
            elif character == '"':
                quoted = True
            elif character in '{[':
                depth += 1
                require(depth <= 16, 'JSON nesting exceeds supported 16 levels')
            elif character in '}]':
                depth -= 1
        return json.loads(text, object_pairs_hook=unique_object,
                          parse_constant=lambda value: require(False, 'Nonfinite JSON constant'))
    except (UnicodeError, RecursionError) as error:
        raise ValueError('Invalid/beyond-depth JSON input') from error


def checked_path(value, exists):
    path = Path(value)
    require(path.is_absolute() and '..' not in path.parts, 'Absolute nontraversing paths required')
    for part in (path, *path.parents) if exists else path.parents:
        info = part.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not (getattr(info, 'st_file_attributes', 0) & 0x400),
                'Link/reparse ancestry refused')
        if part != path:
            require(stat.S_ISDIR(info.st_mode), 'Directory ancestry required')
    if exists:
        require(stat.S_ISREG(path.stat().st_mode), 'Regular input file required')
    return path


def write_conversion(input_path, output_path):
    source = checked_path(input_path, True)
    destination = checked_path(output_path, False)
    require(destination.suffix == '.json', 'Fresh .json output required; this is not a native asset writer')
    with source.open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    converted = convert(parse(data))
    converted['source_sha256'] = hashlib.sha256(data).hexdigest()
    result = (json.dumps(converted, indent=2, allow_nan=False) + '\n').encode('utf-8')
    require(len(result) <= 4 * MAX_BYTES, 'Output exceeds 4 MiB policy')
    with destination.open('xb') as stream:
        stream.write(result)
    return converted


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        write_conversion(args.input, args.output)
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + '\n')
