"""Owned decoded component linkage. No IO, sampler, exporter or admission token.

The caller supplies the asset-bridge and t7-iw7 Source package roots. Two equal
bounded captures detect observed substitutions; they are not an atomic snapshot
of concurrently changing inputs. Only the retained owned capture reaches helpers.
"""
from dataclasses import dataclass
import hashlib
import math
import struct
from types import MappingProxyType

from animated.preflight import (ABSENT, CLIP_FIELDS, FLAGS, MAX_BYTES, PIN,
                                STREAMS, Refusal, preflight_clip, preflight_skeleton)
from .raygun.owned_skin_mapping import map_owned_source_surface


PROFILE = 'iw7.owned-rig-binding/1'
_U32 = (0, 2**32 - 1)
_SKELETON = (
    ('numBones', ('int', 2, 255)), ('numRootBones', ('int', *_U32)),
    ('numCosmeticBones', ('int', *_U32)), ('names', ('names',)),
    ('parentList', ('bytes', 254)), ('tagAngles', ('bytes', 8 * 254)),
    ('tagPositions', ('bytes', 12 * 254)), ('partClassification', ('bytes', 255)),
    ('baseMat', ('bytes', 32 * 255)), ('positionLayout', ('text',)),
)
_SHARED = tuple((name, ('int', *_U32)) for name in (
    'dataSize', 'flags', 'vertCount', 'indexCount', 'posOffset', 'vertsOffset',
    'skinWeightsOffset', 'indicesOffset'))
_SURFACE = tuple((name, ('int', *_U32)) for name in (
    'vertCount', 'triCount', 'baseVertOffset', 'baseIndexOffset', 'flags',
    'vertListCount')) + (('partBits', ('bytes', 48)),)
_FLOATS = ('framerate', 'frequency', 'primedLength', 'loopEntryTime')
_CLIP = tuple((name, ('bool',) if name in FLAGS + ABSENT else
               ('float',) if name in _FLOATS else
               ('bytes', MAX_BYTES) if name in STREAMS else
               ('names',) if name == 'names' else
               ('counts',) if name == 'boneCount' else ('int', *_U32))
              for name in CLIP_FIELDS)
_RECORDS = (('skeleton', _SKELETON), ('shared', _SHARED),
            ('surface', _SURFACE), ('clip', _CLIP))
_FALSE_FLAGS = (
    'ready', 'real_t7_provenance', 'complete_native_reader', 'native_payload_verified',
    'native_position_stride_verified', 'bind_hierarchy_consistency_verified',
    'clip_semantics_complete', 'key_schedule_verified', 'engine_verified',
    'production_admissible',
)


def _require(ok, code, detail):
    if not ok:
        raise Refusal(code, detail)


def _text(value):
    _require(type(value) is str and 0 < len(value) <= 128 and value.isascii()
             and all(32 < ord(c) < 127 for c in value), 'binding_text', 'bounded ASCII text')


def _value(value, rule, *, copy=False):
    kind = rule[0]
    if kind == 'int':
        _require(type(value) is int and rule[1] <= value <= rule[2],
                 'binding_integer', 'bounded exact int, never bool')
    elif kind == 'float':
        _require(type(value) is float and math.isfinite(value),
                 'binding_float', 'finite exact binary64 float; no integer coercion')
    elif kind == 'bool':
        _require(type(value) is bool, 'binding_boolean', 'exact bool')
    elif kind == 'bytes':
        _require(type(value) is bytes and len(value) <= rule[1],
                 'binding_bytes', 'bounded immutable bytes')
    elif kind == 'text':
        _text(value)
    elif kind in ('names', 'counts'):
        _require(type(value) is list, 'binding_list', 'exact builtin list')
        count = len(value)
        _require((2 <= count <= 255) if kind == 'names' else count == 10,
                 'binding_list_bound', 'bounded names or ten category counters')
        result = [] if copy else None
        for i in range(count):
            item = value[i]
            if kind == 'names':
                _text(item)
            else:
                _require(type(item) is int and 0 <= item <= 255,
                         'binding_integer', 'bounded exact category int')
            if copy:
                result.append(item)
        _require(len(value) == count, 'binding_changed', 'list changed during capture')
        return result
    else:
        raise AssertionError('closed internal field rule')
    return value


def _shape(value, fields):
    _require(type(value) is dict and len(value) == len(fields),
             'binding_schema', 'exact bounded builtin dict')
    allowed = frozenset(name for name, _ in fields)
    # Check key types and sizes before hashing/comparing caller-supplied keys.
    for key in value:
        _require(type(key) is str and len(key) <= 128,
                 'binding_schema', 'bounded exact string keys')
        _require(key in allowed, 'binding_schema', 'closed field schema')


def _record(value, fields, *, copy=False):
    _shape(value, fields)
    result = {} if copy else None
    byte_count = 0
    for name, rule in fields:
        item = value[name]
        checked = _value(item, rule, copy=copy)
        if rule[0] == 'bytes':
            byte_count += len(item)
        if copy:
            result[name] = checked
    _shape(value, fields)
    _require(byte_count <= MAX_BYTES, 'binding_byte_budget', 'aggregate record byte budget')
    return result


