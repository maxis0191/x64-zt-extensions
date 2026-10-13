"""Verify nine selected code windows from an existing patched runtime snapshot.

Reads 2,690 selected text bytes, the pinned rdata/pdata metadata, and no process.
No whole-text search, native invocation, extracted bytes or disassembly output.
Addresses below are preferred-image addresses, not callable live bindings.
Requires the already installed Capstone package only for instruction checks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import capstone

from havok_probe import RDATA_SHA256, RDATA_SIZE, read_bounded
from trigger_bridge import checked_path, require

TEXT_BASE = 0x140001000
RDATA_BASE = 0x141435000
PDATA_SHA = '8ff97607018c0c531a9d6851282701074a50b141729060f9f23ae728c9fad41e'
WINDOWS = (
    ('db_add_patched', 0x140A76520, 121, '23f37d5c81eea00330ad7e31ca92b2639f27e8a5795fd34f7850cefa6de3faa2'),
    ('asset_link', 0x140A782B0, 568, '95f7074da74f208ddf427949d451905c3bf1f81ca25758759985c7c65bc0f32f'),
    ('type_dispatch', 0x1403B7430, 34, '8bac3192200b7cc05a18a5f9f3b02782c3e5a87dea62b65d5ea40d436212c23e'),
    ('clipmap_wrapper', 0x1403B72F0, 14, '3ffcf4a7d534e80a7ab3126240c646f2c0d694e022fc0bbc1c460ad4d8b01575'),
    ('clipmap_thunk', 0x14054BEB0, 5, 'bed2f0bc5652a6ae9482680e20b96d1081ce233d4826c278fead39ea071ec3c1'),
    ('world_consumer', 0x140571D50, 432, '12d99ba73e2078af560f1096c03c84b0a994c457fe7238cd79bb1793bcba35b6'),
    ('shape_tags_loader', 0x140572C30, 143, '926f1458422a1f58ac65243b9f53f3fe6f4ccaccc8fed23039496267f1f7f0db'),
    ('packfile_inplace', 0x140F2DA80, 966, '01e53078c7ab6cd0be20812f2ca919528c3232cf74d1a14664adad6f980a3048'),
    ('packfile_header_check', 0x140F2E120, 407, '8cb2ab453ae56a0e78ce22912f2570e0983b0034a898d8158896eef0a16f4576'),
)
CALLS = (
    (0x140A76557, 'call', 0x140A782B0),
    (0x140A783CB, 'call', 0x1403B7430),
    (0x1403B72F4, 'call', 0x14054BEB0),
    (0x14054BEB0, 'jmp', 0x140571D50),
    (0x140571D79, 'call', 0x140572C30),
    (0x140572C3A, 'call', 0x140F2DA80),
    (0x140F2DAAE, 'call', 0x140F2E120),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inspect(root):
    root = Path(root)
    rdata = read_bounded(root / 'unpacked-rdata.bin', RDATA_SIZE)
    pdata = read_bounded(root / 'unpacked-pdata.bin', 832608)
    require(sha(rdata) == RDATA_SHA256 and sha(pdata) == PDATA_SHA, 'Metadata snapshot differs')
    records = list(struct.iter_unpack('<III', pdata))
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True
    windows, instructions = [], {}
    with checked_path(root / 'unpacked-text.bin', True).open('rb') as stream:
        for name, address, count, expected in WINDOWS:
            stream.seek(address - TEXT_BASE)
            data = stream.read(count)
            require(len(data) == count and sha(data) == expected, 'Code window differs: ' + name)
            decoded = list(md.disasm(data, address))
            require(sum(item.size for item in decoded) == count, 'Incomplete selected-window decode')
            instructions.update((item.address, item) for item in decoded)
            owners = [{'start': hex(0x140000000 + a), 'end': hex(0x140000000 + b)}
                      for a, b, _ in records if a < address + count - 0x140000000
                      and b > address - 0x140000000]
            windows.append({'name': name, 'start': hex(address), 'bytes': count,
                            'sha256': expected, 'overlapping_unwind_ranges': owners})
    for site, mnemonic, target in CALLS:
        ins = instructions[site]
        require(ins.mnemonic == mnemonic and ins.operands[0].type == capstone.CS_OP_IMM
                and ins.operands[0].imm == target, 'Call-chain edge differs')
    lea = instructions[0x1403B7437]
    require(lea.mnemonic == 'lea' and lea.operands[1].type == capstone.CS_OP_MEM
            and lea.operands[1].mem.base == capstone.x86.X86_REG_RIP, 'Dispatch table reference differs')
    table = lea.address + lea.size + lea.operands[1].mem.disp
    require(table == 0x1414672D0, 'Dispatch table address differs')
    clipmap_entry = struct.unpack_from('<Q', rdata, table - RDATA_BASE + 22 * 8)[0]
    require(clipmap_entry == 0x1403B72F0, 'CLIPMAP handler differs')
    for address, destination, displacement in ((0x140571D5F, capstone.x86.X86_REG_EDX, 0xF8),
                                                (0x140571D72, capstone.x86.X86_REG_RCX, 0x100)):
        ins = instructions[address]
        require(ins.mnemonic == 'mov' and ins.operands[0].reg == destination
                and ins.operands[1].type == capstone.CS_OP_MEM
                and ins.operands[1].mem.base == capstone.x86.X86_REG_RCX
                and ins.operands[1].mem.disp == displacement, 'World field access differs')
    require(instructions[0x140A76520].mnemonic == 'jmp', 'Known patched entry differs')
    return {'schema': 'iw7.asset-bridge.world-consumer-inspection/1',
            'snapshot': 'Existing patched capture; not a live binary ABI or pristine retail image',
            'rdata_sha256': sha(rdata), 'pdata_sha256': sha(pdata),
            'whole_text_hash_recomputed': False,
            'selected_text_bytes': sum(row['bytes'] for row in windows),
            'windows': windows, 'capstone_version': capstone.__version__,
            'call_chain': [{'site': hex(site), 'kind': kind, 'target': hex(target)}
                           for site, kind, target in CALLS],
            'dispatch': {'table': hex(table), 'asset_type': 22, 'entry': hex(clipmap_entry)},
            'world_blob_fields': {'size_offset': '0xf8', 'pointer_offset': '0x100'},
            'root_class_identified': False, 'creator_identified': False,
            'serializer_identified': False, 'native_executed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-root', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.reference_root), indent=2))
    except (ValueError, OSError, KeyError, struct.error) as error:
        parser.exit(2, str(error) + '\n')
