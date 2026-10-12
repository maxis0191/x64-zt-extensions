"""Separate bounded FLAC subset decoder; imports no encoder or native codec.

This is a separately implemented structural/sample check, not third-party codec
or IW7 playback acceptance. Unsupported FLAC features fail closed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def check(ok, message):
    if not ok:
        raise ValueError(message)


def remainder(data, width, polynomial):
    # Polynomial division of bytes including transmitted CRC: residue must be 0.
    acc = 0
    divisor = (1 << width) | polynomial
    for byte in data:
        acc = (acc << 8) | byte
        for bit in range(width + 7, width - 1, -1):
            if acc & (1 << bit):
                acc ^= divisor << (bit - width)
    return acc


def decode(data):
    check(100 <= len(data) <= 200000, "bounded FLAC required")
    check(data[:8] == b"fLaC\x00\x00\x00\x22", "exact first STREAMINFO required")
    lo, hi = struct.unpack_from(">HH", data, 8)
    min_frame, max_frame = int.from_bytes(data[12:15], "big"), int.from_bytes(data[15:18], "big")
    descriptor = int.from_bytes(data[18:26], "big")
    rate, channels = descriptor >> 44, ((descriptor >> 41) & 7) + 1
    bits, total = ((descriptor >> 36) & 31) + 1, descriptor & ((1 << 36) - 1)
    check((lo, hi, rate, channels, bits) == (4096, 4096, 48000, 1, 16), "unsupported STREAMINFO")
    check(16 <= total <= 96000, "sample count outside bound")
    expected_md5 = data[26:42]
    check(data[42] == 0x83, "one final SEEKTABLE required")
    seek_size = int.from_bytes(data[43:46], "big")
    expected_frames = (total + 4095) // 4096
    check(seek_size == expected_frames * 18 and 46 + seek_size < len(data), "seek table length mismatch")
    seeks = [struct.unpack_from(">QQH", data, 46 + i * 18) for i in range(expected_frames)]
    audio_start = pos = 46 + seek_size
    pcm, observed_sizes = bytearray(), []
    for index in range(expected_frames):
        start = pos
        check(pos + 11 <= len(data), "truncated frame")
        sync = int.from_bytes(data[pos:pos + 2], "big")
        block_code, rate_code = data[pos + 2] >> 4, data[pos + 2] & 15
        channel_code, depth_code = data[pos + 3] >> 4, (data[pos + 3] >> 1) & 7
        check(sync == 0xFFF8 and (block_code, rate_code, channel_code, depth_code) == (7, 10, 0, 4)
              and data[pos + 3] & 1 == 0, "unsupported frame header")
        check(data[pos + 4] == index, "noncanonical frame sequence")
        count = int.from_bytes(data[pos + 5:pos + 7], "big") + 1
        check(count == min(4096, total - len(pcm) // 2), "frame block/sample count mismatch")
        check(remainder(data[pos:pos + 8], 8, 0x07) == 0, "header CRC mismatch")
        check(seeks[index] == (len(pcm) // 2, start - audio_start, count), "seek point mismatch")
        pos += 8
        check(data[pos] == 2, "only verbatim subframes without wasted bits supported")
        pos += 1
        end = pos + count * 2
        check(end + 2 <= len(data), "truncated subframe")
        for cursor in range(pos, end, 2):
            value = int.from_bytes(data[cursor:cursor + 2], "big", signed=True)
            pcm.extend(value.to_bytes(2, "little", signed=True))
        pos = end + 2
        check(remainder(data[start:pos], 16, 0x8005) == 0, "frame CRC mismatch")
        observed_sizes.append(pos - start)
    check(pos == len(data), "trailing bytes/frame refused")
    check((min(observed_sizes), max(observed_sizes)) == (min_frame, max_frame), "frame size bounds mismatch")
    check(len(pcm) == total * 2 and hashlib.md5(pcm).digest() == expected_md5, "PCM MD5/count mismatch")
    report = {"schema": "iw7.original-sound-flac-read/1", "sample_rate": rate,
              "channels": channels, "bits_per_sample": bits, "samples": total,
              "frames": expected_frames, "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
              "crc_and_seek_verified": True, "pcm_md5_verified": True,
              "decoder": "separate Python restricted-subset implementation",
              "native_codec_verified": False, "playback_verified": False, "ready": False}
    return bytes(pcm), report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    # Bound the read, not only the parser allocation.
    with args.path.open("rb") as stream:
        data = stream.read(200001)
    _, report = decode(data)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
