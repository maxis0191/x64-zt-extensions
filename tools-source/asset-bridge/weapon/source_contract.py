"""Reproduce the weapon animation schema from the retained ZoneTool source.

This parses source text only. It does not compile or execute the native reader.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

PIN = 'fab935826c898806855376662a8a03317b3ad8f1'
FILES = ('h1/assets/weapondef.hpp', 'h1/assets/weapondef.cpp', 'h1/structs.hpp',
         'iw7/assets/weapon_anim_package.cpp', 'iw7/assets/weapondef.cpp', 'iw7/structs.hpp')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bounded(path):
    with Path(path).open('rb') as stream:
        data = stream.read(2*1024*1024+1)
    require(len(data) <= 2*1024*1024, 'Input exceeds 2 MiB')
    return data


def enums(source, count):
    block = re.search(r'enum weapAnimFiles_t[^\{]*\{(.*?)\};', source, re.S)
    require(block is not None, 'Weapon enum missing')
    result = {}
    for symbol, number in re.findall(r'(\w+)\s*=\s*(-?\d+)\s*,', block.group(1)):
        value = int(number)
        if 0 <= value < count:
            require(value not in result, 'Aliased numeric slot requires explicit review')
            result[value] = symbol
    require(set(result) == set(range(count)), 'Enum slots are incomplete')
    return [result[i] for i in range(count)]


def names(source, count):
    block = re.search(r'anim_names\[NUM_WEAP_ANIMS\]\s*=\s*\{(.*?)\};', source, re.S)
    require(block is not None, 'JSON slot table missing')
    result = re.findall(r'"([A-Z0-9_]+)"', block.group(1))
    require(len(result) == count == len(set(result)), 'Invalid JSON slot names/count')
    return result


def build(root):
    root = Path(root)/'src/zonetool/zonetool'
    raw = {name: bounded(root/name) for name in FILES}
    text = {name: data.decode('utf-8-sig') for name, data in raw.items()}
    h1_names = names(text[FILES[0]], 190)
    h1_symbols = enums(text[FILES[2]], 190)
    iw7_names = names(text[FILES[3]], 260)
    iw7_symbols = enums(text[FILES[5]], 260)
    # The existing IW7 parser/writer uses these exact enum-symbol strings.
    require(iw7_names == iw7_symbols, 'IW7 JSON/enum identity changed')
    timer_block = re.search(r'struct WeaponAnimPackageStateTimers\s*\{(.*?)\};', text[FILES[5]], re.S)
    require(timer_block is not None, 'IW7 timer structure missing')
    timer_types = dict((name, kind) for kind, name in re.findall(r'\b(unsigned short|bool)\s+(\w+)\s*;', timer_block.group(1)))
    parser = text[FILES[3]].split('void parse_state_timers(', 1)[1].split('void parse(MovementTime*', 1)[0]
    writer = text[FILES[3]].split('void dump_state_timers(', 1)[1].split('void dump(MovementTime*', 1)[0]
    fields = re.findall(r'PARSE_FIELD\((\w+)\);', parser)
    require(fields == re.findall(r'DUMP_FIELD\((\w+)\);', writer), 'Timer parse/dump mismatch')
    require(all(name in timer_types for name in fields), 'Unknown timer scalar type')
    target = {symbol: i for i, symbol in enumerate(iw7_symbols)}
    return {'schema':'iw7.weapon-animation-slot-contract/1', 'source_pin':PIN,
            'source_files':{name:digest(data) for name, data in raw.items()},
            'h1_slots':[{'key':key, 'symbol':symbol, 'iw7_index':target.get(symbol)}
                        for key, symbol in zip(h1_names, h1_symbols)],
            'iw7_slots':iw7_names, 'timer_fields':{name:timer_types[name] for name in fields},
            'evidence':'Pinned source text; no native parser/engine execution'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_root', type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.source_root), indent=2))
