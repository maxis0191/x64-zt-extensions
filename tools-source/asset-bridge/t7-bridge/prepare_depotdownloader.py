"""Prepare one pinned portable tool; never execute it or download game content."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import time
import urllib.request
import zipfile

URL = "https://github.com/SteamRE/DepotDownloader/releases/download/DepotDownloader_3.4.0/DepotDownloader-windows-x64.zip"
ARCHIVE_BYTES = 33474005
SHA256 = "41c9e9f0df54b3ad02e67a11726756e5c73283bd7c2e1b04acfa5ae4c2ed3767"
SOURCE = "c553ef4d60c00a4f5fd16c9fe017f569001589ff"
TRANSFER_LIMIT = 40 * 1024 * 1024
EXTRACTION_LIMIT = 128 * 1024 * 1024


def canonical_parent(path):
    if not path.is_absolute() or path != path.resolve() or path.exists():
        raise ValueError("Fresh canonical absolute destination required")
    if not path.parent.is_dir():
        raise ValueError("Existing durable tool parent required")
    for entry in (path.parent, *path.parent.parents):
        if entry.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError("Reparse ancestry refused")


def safe_entry(info):
    name = info.filename
    parts = PurePosixPath(name).parts
    if not name or name.startswith("/") or "\\" in name or not parts:
        raise ValueError("Invalid archive path")
    for part in name.rstrip("/").split("/"):
        stem = part.split(".")[0].rstrip(" .").upper()
        devices = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$", "CLOCK$"}
        devices.update(f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(10))
        if (part in ("", ".", "..") or part.endswith((" ", ".")) or stem in devices
                or any(ord(c) < 32 or ord(c) > 126 or c in ':<>"|?*' for c in part)):
            raise ValueError("Unsafe Windows archive component")
    mode = stat.S_IFMT(info.external_attr >> 16)
    if mode not in (0, stat.S_IFREG, stat.S_IFDIR) or info.flag_bits & 1:
        raise ValueError("Link/special/encrypted archive entry refused")
    return parts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    if os.name != "nt":
        raise ValueError("Windows portable preparation only")
    root = Path(args.destination)
    canonical_parent(root)
    root.mkdir()
    archive = root / "DepotDownloader-windows-x64.zip"
    started, transferred = time.monotonic(), 0
    digest = hashlib.sha256()
    request = urllib.request.Request(URL, headers={"User-Agent": "IW7-pinned-tool-preparation"})
    with urllib.request.urlopen(request, timeout=20) as source, archive.open("xb") as target:
        if source.status != 200 or int(source.headers.get("Content-Length", -1)) != ARCHIVE_BYTES:
            raise ValueError("Official asset size/status differs")
        while block := source.read(1024 * 1024):
            transferred += len(block)
            if transferred > TRANSFER_LIMIT or time.monotonic() - started >= 60:
                raise ValueError("Bounded transfer exceeded")
            target.write(block)
            digest.update(block)
    if transferred != ARCHIVE_BYTES or digest.hexdigest() != SHA256:
        raise ValueError("Archive identity mismatch; preserve failed download")
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        if not entries or len(entries) > 128 or sum(x.file_size for x in entries) > EXTRACTION_LIMIT:
            raise ValueError("Archive inventory exceeds extraction bounds")
        names = set()
        for entry in entries:
            safe_entry(entry)
            key = entry.filename.rstrip("/").casefold()
            if key in names:
                raise ValueError("Duplicate archive path")
            names.add(key)
        if "depotdownloader.exe" not in names:
            raise ValueError("Expected portable executable missing")
        inventory = [{"name": x.filename, "bytes": x.file_size, "compressed_bytes": x.compress_size}
                     for x in entries]
        (root / "archive-inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
        output = root / "bin"
        output.mkdir()
        files, total = [], 0
        for entry in entries:
            target = output.joinpath(*safe_entry(entry))
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            written, file_digest = 0, hashlib.sha256()
            with package.open(entry) as source, target.open("xb") as destination:
                while block := source.read(1024 * 1024):
                    written += len(block)
                    total += len(block)
                    if written > entry.file_size or total > EXTRACTION_LIMIT:
                        raise ValueError("Actual extraction exceeds reviewed inventory")
                    destination.write(block)
                    file_digest.update(block)
            if written != entry.file_size:
                raise ValueError("Extracted length mismatch")
            files.append({"path": entry.filename, "bytes": written, "sha256": file_digest.hexdigest()})
    receipt = {"schema": "iw7.depotdownloader-preparation/1", "version": "3.4.0",
               "upstream": "SteamRE/DepotDownloader", "source_commit": SOURCE,
               "release_asset_id": 253287195, "archive_url": URL, "archive_bytes": transferred,
               "archive_sha256": SHA256, "checksum_source": "Microsoft winget-pkgs SteamRE.DepotDownloader 3.4.0 installer manifest",
               "upstream_release_api_digest": None, "extracted_bytes": total, "files": files,
               "tool_executed": False, "system_runtime_installed": False, "game_payload_downloaded": False}
    (root / "prepare-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
