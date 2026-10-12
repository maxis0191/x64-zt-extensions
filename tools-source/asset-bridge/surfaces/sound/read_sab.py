"""Read only the original one-entry IW7 SABL/empty SABS; no writer/native imports.

All extents are exact for this fixture. A general/retail bank is unsupported.
This separate reader shares only the previously reviewed FLAC subset decoder.
"""
import argparse
import csv
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import struct
import wave

from read_flac import decode

ZONE = "sdk_original_sound_v1"
BANK = "community_original_sound_v1.all"
ALIAS = "community_original_chime_v1"
SAMPLE = "community/original_chime_v1"
ALIAS_PATH = "sound/" + BANK + ".aliases.csv"
BANK_PATH = "soundbank/" + BANK + ".json"
FLAC_PATH = "sound_assets/" + SAMPLE + ".flac"
SOURCES = {"original/source.wav", FLAC_PATH, ALIAS_PATH, BANK_PATH, "zone_source/" + ZONE + ".csv"}
HEADER = struct.Struct("<8I3Q16s512s2Q64s8s3s2I5s")
ENTRY = struct.Struct("<5IQiBBBHH5B")
MAX_FILE = 256 * 1024
MAX_TOTAL = 2 * 1024 * 1024
EMPTY_TABLES = ("ADSRSettings", "AmbientDefs", "AmbientElements", "AmbientEvents", "FilterDefs",
                "FullOcclusionDefs", "MixDefs", "NPCAdsrZoneEntry", "OccludeDefs", "PLRAdsrZoneEntry",
                "PlayerBreathStateDefs", "ReverbDefs", "TimescaleEntrys", "Unks", "ZoneDefs", "sendEffectParams")
NUMERIC = {"vol_min", "vol_max", "pitch_min", "pitch_max", "donut_fadeend", "dist_min", "dist_max",
           "Velocity_Min", "Probability", "StartDelay", "reverb_multiplier", "far_reverb_multiplier",
           "lfe_percentage", "center_percentage", "envelop_min", "envelop_max", "envelop_percentage",
           "smartPanDistance2d", "smartPanDistance3d", "smartPanAttenuation2d", "stereoSpreadMinDist",
           "stereoSpreadMaxDist", "stereoSpreadMidPoint", "stereoSpreadMaxAngle", "masterPriority",
           "masterPercentage", "masterSlavePercentage"}


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(raw, limit=16384):
    require(type(raw) is bytes and len(raw) <= limit, "bounded JSON required")
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON field")
            result[key] = value
        return result
    def invalid(_):
        raise ValueError("nonfinite JSON refused")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def name_id(value):
    result = 5381
    for byte in value.lower().encode("ascii"):
        result = (65599 * result + byte) & 0xffffffff
    return result or 1


