"""Read only PE CodeView and MSF7 stream-1 identity, with bounded seek reads.

No symbol loading, debugger, subprocess, network, whole-file read or file hash.
Matching GUID/age identifies a symbol pair, not the current process image.
"""
import argparse
import json
import os
from pathlib import Path
import struct
import uuid


LIMIT = 4 * 1024 * 1024
MAGIC = b"Microsoft C/C++ MSF 7.00\r\n\x1aDS\0\0\0"


def require(condition, message):
    if not condition:
        raise ValueError(message)


class BoundedFile:
    def __init__(self, path):
        self.file = open(path, "rb")
        self.size = os.fstat(self.file.fileno()).st_size
        self.bytes_read = 0

    def read(self, offset, count):
        require(0 <= offset <= self.size and 0 <= count <= self.size - offset,
                "file range is invalid or truncated")
        require(self.bytes_read + count <= LIMIT, "metadata read budget exceeded")
        self.file.seek(offset)
        data = self.file.read(count)
        require(len(data) == count, "file changed or truncated while reading")
        self.bytes_read += count
        return data

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.file.close()


def pe_identity(path):
    with BoundedFile(path) as src:
        dos = src.read(0, 64)
        require(dos[:2] == b"MZ", "expected DOS signature")
        offset = struct.unpack_from("<I", dos, 60)[0]
        header = src.read(offset, 24)
        require(header[:4] == b"PE\0\0", "expected PE signature")
        machine, sections, timestamp = struct.unpack_from("<HHI", header, 4)
        optional_size = struct.unpack_from("<H", header, 20)[0]
        require(machine == 0x8664 and 1 <= sections <= 96, "expected bounded AMD64 PE")
        require(112 <= optional_size <= 4096, "invalid optional header size")
        opt = src.read(offset + 24, optional_size)
        require(struct.unpack_from("<H", opt)[0] == 0x20B, "expected PE32+")
        dirs = struct.unpack_from("<I", opt, 108)[0]
        require(7 <= dirs <= 16 and 112 + dirs * 8 <= len(opt), "invalid PE directories")
        debug_rva, debug_size = struct.unpack_from("<II", opt, 112 + 6 * 8)
        require(debug_rva and 0 < debug_size <= 28 * 128 and debug_size % 28 == 0,
                "missing or invalid debug directory")
        table = src.read(offset + 24 + optional_size, sections * 40)
        locations = []
        for n in range(sections):
            _, va, raw_size, raw_offset = struct.unpack_from("<IIII", table, n * 40 + 8)
            if va <= debug_rva and debug_rva + debug_size <= va + raw_size:
                locations.append(raw_offset + debug_rva - va)
        require(len(locations) == 1, "debug directory needs one file-backed section")
        debug = src.read(locations[0], debug_size)
        identities = []
        for n in range(debug_size // 28):
            kind, cv_size, _, cv_offset = struct.unpack_from("<IIII", debug, n * 28 + 12)
            if kind != 2:
                continue
            require(25 <= cv_size <= 4096, "invalid CodeView size")
            cv = src.read(cv_offset, cv_size)
            require(cv[:4] == b"RSDS" and b"\0" in cv[24:], "expected terminated RSDS")
            identities.append({"guid": str(uuid.UUID(bytes_le=cv[4:20])),
                               "age": struct.unpack_from("<I", cv, 20)[0],
                               "name": cv[24:].split(b"\0", 1)[0].decode("utf-8", "replace")
                                         .replace("\\", "/").rsplit("/", 1)[-1]})
        require(len(identities) == 1, "expected exactly one CodeView identity")
        return {"name": Path(path).name, "file_bytes": src.size,
                "metadata_bytes_read": src.bytes_read, "machine": "AMD64",
                "timestamp": timestamp, "image_base": hex(struct.unpack_from("<Q", opt, 24)[0]),
                "size_of_image": struct.unpack_from("<I", opt, 56)[0], "codeview": identities[0]}


def pdb_identity(path):
    with BoundedFile(path) as src:
        header = src.read(0, 56)
        require(header[:32] == MAGIC, "expected PDB MSF7")
        block_size, _, blocks, directory_size, _, block_map = struct.unpack_from("<6I", header, 32)
        require(block_size in (512, 1024, 2048, 4096, 8192), "invalid PDB block size")
        require(blocks > 0 and blocks * block_size == src.size, "invalid PDB file extent")
        require(12 <= directory_size <= LIMIT // 2, "directory exceeds bounded metadata budget")
        count = (directory_size + block_size - 1) // block_size
        require(count * 4 <= block_size and block_map < blocks, "unsupported directory map")
        numbers = struct.unpack("<" + "I" * count, src.read(block_map * block_size, count * 4))
        require(len(set(numbers)) == count and all(x < blocks for x in numbers), "invalid directory blocks")
        directory = b"".join(src.read(x * block_size, min(block_size, directory_size - i * block_size))
                             for i, x in enumerate(numbers))
        streams = struct.unpack_from("<I", directory)[0]
        require(2 <= streams <= 100000 and 4 + streams * 4 <= len(directory), "invalid stream table")
        sizes = struct.unpack_from("<" + "I" * streams, directory, 4)
        cursor, info_block = 4 + streams * 4, None
        for index, size in enumerate(sizes):
            n = 0 if size == 0xFFFFFFFF else (size + block_size - 1) // block_size
            require(cursor + n * 4 <= len(directory), "truncated stream block list")
            stream_blocks = struct.unpack_from("<" + "I" * n, directory, cursor)
            require(all(x < blocks for x in stream_blocks), "invalid stream block number")
            if index == 1:
                require(size != 0xFFFFFFFF and size >= 28 and n > 0, "missing PDB info stream")
                info_block = stream_blocks[0]
            cursor += n * 4
        require(cursor == len(directory) and info_block is not None, "invalid directory tail")
        info = src.read(info_block * block_size, 28)
        version, _, age = struct.unpack_from("<III", info)
        require(version == 20000404, "unsupported PDB info version")
        return {"name": Path(path).name, "file_bytes": src.size,
                "metadata_bytes_read": src.bytes_read,
                "guid": str(uuid.UUID(bytes_le=info[12:28])), "age": age}


def pair_report(image, pdb):
    pe, symbols = pe_identity(image), pdb_identity(pdb)
    return {"schema": "iw7.rig-abi.symbol-identity/1", "pe": pe, "pdb": symbols,
            "guid_age_match": all(pe["codeview"][key] == symbols[key] for key in ("guid", "age")),
            "full_hash_verified": False, "runtime_mapping_verified": False,
            "retail_loader_symbols_established": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--pdb", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = pair_report(args.image, args.pdb)
    except (OSError, ValueError, struct.error) as exc:
        parser.exit(2, f"refused: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0 if result["guid_age_match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
