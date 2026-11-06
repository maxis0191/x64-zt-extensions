"""Read IW7 sound asset banks (.sabl loaded / .sabs streamed), stdlib only.

List the entries of a bank, find entries by alias asset file name (the
`File` column of an IW7 alias table, hashed the way the engine does), and
extract entries as playable FLAC files (same container ZoneTool's soundbank
dump writes, so they can be fed back to ZoneTool as `sound_assets/<File>.flac`).

    python iw7_sab.py list <bank.sabl|.sabs> [--grep text] [--json]
    python iw7_sab.py extract <bank> --name "ambient\\amb_cp_zmb_basement_lr.SL.75.36000.all" ... --out <dir>
    python iw7_sab.py extract <bank> --names-from <aliases.csv> --alias amb_cp_zmb_basement_lr ... --out <dir>
    python iw7_sab.py hash "<file name>"

Streamed music/ambience of stock levels lives in the global streamed bank
(code_post_gfx.sabs); a level's own .sabs may be an empty 4096-byte header.
"""
import argparse
import csv
import json
import os
import struct
import sys

MAGIC = 0x23585532  # '2UX#'
HEADER = struct.Struct('<8I3Q16s512sQQ64s8s3sII5s')
ENTRY = struct.Struct('<5IQiBBBHHBBBBB')
NAME_LEN = 128
FORMAT_PCMS16, FORMAT_FLAC = 0, 8
FORMATS = {0: 'pcms16', 8: 'flac'}


def snd_hash_name(name):
    """Engine hash of alias/asset names (ZoneTool game/shared.cpp snd_hash_name)."""
    if not name:
        return 0
    h = 5381
    for ch in name.encode('latin-1', 'replace'):
        if 65 <= ch <= 90:
            ch += 32
        h = (65599 * h + ch) & 0xFFFFFFFF
    return h or 1


class Bank:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            raw = f.read(HEADER.size)
        if len(raw) < HEADER.size:
            raise ValueError('%s: too small for a bank header' % path)
        v = HEADER.unpack(raw)
        (self.magic, self.version, self.entry_size, self.checksum_size, self.dependency_size, self.entry_count,
         self.dependency_count, self.build_version, self.file_size, self.entry_offset, self.checksum_offset,
         _cc, deps, self.source_checksum_offset, self.asset_name_offset, zone, platform, language,
         self.converted_asset_version, self.asset_section_size, _pad) = v
        if self.magic != MAGIC or self.entry_size != ENTRY.size:
            raise ValueError('%s: not an IW7 sound asset bank (magic %08x entry %d)' % (path, self.magic, self.entry_size))
        self.zone = zone.split(b'\0')[0].decode('latin-1')
        self.platform = platform.split(b'\0')[0].decode('latin-1')
        self.language = language.split(b'\0')[0].decode('latin-1')
        self.dependencies = [d.decode('latin-1') for d in deps.split(b'\0') if d][:self.dependency_count]
        self._entries = None

    def entries(self):
        if self._entries is None:
            out = []
            with open(self.path, 'rb') as f:
                f.seek(self.entry_offset)
                table = f.read(ENTRY.size * self.entry_count)
                names = b''
                if self.asset_name_offset:
                    f.seek(self.asset_name_offset)
                    names = f.read(NAME_LEN * self.entry_count)
            for i in range(self.entry_count):
                e = ENTRY.unpack_from(table, i * ENTRY.size)
                name = names[i * NAME_LEN:(i + 1) * NAME_LEN].split(b'\0')[0].decode('latin-1') if names else ''
                out.append({
                    'index': i, 'id': e[0], 'size': e[1], 'seek_table_size': e[2], 'frame_count': e[3],
                    'hybrid_pcm_size': e[4], 'offset': e[5], 'frame_rate': e[6], 'channels': e[7],
                    'looping': e[8], 'format': FORMATS.get(e[9], e[9]), 'blocksize_kb': e[16], 'name': name,
                    'seconds': (e[3] / e[6]) if e[6] else 0.0,
                })
            self._entries = out
        return self._entries

    def by_id(self):
        return {e['id']: e for e in self.entries()}

    def read(self, entry):
        with open(self.path, 'rb') as f:
            f.seek(entry['offset'])
            return f.read(entry['size'] + entry['seek_table_size'] + entry['hybrid_pcm_size'])


