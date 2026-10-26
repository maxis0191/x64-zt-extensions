"""Read-only BO3 xpak reader (header/hash table per x64-zt t7/common/xpak.cpp;
data blocks: XPakDataHeader {count, offset, commands[30]}, command = flag<<24 |
size, flag 3 = LZ4 block, 0 = raw). Pure-Python LZ4 block decoder."""
import os, struct, glob

HDR = struct.Struct("<IHHQQQQQQQQQQQQQQ")


def lz4_block(src, max_out=0x10000):
    """Decode one LZ4 block; truncated or oversized input raises ValueError."""
    out = bytearray()
    i, n = 0, len(src)

    def byte():
        nonlocal i
        if i >= n:
            raise ValueError("truncated lz4 block")
        b = src[i]
        i += 1
        return b

    while i < n:
        token = byte()
        lit = token >> 4
        if lit == 15:
            while True:
                b = byte(); lit += b
                if b != 255:
                    break
        if i + lit > n:
            raise ValueError("truncated lz4 literals")
        out += src[i:i + lit]; i += lit
        if i >= n:
            break
        if i + 2 > n:
            raise ValueError("truncated lz4 offset")
        off = src[i] | (src[i + 1] << 8); i += 2
        if off == 0 or off > len(out):
            raise ValueError("invalid lz4 offset")
        ml = token & 15
        if ml == 15:
            while True:
                b = byte(); ml += b
                if b != 255:
                    break
        ml += 4
        if len(out) + ml > max_out:
            raise ValueError("lz4 block overflow")
        start = len(out) - off
        if off >= ml:
            out += out[start:start + ml]
        else:
            for k in range(ml):
                out.append(out[start + k])
    if len(out) > max_out:
        raise ValueError("lz4 block overflow")
    return bytes(out)


class XPakSet:
    def __init__(self, zone_dir, names=None):
        self.index = {}
        paths = sorted(glob.glob(os.path.join(zone_dir, "*.xpak")))
        for p in paths:
            if names and os.path.splitext(os.path.basename(p))[0] not in names:
                continue
            if os.path.getsize(p) < HDR.size:
                continue
            with open(p, "rb") as f:
                h = HDR.unpack(f.read(HDR.size))
                if h[0] != 0x4950414B:
                    continue
                data_off, hash_count, hash_off = h[6], h[8], h[9]
                f.seek(hash_off)
                raw = f.read(hash_count * 24)
            for k in range(hash_count):
                key, off, size = struct.unpack_from("<QQQ", raw, k * 24)
                self.index.setdefault(key, (p, data_off + off, size & 0xFFFFFFFFFFFFFF))

    def get(self, key):
        if isinstance(key, str):
            key = int(key, 16)
        if key not in self.index:
            return None
        path, off, size = self.index[key]
        with open(path, "rb") as f:
            f.seek(off)
            data = f.read(size)
        out = bytearray()
        p = 0
        while p + 128 <= len(data):
            count, offset = struct.unpack_from("<II", data, p)
            cmds = struct.unpack_from("<30I", data, p + 8)
            valid = 1 <= count <= 30 and offset == len(out) and all((c >> 24) in (0, 3) for c in cmds[:count])
            if not valid:
                # Groups are padded (0xCD fill); the next header is 128-aligned and
                # its Offset field equals the decompressed position.
                p = (p // 128 + 1) * 128
                continue
            p += 128
            for c in cmds[:count]:
                bs, flag = c & 0xFFFFFF, c >> 24
                block = data[p:p + bs]
                out += lz4_block(block) if flag == 3 else block
                p += bs
        return bytes(out)
