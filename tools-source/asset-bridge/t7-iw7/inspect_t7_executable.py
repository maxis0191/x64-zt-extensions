"""Bounded, read-only T7 PE inspection. Never loads or executes the input image."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import struct

_helper = Path(__file__).resolve().parents[1] / "rig-abi" / "symbol_identity.py"
_spec = importlib.util.spec_from_file_location("t7_bounded_pe_reader", _helper)
_reader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_reader)
require = _reader.require
BASE = 0x140000000
SOURCE = "fab935826c898806855376662a8a03317b3ad8f1"

# label, RVA, preceding bytes, total window bytes, source-derived expectation.
# Windows are fixed: no caller-provided addresses, scanning, or recursive follows.
SITES = [
    ("DB_FindXAssetHeader", 0x1D5FB0, 0, 0x100, "entry"),
    ("DB_LoadXAssets", 0x1D8740, 0, 0x100, "entry"),
    ("SL_ConvertToString", 0x1632C0, 0, 0x80, "entry"),
    ("boot_call", 0x502AA9, 0x20, 0x60, "call_init"),
    ("server_thread_ret", 0x537840, 0, 0x80, "entry"),
    ("original_init", 0x504170, 0, 0x80, "entry"),
    ("Com_Frame", 0x501F90, 0, 0x80, "entry"),
    ("Load_SimpleAsset", 0x1DB2B0, 0, 0x80, "entry"),
    ("demonware_start_ret", 0x1E6050, 0, 0x80, "entry"),
    ("demonware_shutdown_ret", 0x7EA850, 0, 0x80, "entry"),
    ("download_ret", 0x7D5F70, 0, 0x80, "entry"),
    ("copy_info_branch_1", 0x1A18DF, 0x20, 0x60, "short_branch"),
    ("copy_info_branch_2", 0x1A1B5B, 0x20, 0x60, "short_branch"),
    ("image_loader_call", 0x1B1E5D, 0x20, 0x60, "call"),
    ("DB_AddXAsset_detour", 0x1D4600, 0, 0x80, "entry"),
    ("DB_FinishLoadXFile_detour", 0x1D3F00, 0, 0x80, "entry"),
    ("scheduler_detour", 0x5020E0, 0, 0x80, "entry"),
    ("command_jump", 0x4F9CD0, 0, 0x80, "entry"),
    ("integrity_intact_1", 0x064DC4, 0x20, 0x60, "intact"),
    ("integrity_intact_2", 0x909BD4, 0x20, 0x60, "intact"),
    ("integrity_intact_3", 0x10654C1, 0x20, 0x60, "intact"),
    ("integrity_split", 0x0621A8, 0x20, 0x60, "split"),
    ("database_ready", 0x5261E0, 0, 0x80, "entry"),
    ("DB_GetXAssetName", 0x19F080, 0, 0x80, "entry"),
    ("DB_FileExists", 0x1D5C20, 0, 0x80, "entry"),
    ("DB_IsXAssetDefault", 0x1D7260, 0, 0x80, "entry"),
    *[("load_zone_call_%d" % i, rva, 0, 0x80, "entry")
      for i, rva in enumerate((0x506C70, 0x1360A0, 0x6FF940,
                              0x14C610, 0x309FF0, 0x38ED20), 1)],
    ("g_assetNames", 0x10BDC70, 0, 8, "data"),
    ("g_zones", 0x6E84AD0, 0, 8, "data"),
    ("g_zoneNames", 0x6E83270, 0, 8, "data"),
    ("g_zoneCount", 0x699D21C, 0, 4, "data"),
    ("g_zoneIndex", 0x69BB268, 0, 2, "data"),
    ("current_fastfile_name", 0x68FD4A8, 0, 8, "data"),
]


class ObservedFile(_reader.BoundedFile):
    def __init__(self, path):
        super().__init__(path)
        self.before = self.identity()
        self.digest = hashlib.sha256()

    def identity(self):
        s = os.fstat(self.file.fileno())
        return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)

    def read(self, offset, count):
        data = super().read(offset, count)
        self.digest.update(struct.pack("<QQ", offset, count) + data)
        return data


class PE:
    def __init__(self, source):
        self.source = source
        dos = source.read(0, 64)
        require(dos[:2] == b"MZ", "missing MZ")
        nt = struct.unpack_from("<I", dos, 60)[0]
        hdr = source.read(nt, 24)
        require(hdr[:4] == b"PE\0\0", "missing PE signature")
        machine, count, self.timestamp = struct.unpack_from("<HHI", hdr, 4)
        require(machine == 0x8664 and 1 <= count <= 96, "expected bounded AMD64 PE")
        opt_size = struct.unpack_from("<H", hdr, 20)[0]
        require(112 <= opt_size <= 4096, "invalid optional header size")
        opt = source.read(nt + 24, opt_size)
        require(struct.unpack_from("<H", opt)[0] == 0x20B, "expected PE32+")
        self.entry = struct.unpack_from("<I", opt, 16)[0]
        self.base = struct.unpack_from("<Q", opt, 24)[0]
        self.image_size = struct.unpack_from("<I", opt, 56)[0]
        self.dll_characteristics = struct.unpack_from("<H", opt, 70)[0]
        dirs = struct.unpack_from("<I", opt, 108)[0]
        require(0 <= dirs <= 16 and 112 + 8 * dirs <= opt_size, "invalid directories")
        self.directories = [struct.unpack_from("<II", opt, 112 + 8 * n)
                            for n in range(dirs)] + [(0, 0)] * (16 - dirs)
        table = source.read(nt + 24 + opt_size, count * 40)
        self.sections = []
        for n in range(count):
            row = table[n * 40:(n + 1) * 40]
            vsize, va, raw_size, raw = struct.unpack_from("<IIII", row, 8)
            extent = max(vsize, raw_size)
            require(va + extent <= self.image_size, "section exceeds image")
            require(raw <= source.size and raw_size <= source.size - raw,
                    "section raw range exceeds file")
            self.sections.append(dict(name=row[:8].split(b"\0", 1)[0].decode("ascii", "replace"),
                                      rva=va, virtual_size=vsize, raw_size=raw_size,
                                      raw_offset=raw, characteristics=struct.unpack_from("<I", row, 36)[0]))
        ordered = sorted(self.sections, key=lambda s: s["rva"])
        for a, b in zip(ordered, ordered[1:]):
            require(a["rva"] + max(a["virtual_size"], a["raw_size"]) <= b["rva"],
                    "overlapping virtual sections")
        backed = sorted((s for s in self.sections if s["raw_size"]), key=lambda s: s["raw_offset"])
        for a, b in zip(backed, backed[1:]):
            require(a["raw_offset"] + a["raw_size"] <= b["raw_offset"],
                    "overlapping file sections")

    def section(self, rva, count):
        require(count > 0 and 0 <= rva < self.image_size and count <= self.image_size - rva,
                "RVA range exceeds image")
        candidates = [s for s in self.sections if s["rva"] <= rva and
                      rva + count <= s["rva"] + max(s["virtual_size"], s["raw_size"])]
        require(len(candidates) == 1, "RVA range needs one section")
        return candidates[0]

    def read(self, rva, count):
        s = self.section(rva, count)
        delta = rva - s["rva"]
        require(delta + count <= s["raw_size"], "RVA range has no complete file backing")
        return self.source.read(s["raw_offset"] + delta, count)

    def string(self, rva):
        value = bytearray()
        for n in range(512):
            ch = self.read(rva + n, 1)
            if ch == b"\0":
                return value.decode("ascii", "strict")
            value.extend(ch)
        raise ValueError("unterminated metadata string")

    def imports(self):
        rva, size = self.directories[1]
        if not rva and not size:
            return []
        require(rva and 20 <= size <= self.image_size, "invalid import directory extent")
        rows, total = [], 0
        for n in range(min(size // 20, 129)):
            row = struct.unpack("<5I", self.read(rva + 20 * n, 20))
            if not any(row):
                return rows
            original, _, _, name, first = row
            require(n < 128 and name and (original or first), "invalid import descriptor")
            dll, names = self.string(name), []
            for j in range(4097):
                total += 1
                require(total <= 4096, "total import thunk bound exceeded")
                value = struct.unpack("<Q", self.read((original or first) + 8 * j, 8))[0]
                if not value:
                    break
                names.append("ordinal:%d" % (value & 0xFFFF) if value >> 63
                             else self.string(value + 2))
            rows.append(dict(dll=dll, symbols=names))
        raise ValueError("unterminated import descriptors")

    def pdata(self):
        rva, size = self.directories[3]
        if not rva and not size:
            return b""
        require(rva and 0 < size <= 2 * 1024 * 1024 and size % 12 == 0, "invalid .pdata bound")
        data = self.read(rva, size)
        previous, previous_end = -1, 0
        for start, end, unwind in struct.iter_unpack("<III", data):
            require(previous < start < end <= self.image_size and 0 < unwind < self.image_size,
                    "invalid or unsorted .pdata record")
            require(start >= previous_end, "overlapping .pdata function ranges")
            previous, previous_end = start, end
        return data

    def unwind(self, pdata, rva):
        low, high = 0, len(pdata) // 12
        while low < high:
            mid = (low + high) // 2
            if struct.unpack_from("<I", pdata, mid * 12)[0] <= rva:
                low = mid + 1
            else:
                high = mid
        if not low:
            return None
        start, end, unwind = struct.unpack_from("<III", pdata, (low - 1) * 12)
        if not start <= rva < end:
            return None
        head = self.read(unwind, 4)
        flags = head[0] >> 3
        require(head[0] & 7 in (1, 2) and flags <= 7 and not (flags & 4 and flags & 3),
                "unsupported or invalid unwind header")
        size = (4 + head[2] * 2 + 3) & ~3
        size += 12 if flags & 4 else (4 if flags & 3 else 0)
        return dict(begin_rva=start, end_rva=end, unwind_rva=unwind,
                    version=head[0] & 7, flags=flags, bytes_hex=self.read(unwind, size).hex())


def expectation(kind, data, rva):
    """These comparisons are source-derived expectations, never a known-good hash."""
    if kind in ("call", "call_init"):
        if data[0] != 0xE8:
            return ["source expects a five-byte direct CALL at this site"], {}
        target = BASE + rva + 5 + struct.unpack_from("<i", data, 1)[0]
        conflict = kind == "call_init" and target != 0x140504170
        return (["original CALL target differs from the stub's original-init target"] if conflict else []), {
            "direct_call_target": hex(target), "expected_target_from_source":
            "0x140504170" if kind == "call_init" else None}
    if kind == "short_branch" and not (0x70 <= data[0] <= 0x7F or data[0] == 0xEB):
        return ["one-byte EB replacement does not start on the expected short branch"], {}
    if kind == "intact" and not (data[:5] == bytes.fromhex("89 04 8a 83 45") and data[6] == 0xFF):
        return ["precomputed intact-integrity site differs from source signature"], {}
    if kind == "split" and data[:4] != bytes.fromhex("89 04 8a e9"):
        return ["precomputed split-integrity site differs from source signature"], {}
    return [], {}


def inspect(path, acquisition_sha256=None):
    if acquisition_sha256 is not None:
        require(re.fullmatch(r"[0-9a-fA-F]{64}", acquisition_sha256), "invalid acquisition SHA256")
    try:
        import capstone
        decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    except (ImportError, OSError):
        decoder = None
    with ObservedFile(path) as src:
        pe = PE(src)
        conflicts, unknowns = [], []
        if pe.base != BASE:
            conflicts.append("preferred ImageBase differs from absolute source addresses")
        try:
            entry_section = pe.section(pe.entry, 1)
            if not entry_section["characteristics"] & 0x20000000:
                conflicts.append("entrypoint is not in an executable section")
        except ValueError as exc:
            conflicts.append("entrypoint: " + str(exc))
        imports, pdata = [], b""
        for label, reader in (("imports", pe.imports), ("pdata", pe.pdata)):
            try:
                value = reader()
                if label == "imports":
                    imports = value
                else:
                    pdata = value
            except (ValueError, UnicodeError) as exc:
                unknowns.append(label + ": " + str(exc))
        names = {n for dll in imports for n in dll["symbols"]}
        for name in ("SetProcessDPIAware", "ExitProcess"):
            if name not in names:
                unknowns.append("required source import not observed: " + name)
        windows = []
        for label, rva, before, count, kind in SITES:
            row = dict(site=label, source_va=hex(BASE + rva), rva=rva,
                       window_rva=rva - before, window_bytes=count, source_expectation=kind)
            if rva >= pe.image_size:
                conflicts.append(label + ": fixed source address exceeds candidate image")
            try:
                section = pe.section(rva, 1)
                row["section"] = section["name"]
                if kind != "data" and not section["characteristics"] & 0x20000000:
                    conflicts.append(label + ": source code site is not executable")
                data = pe.read(rva - before, count)
                row.update(bytes_hex=data.hex(), sha256=hashlib.sha256(data).hexdigest())
                failures, detail = expectation(kind, data[before:], rva)
                conflicts.extend(label + ": " + reason for reason in failures)
                row.update(detail)
                if kind != "data":
                    unwind = pe.unwind(pdata, rva)
                    row["runtime_function"] = unwind
                    # Decode only from an unwind entry inside the fixed window.
                    # Otherwise show a separately labelled source-assumed-site decode.
                    anchor = unwind["begin_rva"] if unwind else None
                    anchored = anchor is not None and rva - before <= anchor <= rva
                    start = anchor if anchored else rva
                    row["decode_anchor"] = "pdata_begin" if anchored else "source_assumed_site"
                    if decoder:
                        decoded = list(decoder.disasm(data[start - (rva - before):], BASE + start))
                        row["instructions"] = [dict(va=hex(i.address), size=i.size,
                                                    mnemonic=i.mnemonic, operands=i.op_str) for i in decoded]
                        boundaries = {i.address for i in decoded}
                        if anchored and BASE + rva not in boundaries:
                            # An instruction spanning the site is a conflict; a decoding gap is unknown.
                            spanning = any(i.address < BASE + rva < i.address + i.size for i in decoded)
                            (conflicts if spanning else unknowns).append(label + ": " +
                                ("site falls inside an instruction" if spanning else "decode did not reach site"))
                        if label == "DB_LoadXAssets" and anchored:
                            for edge in (BASE + 0x1D87AE, BASE + 0x1D87B3):
                                if edge not in boundaries:
                                    spanning = any(i.address < edge < i.address + i.size for i in decoded)
                                    (conflicts if spanning else unknowns).append("DB_LoadXAssets NOP edge " +
                                        hex(edge) + (": inside instruction" if spanning else ": not decoded"))
                    else:
                        unknowns.append(label + ": capstone unavailable; no disassembly")
                    if not anchored:
                        unknowns.append(label + ": instruction boundary not independently anchored")
                if label == "DB_LoadXAssets":
                    row["additional_source_patch"] = dict(rva=0x1D87AE, length=5, operation="NOP",
                        note="inside this window; original five-byte instruction span requires review")
            except ValueError as exc:
                row["indeterminate"] = str(exc)
                unknowns.append(label + ": " + str(exc))
            windows.append(row)
        require(src.identity() == src.before, "input identity/size/timestamps changed during inspection")
        return dict(schema="iw7.t7-static-executable-inspection/1", source_commit=SOURCE,
                    identity=dict(name=Path(path).name, file_bytes=src.size,
                                  filesystem_identity=list(src.before),
                                  acquisition_sha256_unverified=acquisition_sha256,
                                  observed_read_sequence_sha256=src.digest.hexdigest(),
                                  full_file_sha256_computed=False),
                    pe=dict(machine="AMD64", format="PE32+", preferred_image_base=hex(pe.base),
                            timestamp=pe.timestamp, size_of_image=pe.image_size, entrypoint_rva=pe.entry,
                            dll_characteristics=pe.dll_characteristics, directories=pe.directories,
                            sections=pe.sections, imports=imports, pdata_records=len(pdata) // 12),
                    bytes_read=src.bytes_read, read_budget=_reader.LIMIT,
                    windows=windows, conflicts=conflicts, indeterminate=unknowns,
                    decision="stop_before_boot" if conflicts else "indeterminate_manual_review_required",
                    executable_loaded=False, runtime_compatibility_proven=False, boot_authorized=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--output", required=True, type=Path, help="new JSON under this checkout's ignored runtime/")
    parser.add_argument("--acquisition-sha256", help="optional acquisition receipt value; not verified by this bounded reader")
    args = parser.parse_args()
    runtime = (Path(__file__).resolve().parents[3] / "runtime").resolve()
    target = args.output.resolve()
    try:
        require(target.is_relative_to(runtime) and target != runtime and target.suffix.lower() == ".json",
                "raw output must be a new JSON below this checkout's ignored runtime/")
        require(not target.exists(), "output already exists")
        report = inspect(args.executable, args.acquisition_sha256)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as out:
            json.dump(report, out, indent=2)
            out.write("\n")
        print(json.dumps(dict(output=str(target), decision=report["decision"],
                              conflicts=len(report["conflicts"]), bytes_read=report["bytes_read"])))
        return 2 if report["conflicts"] else 0
    except (ValueError, OSError) as exc:
        print(json.dumps(dict(decision="indeterminate_stop_before_boot", error=str(exc),
                              executable_loaded=False, boot_authorized=False)))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
