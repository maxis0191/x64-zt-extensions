"""Synthetic header cases and independent Python oracle; no audio or native I/O."""
import struct


def crc8(raw):
    # Polynomial division, independent of the C++ byte-at-a-time shift register.
    value = int.from_bytes(raw, "big") << 8
    while value.bit_length() > 8:
        value ^= 0x107 << (value.bit_length() - 9)
    return value


def header(block_code=7, block=4096, rate_code=10, rate=48000,
           channel_code=0, depth=4, number=0, sync=0xfff8, reserved=0):
    raw = struct.pack(">HBBB", sync, block_code << 4 | rate_code,
                      channel_code << 4 | depth << 1 | reserved, number)
    if block_code == 6:
        raw += bytes([block - 1])
    if block_code == 7:
        raw += struct.pack(">H", block - 1)
    if rate_code == 12:
        raw += bytes([rate // 1000])
    if rate_code in (13, 14):
        raw += struct.pack(">H", rate // (10 if rate_code == 14 else 1))
    return raw + bytes([crc8(raw)])


def oracle(entry, raw, null=False):
    """Header interpretation only. Arbitrary trailing bytes are intentionally opaque."""
    encoded, seek, total, hybrid, rate, channels = entry
    if (hybrid or not 0 < rate < 2**20 or not 1 <= channels <= 8 or not total
            or not encoded or seek > 0xffffff or seek % 18 or null
            or len(raw) != seek + encoded):
        return None
    data = raw[seek:]
    if len(data) < 5:
        return None
    if data[:2] != b"\xff\xf8" or data[3] & 1 or data[4] != 0:
        return None
    channel = data[3] >> 4
    if channel > 10 or (channel + 1 if channel < 8 else 2) != channels or (data[3] >> 1) & 7 != 4:
        return None
    code, rate_code = data[2] >> 4, data[2] & 15
    blocks = {1: 192, 2: 576, 3: 1152, 4: 2304, 5: 4608,
              8: 256, 9: 512, 10: 1024, 11: 2048, 12: 4096,
              13: 8192, 14: 16384, 15: 32768}
    cursor = 5
    try:
        if code in (6, 7):
            width = code - 5
            if len(data[cursor:cursor + width]) != width:
                return None
            block = int.from_bytes(data[cursor:cursor + width], "big") + 1
            cursor += width
        else:
            block = blocks[code]
        rates = {0: rate, 1: 88200, 2: 176400, 3: 192000, 4: 8000,
                 5: 16000, 6: 22050, 7: 24000, 8: 32000, 9: 44100,
                 10: 48000, 11: 96000}
        if rate_code in (12, 13, 14):
            width = 1 if rate_code == 12 else 2
            if len(data[cursor:cursor + width]) != width:
                return None
            observed_rate = int.from_bytes(data[cursor:cursor + width], "big")
            observed_rate *= {12: 1000, 13: 1, 14: 10}[rate_code]
            cursor += width
        else:
            observed_rate = rates[rate_code]
        if (not 16 <= block <= 65535 or total <= block or observed_rate != rate
                or crc8(data[:cursor]) != data[cursor]):
            return None
        return block, cursor + 1
    except (KeyError, IndexError):
        return None


def cases():
    result = []

    def add(name, raw=None, expected=None, *, seek=b"", total=96000,
            rate=48000, channels=1, hybrid=0, null=False, override=None):
        raw = header() if raw is None else raw
        entry = [len(raw), len(seek), total, hybrid, rate, channels]
        if override:
            for index, value in override.items():
                entry[index] = value
        data = seek + raw
        result.append(dict(name=name, entry=entry, data_hex=data.hex(),
                           null=null, expected=list(expected) if expected else None))

    mapping = {1: 192, 2: 576, 3: 1152, 4: 2304, 5: 4608, 6: 200, 7: 4096,
               8: 256, 9: 512, 10: 1024, 11: 2048, 12: 4096, 13: 8192, 14: 16384, 15: 32768}
    for code, block in mapping.items():
        raw = header(block_code=code, block=block)
        add(f"block-code-{code}", raw, (block, len(raw)))
    for code, block in ((6, 16), (6, 256), (7, 65535)):
        raw = header(block_code=code, block=block)
        add(f"block-boundary-{block}", raw, (block, len(raw)))
    for block in (1, 15, 65536):
        add(f"invalid-block-{block}", header(block=block))
    add("reserved-block-code", header(block_code=0))
    rates = [48000, 88200, 176400, 192000, 8000, 16000, 22050, 24000,
             32000, 44100, 48000, 96000, 48000, 48000, 48000]
    for code, rate in enumerate(rates):
        raw = header(rate_code=code, rate=rate)
        add(f"rate-code-{code}", raw, (4096, len(raw)), rate=rate)
    for code in range(11):
        raw = header(channel_code=code)
        add(f"channel-code-{code}", raw, (4096, len(raw)), channels=code + 1 if code < 8 else 2)
    for code in range(11, 16):
        add(f"reserved-channel-{code}", header(channel_code=code))
    for depth in (0, 1, 2, 3, 5, 6, 7):
        add(f"unsupported-depth-{depth}", header(depth=depth))
    for code in (12, 13, 14):
        add(f"zero-rate-extension-{code}", header(rate_code=code, rate=0))
    add("forbidden-rate-code", header(rate_code=15))
    add("rate-mismatch", rate=44100)
    add("channel-mismatch", channels=2)
    add("variable-strategy", header(sync=0xfff9))
    add("bad-sync", header(sync=0xfef8))
    add("reserved-bit", header(reserved=1))
    add("nonzero-first-number", header(number=1))
    add("overlong-first-number", b"\xff\xf8\x7a\x08\xc0\x80\x0f\xff\x00")
    full = header(rate_code=13)
    for size in range(len(full)):
        add(f"truncated-{size}", full[:size])
    add("bad-crc", header()[:-1] + bytes([header()[-1] ^ 1]))
    for total in (0, 4095, 4096):
        add(f"non-multiframe-{total}", total=total)
    add("hybrid", hybrid=1)
    for rate in (-1, 0, 1048576):
        add(f"invalid-entry-rate-{rate}", rate=rate)
    add("max-entry-rate", header(rate_code=0), (4096, 8), rate=1048575)
    for channels in (-1, 0, 9):
        add(f"invalid-entry-channels-{channels}", channels=channels)
    add("empty-seek", expected=(4096, 8))
    add("sparse-seek-prefix", expected=(4096, 8), seek=struct.pack(">QQH", 0, 0, 4096))
    add("placeholder-prefix-opaque", expected=(4096, 8), seek=b"\xff" * 18)
    add("bad-seek-divisibility", seek=b"\x00" * 17)
    add("seek-over-24bit", override={1: 0x1000000})
    add("encoded-size-mismatch", override={0: 9})
    add("wide-sum-does-not-wrap", override={0: 0xffffffff, 1: 18})
    add("prefix-outside-buffer", override={1: 18})
    add("null-span", null=True)
    # Accepted HEADER only: these bytes intentionally do not form a FLAC stream.
    add("invalid-later-body-not-conformance", header() + b"\x00\xff\xf8", (4096, 8))
    return result


def cpp_cases():
    """Produce source constants for the future actual C++ helper probe."""
    lines = ["// Synthetic header vectors, not encoded audio. Generated by flac_dump_vectors.py.",
             "struct TestCase { const char* name; meta::Entry entry; const char* hex;",
             "bool null_span; bool accepted; unsigned block; unsigned header_bytes; };",
             "constexpr TestCase cases[]{"]
    for case in cases():
        expected = case["expected"]
        lines.append('    {"%s", {%s}, "%s", %s, %s, %d, %d},' % (
            case["name"], ", ".join(str(v) + ("u" if i < 4 else "") for i, v in enumerate(case["entry"])),
            case["data_hex"], str(case["null"]).lower(), str(expected is not None).lower(),
            expected[0] if expected else 0, expected[1] if expected else 0))
    return ("\n".join(lines) + "\n};\n").encode()
