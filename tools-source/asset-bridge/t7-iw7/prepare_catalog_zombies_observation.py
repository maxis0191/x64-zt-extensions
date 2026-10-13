"""Opt-in source overlay for the failed zm_common catalogue; never builds or runs."""
from pathlib import Path
import re
import prepare_cli

HERE = Path(__file__).resolve().parent
SCHEMA = 'iw7.t7-zm-observation/1'
SOURCE_PROFILE = 't7-zombies-catalogue-observation-c'
PHASES = ('installed', 'start', 'handle_params', 'catalogue', 'wait_enter', 'wait_return',
          'load_enter', 'load_return', 'finish_enter', 'finish_return', 'zone_return', 'published',
          'donor_load_enter', 'donor_load_return')
INCLUDES = '#include <intrin.h>\n#include <type_traits>\n#include <cerrno>\n#include <cstdio>\n#include <cwchar>\n'


def edits():
    """Small, exact call-site changes; existing native/preparation contracts stay sealed."""
    phase = lambda name: f'zm_observation_phase_event(zm_observation_phase::{name});'
    callback = '\t\treturn db_finish_load_x_file_hook.invoke<void>(a1, a2);'
    wait = ('\tvoid wait_for_database()\n\t{\n\t\t// wait for database to be ready\n'
            '\t\twhile (!utils::hook::invoke<bool>(0x1405261E0))\n\t\t{\n\t\t\tSleep(5);\n\t\t}\n\t}')
    load_tail = ('\t\t//utils::hook::copy_string(0x14699D220, name.data());\n'
                 '\t\t//utils::hook::invoke<void>(0x1401DB0B0); // DB_LoadZone\n\n\t\treturn true;')
    return (
        ('\t\tinitialized = true;\n', '\t\tinitialized = true;\n\t\tzm_observation_install();\n'),
        ('\tvoid start()\n\t{', '\tvoid start()\n\t{\n\t\t' + phase('start')),
        ('\tvoid handle_params()\n\t{', '\tvoid handle_params()\n\t{\n\t\t' + phase('handle_params')),
        ('\tstatic void catalog_resident_models_iw7(const std::string& zone_arg)\n\t{',
         '\tstatic void catalog_resident_models_iw7(const std::string& zone_arg)\n\t{\n\t\t' + phase('catalogue')),
        (wait, wait.replace('// wait for database to be ready', phase('wait_enter') + '\n\t\t// wait for database to be ready')
         .replace('\n\t}', '\n\t\t' + phase('wait_return') + '\n\t}')),
        ('\tvoid db_finish_load_x_file_stub(void* a1, void* a2)\n\t{',
         '\tvoid db_finish_load_x_file_stub(void* a1, void* a2)\n\t{\n\t\t' + phase('finish_enter')),
        (callback, '\t\tdb_finish_load_x_file_hook.invoke<void>(a1, a2);\n\t\t' + phase('finish_return') + '\n\t\treturn;'),
        ('\t\tDB_LoadXAssets(&zone, 1, static_cast<qboolean>(sync), 0);',
         '\t\t' + phase('donor_load_enter') + '\n\t\tDB_LoadXAssets(&zone, 1, static_cast<qboolean>(sync), 0);\n\t\t' + phase('donor_load_return')),
        (load_tail, load_tail.replace('\t\treturn true;', '\t\t' + phase('zone_return') + '\n\t\treturn true;')),
        ('\t    zonetool::iw7::write_enemy_reference_output(root / "catalog.json", bytes);',
         '\t    zonetool::iw7::write_enemy_reference_output(root / "catalog.json", bytes);\n\t    ' + phase('published')),
    )


def wire_cli(text):
    """Caller supplies a reviewed final TU and binds returned bytes in a NEW plan."""
    if type(text) is not str or '\r' in text or 'zm_observation_' in text:
        raise ValueError('Fresh LF-only final T7 CLI source required')
    module = (HERE / 'native_catalog_zombies_observation.inc').read_text(encoding='utf-8')
    for old, new in edits():
        text = prepare_cli.helper.once(text, old, new)
    namespace = 'namespace zonetool::t7\n{'
    return prepare_cli.helper.once(text, namespace,
        INCLUDES + '\n' + namespace + '\n' + '\n'.join('\t' + line if line else '' for line in module.splitlines()))