def flac_container(entry, data):
    """Wrap raw bank FLAC frames (+ seek table) into a FLAC file, as ZoneTool's flac::dump does."""
    block = entry['blocksize_kb'] * 1024 if entry['blocksize_kb'] else 0x400
    rate, ch, total = entry['frame_rate'], entry['channels'], entry['frame_count']
    info = struct.pack('>HH', block, block) + b'\0' * 6
    info += bytes([(rate >> 12) & 0xFF, (rate >> 4) & 0xFF, (((ch - 1) << 1) | ((rate << 4) & 0xF0)) & 0xFF])
    info += bytes([((16 - 1) << 4) | ((total >> 32) & 0x0F), (total >> 24) & 0xFF, (total >> 16) & 0xFF,
                   (total >> 8) & 0xFF, total & 0xFF])
    info += b'\0' * 16
    has_seek = entry['seek_table_size'] > 0
    out = b'fLaC' + bytes([0x00 if has_seek else 0x80]) + len(info).to_bytes(3, 'big') + info
    if has_seek:
        out += bytes([0x80 | 3]) + entry['seek_table_size'].to_bytes(3, 'big')
    return out + data


def alias_files(aliases_csv, aliases):
    """File column of the named aliases (all variants) in an IW7 alias table."""
    want = set(a.lower() for a in aliases)
    files = []
    with open(aliases_csv, newline='', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if row.get('Name', '').lower() in want and row.get('File'):
                files.append(row['File'])
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('list')
    p.add_argument('bank')
    p.add_argument('--grep')
    p.add_argument('--json', action='store_true')
    p = sub.add_parser('extract')
    p.add_argument('bank', nargs='+', help='banks searched in order (first match wins)')
    p.add_argument('--name', action='append', default=[], help='asset file name (alias File column)')
    p.add_argument('--names-from', help='IW7 aliases.csv used with --alias')
    p.add_argument('--alias', nargs='*', default=[])
    p.add_argument('--out', required=True, help='root; files land at <out>/<File>.flac (ZoneTool sound_assets layout)')
    p = sub.add_parser('hash')
    p.add_argument('name')
    args = ap.parse_args(argv)

    if args.cmd == 'hash':
        print('%08x' % snd_hash_name(args.name))
        return 0
    if args.cmd == 'list':
        b = Bank(args.bank)
        rows = [e for e in b.entries() if not args.grep or args.grep.lower() in e['name'].lower()]
        if args.json:
            print(json.dumps({'zone': b.zone, 'language': b.language, 'entries': len(b.entries()), 'rows': rows}, indent=1))
        else:
            print('zone=%s language=%s entries=%d deps=%s' % (b.zone, b.language, b.entry_count, b.dependencies))
            for e in rows:
                print('%08x %9d %7.2fs %dch %5d %s %s' % (e['id'], e['size'], e['seconds'], e['channels'], e['frame_rate'],
                                                         'loop' if e['looping'] else '    ', e['name']))
        return 0

    names = list(args.name)
    if args.alias:
        if not args.names_from:
            raise SystemExit('--alias needs --names-from')
        names += alias_files(args.names_from, args.alias)
    banks = [Bank(p) for p in args.bank]
    index = [(b, b.by_id()) for b in banks]
    report, missing = [], []
    for name in dict.fromkeys(names):
        h = snd_hash_name(name)
        hit = next(((b, ids[h]) for b, ids in index if h in ids), None)
        if not hit:
            missing.append(name)
            continue
        b, e = hit
        if e['format'] != 'flac':
            missing.append(name + ' (format %s)' % e['format'])
            continue
        dest = os.path.join(args.out, *name.replace('/', '\\').split('\\')) + '.flac'
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(flac_container(e, b.read(e)))
        report.append({'name': name, 'bank': b.path, 'id': '%08x' % h, 'seconds': round(e['seconds'], 3),
                       'channels': e['channels'], 'rate': e['frame_rate'], 'bytes': os.path.getsize(dest)})
    print(json.dumps({'extracted': report, 'missing': missing}, indent=1))
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