def contract(raw):
    value = strict_json(raw)
    expected = dict(schema="iw7.original-sound-bank-contract/1", zone=ZONE, bank=BANK, alias=ALIAS,
                    sample=SAMPLE, samples=48000, sample_rate=48000, channels=1, bits_per_sample=16,
                    alias_id=name_id(ALIAS), asset_id=name_id(SAMPLE),
                    pcm_sha256="72cb02b5178ce424fd3df3dbfb28b0b9613f69a4da3af71a022b8b542a46ddd9")
    require(type(value) is dict and set(value) == set(expected) | {"sources"}, "exact contract fields required")
    for name, wanted in expected.items():
        require(type(value[name]) is type(wanted) and value[name] == wanted, "contract field differs: " + name)
    require(type(value["sources"]) is dict and set(value["sources"]) == SOURCES, "exact source inventory required")
    for pin in value["sources"].values():
        require(type(pin) is dict and set(pin) == {"bytes", "sha256"}, "exact source pin fields required")
        require(type(pin["bytes"]) is int and 0 < pin["bytes"] <= MAX_FILE, "bounded integer source size required")
        require(type(pin["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", pin["sha256"]), "source SHA required")
    return value


def plain(path):
    path = Path(path).absolute()
    for current in (path, *path.parents):
        require(not current.is_symlink() and not current.is_junction(), "linked input refused")
    return path


class Inputs:
    def __init__(self):
        self.total = 0
        self.observed = {}

    def read(self, path, limit=MAX_FILE):
        path = plain(path)
        info = path.stat()
        require(stat.S_ISREG(info.st_mode) and info.st_size <= limit, "regular bounded file required")
        require(self.total + info.st_size <= MAX_TOTAL, "total read bound exceeded")
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
        require(len(data) == info.st_size, "input size changed during read")
        previous = self.observed.get(path)
        require(previous is None or previous == (len(data), sha(data)), "input changed between reads")
        self.observed[path] = (len(data), sha(data))
        self.total += len(data)
        return data

    def recheck(self):
        # Sequential snapshots, not persistent read locks or a concurrent-writer guarantee.
        for path, expected in list(self.observed.items()):
            require((len(self.read(path)), self.observed[path][1]) == expected, "final input mismatch")


def alias_row(raw):
    require(len(raw) <= 8192, "bounded alias CSV required")
    rows = list(csv.reader(io.StringIO(raw.decode("ascii"), newline=""), strict=True))
    require(len(rows) == 2 and len(rows[0]) == len(rows[1]) == 53 and len(set(rows[0])) == 53,
            "exact single 53-field alias row required")
    return dict(zip(rows[0], rows[1]))


def original(inputs, source, spec):
    files = {}
    for relative, pin in spec["sources"].items():
        data = inputs.read(Path(source) / relative)
        require(len(data) == pin["bytes"] and sha(data) == pin["sha256"], "original source changed: " + relative)
        files[relative] = data
    bank = strict_json(files[BANK_PATH])
    wanted = dict(name=BANK, zone=ZONE, gameLanguage="all", soundLanguage="all", aliases=[ALIAS_PATH])
    wanted.update({name: [] for name in EMPTY_TABLES})
    require(bank == wanted, "original bank fields differ")
    require(files["zone_source/" + ZONE + ".csv"] == ("soundbank," + BANK + "\n").encode(), "zone differs")
    alias = alias_row(files[ALIAS_PATH])
    require(alias.get("Name") == ALIAS and alias.get("File") == SAMPLE and alias.get("type") == "loaded"
            and alias.get("loop") == "nonlooping" and alias.get("precached") == "True", "original alias binding differs")
    flac = files[FLAC_PATH]
    pcm, decoded = decode(flac)
    require(decoded["samples"] == 48000 and sha(pcm) == spec["pcm_sha256"], "original PCM contract differs")
    wav = files["original/source.wav"]
    require(wav[:4] == b"RIFF" and int.from_bytes(wav[4:8], "little") + 8 == len(wav), "original RIFF closure")
    with wave.open(io.BytesIO(wav), "rb") as reader:
        require(reader.getparams()[:4] == (1, 2, 48000, 48000) and reader.getcomptype() == "NONE",
                "original WAV parameters differ")
        require(reader.readframes(48001) == pcm, "original WAV samples differ")
    return files, alias, pcm


def pad_text(value, size):
    raw = value.encode("ascii")
    require(len(raw) < size, "terminated text bound")
    return raw + bytes(size - len(raw))


def read_bank(raw, streamed, flac, pcm, spec):
    require(type(streamed) is bool, "explicit bank kind required")
    require(type(raw) is bytes and HEADER.size <= len(raw) <= MAX_FILE, "bounded complete SAB required")
    fields = HEADER.unpack_from(raw)
    (magic, version, entry_size, checksum_size, dependency_size, count, dependency_count, build_version,
     file_size, entry_offset, checksum_offset, placeholder, dependencies, source_offset, names_offset,
     zone, platform, language, converted, section_size, padding) = fields
    require((magic, version, entry_size, checksum_size, dependency_size, dependency_count, build_version, converted)
            == (0x23585532, 4, 44, 16, 64, 8, 4, 4), "SAB header fields differ")
    require(zone == pad_text(ZONE, 64) and platform == pad_text("pc", 8) and language == b"all", "SAB identity differs")
    require(placeholder == b"\xcc" * 16, "expected writer placeholder differs; not a checksum")
    require(dependencies == bytes(512) and padding == bytes(5), "SAB dependency/reserved fields differ")
    require(raw[HEADER.size:4096] == bytes(4096 - HEADER.size), "SAB header padding differs")
    if streamed:
        require((count, file_size, entry_offset, checksum_offset, source_offset, names_offset, section_size)
                == (0, 4096, 0, 0, 0, 0, 0) and len(raw) == 4096, "exact empty SABS required")
        return {"bytes": len(raw), "sha256": sha(raw), "entries": 0}
    require((count, file_size, entry_offset, checksum_offset, source_offset, names_offset, section_size)
            == (1, 114816, 102400, 106496, 110592, 114688, 98304) and len(raw) == file_size,
            "exact loaded SAB layout/closure required")
    entry = ENTRY.unpack_from(raw, entry_offset)
    wanted = (spec["asset_id"], 96132, 216, 48000, 0, 4096, 48000, 1, 0, 8, 0, 0, 0, 0, 0, 0, 0)
    require(entry == wanted, "SAB entry fields differ")
    payload = raw[4096:4096 + 96348]
    require(payload == flac[46:], "SAB seek/frame bytes differ from approved original")
    reconstructed = flac[:46] + payload
    actual_pcm, report = decode(reconstructed)
    require(actual_pcm == pcm and report["pcm_sha256"] == spec["pcm_sha256"], "SAB PCM mismatch")
    require(raw[checksum_offset:checksum_offset + 16] == hashlib.md5(payload).digest(), "SAB payload checksum mismatch")
    require(raw[source_offset:source_offset + 16] == hashlib.md5(pcm).digest() == flac[26:42], "SAB PCM checksum mismatch")
    require(raw[names_offset:] == pad_text(SAMPLE, 128), "exact SAB asset name/trailing closure required")
    for start, end in ((4096 + 96348, entry_offset), (entry_offset + 44, checksum_offset),
                       (checksum_offset + 16, source_offset), (source_offset + 16, names_offset)):
        require(raw[start:end] == bytes(end - start), "nonzero SAB section padding")
    return {"bytes": len(raw), "sha256": sha(raw), "entries": 1, "payload_bytes": len(payload),
            "payload_md5_verified": True, "pcm_md5_verified": True, "pcm_sha256": sha(pcm),
            "seek_points": 12, "frames": report["frames"], "samples": 48000}


def compare_alias_dump(raw, expected):
    actual = alias_row(raw)
    require(list(actual) == list(expected), "dump alias fields/order differ")
    for name, value in actual.items():
        wanted = expected[name]
        if name in NUMERIC:
            require(re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value), "finite canonical alias number required")
            require(Decimal(value) == Decimal(wanted), "dump alias number differs: " + name)
        else:
            require(value == wanted, "dump alias text differs: " + name)