PREFIX = '[T7_ZM_OBS] schema=' + SCHEMA + ' '
POINTER = r'[0-9A-Fa-f]{16}'  # Windows CRT %p; pointers are observations, never dereferenced here.
PATTERNS = (
    r'kind=phase phase=(?P<phase>\d+)',
    r'kind=raw_enter phase=(?P<phase>\d+) caller=(?P<caller>' + POINTER + r') type=47 error=(?P<error>[01]) wait=(?P<wait>-?\d+)',
    r'kind=raw_return phase=(?P<phase>\d+) result=(?P<result>' + POINTER + r')',
    r'kind=load_enter phase=(?P<phase>\d+) caller=(?P<caller>' + POINTER + r') count=(?P<count>\d+) sync=(?P<sync>-?\d+) suppress=(?P<suppress>-?\d+)',
    r'kind=load_return phase=(?P<phase>\d+)',
    r'kind=zone index=(?P<index>[01]) status=unreadable',
    r'kind=zone index=(?P<index>[01]) status=(?P<status>read|unreadable) nul=(?P<nul>[01]) name_hex=(?P<name_hex>[0-9a-f]{0,128}) alloc=(?P<alloc>\d+) free=(?P<free>\d+) alloc_slot=(?P<alloc_slot>\d+) free_slot=(?P<free_slot>\d+)',
)


def split_observation(text):
    """Validate/remove only this finite marker; return untouched legacy stderr and records.

    A future launcher must select a NEW profile/cap and validate its legacy part
    separately. This parser neither declares native success nor publishes a catalogue.
    """
    if type(text) is not str or len(text.encode('ascii')) > 16384:
        raise ValueError('Bounded ASCII combined trace required')
    legacy, records, sequences, phases = [], [], set(), set()
    byte_count = 0
    counts = {}
    for line in text.splitlines(keepends=True):
        if not line.startswith('[T7_ZM_OBS]'):
            legacy.append(line)
            continue
        if not line.endswith('\n') or len(line) > 512:
            raise ValueError('Complete bounded Zombies observation line required')
        row = line.removesuffix('\n').removesuffix('\r')
        head = re.fullmatch(re.escape(PREFIX) + r'seq=(\d+) tid=(\d+) (.+)', row)
        if not head:
            raise ValueError('Exact Zombies observation schema required')
        sequence, thread = map(int, head.groups()[:2])
        if sequence > 63 or sequence in sequences or not 0 < thread <= 0xffffffff:
            raise ValueError('Observation sequence/thread outside bounds or duplicated')
        sequences.add(sequence)
        body = head[3]
        match = next((m for pattern in PATTERNS if (m := re.fullmatch(pattern, body))), None)
        if not match:
            raise ValueError('Unknown Zombies observation record')
        fields = {k: v for k, v in match.groupdict().items() if v is not None}
        kind = body.split(' ', 1)[0].removeprefix('kind=')
        for key, value in tuple(fields.items()):
            if key not in ('caller', 'result', 'status', 'name_hex'):
                fields[key] = int(value)
                low, high = (-0x80000000, 0x7fffffff) if key in ('wait', 'sync', 'suppress') else (0, 0xffffffffffffffff)
                if not low <= fields[key] <= high:
                    raise ValueError('Observation integer outside native width')
        if ('phase' in fields and fields['phase'] >= len(PHASES)) or fields.get('count', 0) > 0xffffffff:
            raise ValueError('Observation phase/count outside native width')
        if kind == 'phase':
            if fields['phase'] in phases:
                raise ValueError('Duplicate one-shot phase')
            phases.add(fields['phase'])
        if 'name_hex' in fields:
            name = fields['name_hex']
            if len(name) % 2 or (fields['status'] == 'unreadable' and (name or fields['nul'])) or \
               (fields['status'] == 'read' and (len(name) == 128) != (fields['nul'] == 0)):
                raise ValueError('Observed name length/termination differs')
        counts[kind] = counts.get(kind, 0) + 1
        cap = len(PHASES) if kind == 'phase' else 8 if kind == 'zone' else 4
        if counts[kind] > cap:
            raise ValueError('Observation event cap exceeded')
        byte_count += len(line)
        if byte_count > 8192 or len(records) >= 38:
            raise ValueError('Observation trace cap exceeded')
        records.append(dict(kind=kind, sequence=sequence, thread=thread, **fields))
    return ''.join(legacy), records
