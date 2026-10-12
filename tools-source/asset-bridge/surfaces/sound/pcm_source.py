"""Bounded original PCM source and FLAC verbatim encoder. No native execution."""
import hashlib
import struct

RATE = 48000
BLOCK = 4096
MAX_SAMPLES = 96000


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read_wave(data):
    """Accept only canonical RIFF/fmt16/data PCM16 mono 48 kHz, <=2 seconds."""
    require(44 + 32 <= len(data) <= 44 + MAX_SAMPLES * 2, "WAV size outside bound")
    require(data[:4] == b"RIFF" and data[8:12] == b"WAVE", "RIFF/WAVE required")
    require(struct.unpack_from("<I", data, 4)[0] == len(data) - 8, "RIFF length mismatch")
    require(data[12:20] == b"fmt \x10\0\0\0", "canonical fmt16 required; metadata refused")
    require(struct.unpack_from("<HHIIHH", data, 20) == (1, 1, RATE, RATE * 2, 2, 16),
            "only PCM16 mono 48000 Hz supported; no resampling")
    require(data[36:40] == b"data", "one canonical data chunk required")
    size = struct.unpack_from("<I", data, 40)[0]
    require(size == len(data) - 44 and size % 2 == 0, "PCM length/alignment mismatch")
    return data[44:]


def wave_bytes(pcm):
    require(32 <= len(pcm) <= MAX_SAMPLES * 2 and len(pcm) % 2 == 0, "PCM size outside bound")
    return (b"RIFF" + struct.pack("<I", len(pcm) + 36) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, RATE, RATE * 2, 2, 16)
            + b"data" + struct.pack("<I", len(pcm)) + pcm)


def original_wave():
    """One second, three integer triangle pulses; original deterministic marker."""
    samples = [0] * RATE
    for start, stop, period in ((2400, 9600, 96), (14400, 24000, 64), (28800, 43200, 48)):
        for i in range(start, stop):
            phase = (i - start) % period
            triangle = 4096 * (4 * abs(phase - period // 2) - period) // period
            fade = min(i - start, stop - 1 - i, 480)
            samples[i] = triangle * fade // 480
    return wave_bytes(struct.pack("<" + "h" * len(samples), *samples))


def crc(data, width, polynomial):
    value = 0
    for byte in data:
        value ^= byte << (width - 8)
        for _ in range(8):
            value = ((value << 1) ^ (polynomial if value & (1 << (width - 1)) else 0)) & ((1 << width) - 1)
    return value


def encode_flac(pcm):
    """RFC9639 subset: mono16/48k, fixed4096, verbatim, full seek table."""
    require(32 <= len(pcm) <= MAX_SAMPLES * 2 and len(pcm) % 2 == 0, "PCM size outside bound")
    frames, seeks, offset = [], [], 0
    for index, start in enumerate(range(0, len(pcm), BLOCK * 2)):
        block = pcm[start:start + BLOCK * 2]
        count = len(block) // 2
        # All <=24 frame indices use the one-byte UTF-8-style coded number.
        header = b"\xff\xf8\x7a\x08" + bytes([index]) + struct.pack(">H", count - 1)
        header += bytes([crc(header, 8, 0x07)])
        # Verbatim subframe, no wasted bits. Samples are big-endian in FLAC.
        body = bytearray(block)
        body[0::2], body[1::2] = block[1::2], block[0::2]
        frame = header + b"\x02" + bytes(body)
        frame += struct.pack(">H", crc(frame, 16, 0x8005))
        seeks.append(struct.pack(">QQH", start // 2, offset, count))
        frames.append(frame)
        offset += len(frame)
    sizes = [len(frame) for frame in frames]
    info = (struct.pack(">HH", BLOCK, BLOCK) + min(sizes).to_bytes(3, "big")
            + max(sizes).to_bytes(3, "big")
            + ((RATE << 44) | (15 << 36) | (len(pcm) // 2)).to_bytes(8, "big")
            + hashlib.md5(pcm).digest())
    seek = b"".join(seeks)
    return b"fLaC\x00\x00\x00\x22" + info + b"\x83" + len(seek).to_bytes(3, "big") + seek + b"".join(frames)