def inventory(raw):
    require(len(raw) <= 256 * 1024, "bounded inventory required")
    text = raw.decode("utf-8", errors="strict")
    require('Loading zone "' + ZONE + '"' in text and
            not re.search(r"could not be found|could not find referenced|\[\s*(?:ERROR|FATAL)\s*\]", text, re.I),
            "unresolved or absent sound inventory")
    found = []
    for line in text.splitlines():
        if "Loading asset " in line:
            match = re.search(r'Loading asset "([^"\r\n]+)" of type ([a-z0-9]+)\.$', line)
            require(match is not None, "malformed inventory callback")
            found.append((match[2], match[1]))
    require(found == [("soundbank", BANK)], "one exact soundbank inventory callback required")


def inspect(source, banks, contract_path, dump=None, inventory_path=None):
    require((dump is None) == (inventory_path is None), "dump and inventory must be supplied together")
    inputs = Inputs()
    spec = contract(inputs.read(contract_path, 16384))
    files, alias, pcm = original(inputs, source, spec)
    loaded = read_bank(inputs.read(Path(banks) / (ZONE + ".sabl")), False, files[FLAC_PATH], pcm, spec)
    streamed = read_bank(inputs.read(Path(banks) / (ZONE + ".sabs")), True, files[FLAC_PATH], pcm, spec)
    if dump is not None:
        compare_alias_dump(inputs.read(Path(dump) / ALIAS_PATH, 8192), alias)
        actual = inputs.read(Path(dump) / FLAC_PATH)
        # Native dump knowingly rewrites these fields. Verify that behavior but
        # do not call the resulting standalone FLAC or alias index validated.
        expected = bytearray(files[FLAC_PATH])
        expected[8:18] = b"\x04\x00\x04\x00" + bytes(6)
        expected[26:42] = bytes(16)
        require(actual == expected, "dump FLAC header/payload or trailing bytes differ")
        inventory(inputs.read(inventory_path))
    inputs.recheck()
    return {"schema": "iw7.original-sound-sab-read/1", "status": "SABBytesVerified", "loaded": loaded,
            "streamed": streamed, "alias": ALIAS, "source_alias_verified": True, "alias_id": spec["alias_id"],
            "asset_id": spec["asset_id"], "source_alias_matches_sab_asset": True,
            "dump_alias_values_verified": dump is not None, "inventory_verified": dump is not None,
            "dump_seek_frame_bytes_verified": dump is not None, "dump_streaminfo_rewritten": dump is not None,
            "dump_standalone_flac_validated": False, "native_alias_index_verified": False,
            "expected_single_alias_index": {"value": 0, "next": 65535},
            "checksum_checksum_verified": False, "checksum_checksum_kind": "writer 16xCC placeholder",
            "separate_reader": True, "source_recheck": "sequential size/hash snapshots",
            "input_bytes_read_including_recheck": inputs.total, "playback_verified": False, "ready": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--banks", required=True, type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--dump", type=Path)
    parser.add_argument("--inventory", type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.source, args.banks, args.contract, args.dump, args.inventory), indent=2))


if __name__ == "__main__":
    main()
