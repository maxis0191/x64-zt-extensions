"""C2: observe the existing DB_AddXAsset call; prepare source and parse text only."""
from pathlib import Path
import re
import prepare_cli

HERE = Path(__file__).resolve().parent
SCHEMA = 'iw7.t7-zm-add-observation/1'
SOURCE_PROFILE = 't7-zombies-catalogue-observation-c2'
MAX_LINES, MAX_LINE_BYTES, MAX_BYTES, COMBINED_MAX_BYTES = 10, 512, 8192, 16384
INCLUDES = '#include <intrin.h>\n#include <cerrno>\n#include <cstdio>\n#include <cwchar>\n'


def edits():
    original = '\t\treturn db_add_xasset_hook.invoke<XAssetHeader>(type, header);'
    wrapped = ('\t\tconst auto c2_call = c2_add_begin(xasset, _ReturnAddress());\n'
               '\t\tconst auto c2_result = db_add_xasset_hook.invoke<XAssetHeader>(type, header);\n'
               '\t\tc2_add_end(c2_call, c2_result);\n\t\treturn c2_result;')
    install = '\t\tdb_add_xasset_hook.create(0x1401D4600, &db_add_xasset_stub);'
    return ((install, install + '\n\t\tc2_add_enable();'),
            (original, wrapped))


def wire_cli(text):
    if type(text) is not str or '\r' in text or 'c2_add_' in text or 'zm_observation_' in text:
        raise ValueError('Fresh LF-only unobserved T7 CLI source required')
    for old, new in edits():
        text = prepare_cli.helper.once(text, old, new)
    module = (HERE / 'native_catalog_add_observation.inc').read_text(encoding='utf-8')
    namespace = 'namespace zonetool::t7\n{'
    return prepare_cli.helper.once(text, namespace,
        INCLUDES + '\n' + namespace + '\n' + '\n'.join('\t' + line if line else '' for line in module.splitlines()))


PREFIX = '[T7_ZM_ADD] schema=' + SCHEMA + ' '
POINTER = r'[0-9A-Fa-f]{16}'
TARGET_HEX = b'ui/uieditor/widgets/attachmentnamesdisplay.lua'.hex()
CONTEXT = (r'ff_state=(?P<ff_state>pointer_unreadable|null|name_unreadable|read|prefix) '
           r'ff_nul=(?P<ff_nul>[01]) ff_name_hex=(?P<ff_name_hex>[0-9a-f]{0,128}) ff_atomic=0')
PATTERNS = (
    r'kind=enabled',
    r'kind=selection_refused type=47 read_state=(?P<read_state>getter_exception|prefix_unreadable|name_unreadable) target=unknown',
    r'kind=add_enter call=(?P<call>[0-3]) type=47 reference_prefix=(?P<reference_prefix>[01]) '
    r'name_hex=(?P<name_hex>[0-9a-f]{92,94}) caller=(?P<caller>' + POINTER + r') asset=(?P<asset>' + POINTER + r') ' + CONTEXT,
    r'kind=add_return call=(?P<call>[0-3]) reference_prefix=(?P<reference_prefix>[01]) '
    r'result=(?P<result>' + POINTER + r') ' + CONTEXT,
)


def split_observation(text):
    """Return unchanged F text and finite C2 records; never declare catalogue success.

    An entry without a return is admissible incomplete evidence. A fastfile name
    is a non-atomic context snapshot, never an asset-provider or origin claim.
    """
    if type(text) is not str or len(text.encode('ascii')) > COMBINED_MAX_BYTES:
        raise ValueError('Bounded ASCII combined C2 trace required')
    legacy, records, sequences, entries, returns = [], [], set(), {}, set()
    byte_count, enabled, refused = 0, False, False
    for line in text.splitlines(keepends=True):
        if not line.startswith('[T7_ZM_ADD]'):
            legacy.append(line)
            continue
        if not line.endswith('\n') or len(line) > MAX_LINE_BYTES:
            raise ValueError('Complete bounded C2 line required')
        row = line.removesuffix('\n').removesuffix('\r')
        head = re.fullmatch(re.escape(PREFIX) + r'seq=(\d+) tid=(\d+) (.+)', row)
        if not head:
            raise ValueError('Exact C2 schema required')
        sequence, thread = map(int, head.groups()[:2])
        if sequence > 63 or sequence in sequences or not 0 < thread <= 0xffffffff:
            raise ValueError('C2 sequence/thread invalid or duplicated')
        sequences.add(sequence)
        body = head[3]
        match = next((m for pattern in PATTERNS if (m := re.fullmatch(pattern, body))), None)
        if not match:
            raise ValueError('Unknown C2 record')
        fields = {k: v for k, v in match.groupdict().items() if v is not None}
        kind = body.split(' ', 1)[0].removeprefix('kind=')
        for key in ('call', 'reference_prefix', 'ff_nul'):
            if key in fields:
                fields[key] = int(fields[key])
        if kind == 'enabled':
            if enabled or records:
                raise ValueError('One initial C2 enabled record required')
            enabled = True
        elif kind == 'selection_refused':
            if not enabled or refused:
                raise ValueError('One C2 selection refusal after enabled required')
            refused = True
        else:
            if not enabled:
                raise ValueError('C2 call before enabled record')
            state, name, nul = fields['ff_state'], fields['ff_name_hex'], fields['ff_nul']
            if len(name) % 2 or (state in ('pointer_unreadable', 'null', 'name_unreadable') and (name or nul)) or \
               (state == 'read' and (not nul or len(name) >= 128 or '00' in [name[i:i+2] for i in range(0,len(name),2)])) or \
               (state == 'prefix' and (nul or len(name) != 128 or '00' in [name[i:i+2] for i in range(0,len(name),2)])):
                raise ValueError('C2 fastfile state/name/termination differs')
            call = fields['call']
            correlation = (thread, fields['reference_prefix'])
            if kind == 'add_enter':
                if fields['name_hex'] != ('2c' if fields['reference_prefix'] else '') + TARGET_HEX:
                    raise ValueError('C2 selected name differs from exact target/prefix')
                if call in entries:
                    raise ValueError('Duplicate C2 call entry')
                entries[call] = correlation
            else:
                if call not in entries or entries[call] != correlation or call in returns:
                    raise ValueError('C2 return lacks matching unique entry')
                returns.add(call)
        byte_count += len(line)
        if byte_count > MAX_BYTES or len(records) >= MAX_LINES:
            raise ValueError('C2 observation cap exceeded')
        records.append(dict(kind=kind, sequence=sequence, thread=thread, **fields))
    return ''.join(legacy), records