def _capture(skeleton, payload, shared, surface, clip):
    try:
        _require(type(payload) is bytes and 0 < len(payload) <= 256 * 1024,
                 'binding_payload', 'exact immutable payload, at most 256 KiB')
        values = (skeleton, shared, surface, clip)
        # Bound ALL five inputs before owned container copies or codec allocation.
        for value, (_, fields) in zip(values, _RECORDS):
            _record(value, fields)
        result = {name: _record(value, fields, copy=True)
                  for value, (name, fields) in zip(values, _RECORDS)}
        result['payload'] = payload  # Exact bytes are already immutable.
        return result
    except (IndexError, KeyError, RuntimeError) as error:
        raise Refusal('binding_changed', 'container changed during capture') from error


def _tlv(tag, payload):
    return tag + struct.pack('>I', len(payload)) + payload


def _encode_value(value):
    # Closed builtin types only. Values have been bounded before this allocation.
    if type(value) is bool:
        return _tlv(b'B', bytes((value,)))
    if type(value) is int:
        return _tlv(b'U', struct.pack('>I', value))
    if type(value) is float:
        return _tlv(b'F', struct.pack('>d', value))
    if type(value) is str:
        return _tlv(b'S', value.encode('ascii'))
    if type(value) is bytes:
        return _tlv(b'Y', value)
    if type(value) is list:
        return _tlv(b'L', struct.pack('>I', len(value)) + b''.join(map(_encode_value, value)))
    raise AssertionError('closed owned value codec')


def _encode(capture):
    prefix = PROFILE.encode('ascii') + b'\0' + PIN.encode('ascii') + b'\0'
    parts = {}
    for domain, fields in _RECORDS:
        body = b''.join(_tlv(b'K', name.encode('ascii')) + _encode_value(capture[domain][name])
                        for name, _ in fields)
        parts[domain] = prefix + _tlv(b'D', domain.encode('ascii')) + _tlv(b'R', body)
    parts['payload'] = prefix + _tlv(b'D', b'payload') + _encode_value(capture['payload'])
    parts['cohort'] = prefix + _tlv(b'D', b'cohort') + _tlv(b'C', b''.join(
        _tlv(b'K', key.encode('ascii')) + _tlv(b'V', parts[key])
        for key in ('skeleton', 'payload', 'shared', 'surface', 'clip')))
    return parts


def _observe(skeleton, payload, shared, surface, clip):
    first = _capture(skeleton, payload, shared, surface, clip)
    second = _capture(skeleton, payload, shared, surface, clip)
    encoded = _encode(first)
    _require(encoded == _encode(second), 'binding_changed', 'two typed captures differ')
    return first, encoded


def _freeze(value):
    if type(value) is dict:
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if type(value) in (list, tuple):
        return tuple(map(_freeze, value))
    _require(value is None or type(value) in (str, bytes, int, float, bool),
             'binding_result_type', 'closed helper result types')
    return value


@dataclass(frozen=True, slots=True)
class OwnedRigBinding:
    """Immutable data report, never a native permission or provenance credential."""
    profile: str
    source_pin: str
    identities: object
    inputs: object
    parent_indices: tuple
    clip_channel_to_model_bone: tuple
    mapped: object
    skeleton_checks: object
    clip_checks: object
    qualification: object


def bind_owned_rig(skeleton, payload, shared, surface, clip):
    """Link one authored decoded rig/surface/clip; retain all native refusals."""
    owned, encoded = _observe(skeleton, payload, shared, surface, clip)
    s, c = owned['skeleton'], owned['clip']
    skeleton_checks = preflight_skeleton(s)
    mapped = map_owned_source_surface(owned['payload'], owned['shared'], owned['surface'], s['names'])
    clip_checks = preflight_clip(c, s['names'])
    lookup = {name: i for i, name in enumerate(s['names'])}
    return OwnedRigBinding(
        PROFILE, PIN, _freeze({key: hashlib.sha256(value).hexdigest() for key, value in encoded.items()}),
        _freeze(owned), (None,) + tuple(i - distance for i, distance in enumerate(s['parentList'], 1)),
        tuple(lookup[name] for name in c['names']), _freeze(mapped),
        _freeze(skeleton_checks), _freeze(clip_checks),
        _freeze({key: False for key in _FALSE_FLAGS}))


def require_same_inputs(plan, skeleton, payload, shared, surface, clip):
    """Refuse reuse against any changed typed input; this is not an admission gate."""
    _require(type(plan) is OwnedRigBinding, 'binding_plan', 'exact binding report required')
    _, encoded = _observe(skeleton, payload, shared, surface, clip)
    _require(plan.profile == PROFILE and plan.source_pin == PIN and
             dict(plan.identities) == {key: hashlib.sha256(value).hexdigest()
                                       for key, value in encoded.items()},
             'stale_rig_binding', 'input identities differ from the retained plan')
